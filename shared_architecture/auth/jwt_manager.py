# shared_architecture/auth/jwt_manager.py

import jwt
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from pydantic import BaseModel
from cryptography import serialization

from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthenticationException, AuthorizationException
from ..db.models.user import UserRole

logger = get_logger(__name__)

class JWTClaims(BaseModel):
    """Standardized JWT claims structure"""
    sub: str  # Subject (user ID)
    email: str
    preferred_username: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    realm_access: Optional[Dict[str, List[str]]] = None
    resource_access: Optional[Dict[str, Dict[str, List[str]]]] = None
    exp: int  # Expiration time
    iat: int  # Issued at
    iss: str  # Issuer
    aud: Optional[str] = None  # Audience

class UserContext(BaseModel):
    """User context extracted from JWT"""
    user_id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    local_user_role: Optional[UserRole] = None
    groups: List[str] = []

class JWTManager:
    """
    JWT token validation and user context management for Keycloak integration
    """
    
    def __init__(self, keycloak_url: str, realm: str, client_id: str):
        self.keycloak_url = keycloak_url
        self.realm = realm
        self.client_id = client_id
        self.public_key_cache = {}
        self.algorithm = "RS256"
        
    async def get_keycloak_public_key(self) -> str:
        """
        Fetch Keycloak public key for JWT verification
        """
        cache_key = f"{self.keycloak_url}:{self.realm}"
        
        if cache_key in self.public_key_cache:
            return self.public_key_cache[cache_key]
            
        try:
            certs_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(certs_url)
                response.raise_for_status()
                
                jwks = response.json()
                
                # Get the first key (assuming single key setup)
                if not jwks.get("keys"):
                    raise AuthenticationException(
                        message="No public keys found in Keycloak JWKS",
                        details={"realm": self.realm}
                    )
                
                key_data = jwks["keys"][0]
                
                # Convert to PEM format
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                pem_key = public_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                self.public_key_cache[cache_key] = pem_key
                logger.info(f"Successfully cached Keycloak public key for realm: {self.realm}")
                
                return pem_key
                
        except Exception as e:
            logger.error(f"Failed to fetch Keycloak public key: {str(e)}")
            raise AuthenticationException(
                message="Failed to fetch authentication public key",
                details={"error": str(e), "realm": self.realm}
            )
    
    async def validate_token(self, token: str) -> JWTClaims:
        """
        Validate JWT token and extract claims
        """
        try:
            # Get public key for verification
            public_key = await self.get_keycloak_public_key()
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.algorithm],
                audience=self.client_id,
                options={"verify_exp": True, "verify_aud": False}  # Keycloak may not always include aud
            )
            
            # Validate required claims
            required_claims = ["sub", "email", "preferred_username", "exp", "iat", "iss"]
            missing_claims = [claim for claim in required_claims if claim not in payload]
            
            if missing_claims:
                raise AuthenticationException(
                    message="Invalid token: missing required claims",
                    details={"missing_claims": missing_claims}
                )
            
            # Check token expiration
            current_time = datetime.now(timezone.utc).timestamp()
            if payload["exp"] < current_time:
                raise AuthenticationException(
                    message="Token has expired",
                    details={"exp": payload["exp"], "current_time": current_time}
                )
            
            logger.info(f"Successfully validated JWT token for user: {payload['preferred_username']}")
            
            return JWTClaims(**payload)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationException(
                message="Token has expired",
                details={"token_type": "JWT"}
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationException(
                message="Invalid token",
                details={"error": str(e), "token_type": "JWT"}
            )
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            raise AuthenticationException(
                message="Token validation failed",
                details={"error": str(e)}
            )
    
    def extract_user_context(self, claims: JWTClaims) -> UserContext:
        """
        Extract user context from JWT claims
        """
        try:
            # Extract roles from Keycloak claims
            roles = []
            permissions = []
            
            # Extract realm roles
            if claims.realm_access and "roles" in claims.realm_access:
                roles.extend(claims.realm_access["roles"])
            
            # Extract client roles
            if claims.resource_access and self.client_id in claims.resource_access:
                client_access = claims.resource_access[self.client_id]
                if "roles" in client_access:
                    roles.extend(client_access["roles"])
            
            # Map Keycloak roles to local UserRole enum
            local_user_role = self._map_keycloak_role_to_local(roles)
            
            # Extract permissions (if using fine-grained permissions)
            permissions = self._extract_permissions_from_roles(roles)
            
            user_context = UserContext(
                user_id=claims.sub,
                email=claims.email,
                username=claims.preferred_username,
                first_name=claims.given_name,
                last_name=claims.family_name,
                roles=roles,
                permissions=permissions,
                local_user_role=local_user_role,
                groups=[]  # Will be populated from database if needed
            )
            
            logger.debug(f"Extracted user context for: {user_context.username}")
            
            return user_context
            
        except Exception as e:
            logger.error(f"Failed to extract user context: {str(e)}")
            raise AuthenticationException(
                message="Failed to extract user context from token",
                details={"error": str(e)}
            )
    
    def _map_keycloak_role_to_local(self, keycloak_roles: List[str]) -> UserRole:
        """
        Map Keycloak roles to local UserRole enum
        """
        role_mapping = {
            "admin": UserRole.ADMIN,
            "administrator": UserRole.ADMIN,
            "editor": UserRole.EDITOR,
            "trader": UserRole.EDITOR,
            "viewer": UserRole.VIEWER,
            "user": UserRole.VIEWER,
            "default-roles-trading": UserRole.VIEWER  # Keycloak default role
        }
        
        # Check for highest priority role
        for role in keycloak_roles:
            if role.lower() in role_mapping:
                mapped_role = role_mapping[role.lower()]
                if mapped_role == UserRole.ADMIN:
                    return UserRole.ADMIN
                elif mapped_role == UserRole.EDITOR:
                    continue  # Check for admin first
                elif mapped_role == UserRole.VIEWER:
                    continue  # Check for higher roles first
        
        # Return highest found role or default to VIEWER
        for role in keycloak_roles:
            role_lower = role.lower()
            if role_lower in role_mapping:
                return role_mapping[role_lower]
        
        return UserRole.VIEWER  # Default role
    
    def _extract_permissions_from_roles(self, roles: List[str]) -> List[str]:
        """
        Extract fine-grained permissions from roles
        """
        permission_mapping = {
            "admin": [
                "user:create", "user:read", "user:update", "user:delete",
                "group:create", "group:read", "group:update", "group:delete",
                "trade:create", "trade:read", "trade:update", "trade:delete",
                "system:admin"
            ],
            "editor": [
                "user:read", "user:update",
                "group:read",
                "trade:create", "trade:read", "trade:update"
            ],
            "viewer": [
                "user:read",
                "group:read", 
                "trade:read"
            ]
        }
        
        permissions = set()
        for role in roles:
            role_lower = role.lower()
            if role_lower in permission_mapping:
                permissions.update(permission_mapping[role_lower])
        
        return list(permissions)
    
    def check_permission(self, user_context: UserContext, required_permission: str) -> bool:
        """
        Check if user has required permission
        """
        return required_permission in user_context.permissions
    
    def check_role(self, user_context: UserContext, required_role: UserRole) -> bool:
        """
        Check if user has required role or higher
        """
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.EDITOR: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user_context.local_user_role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        return user_level >= required_level

# Singleton instance for global use
jwt_manager: Optional[JWTManager] = None

def get_jwt_manager() -> JWTManager:
    """Get global JWT manager instance"""
    global jwt_manager
    if jwt_manager is None:
        raise RuntimeError("JWT manager not initialized. Call init_jwt_manager() first.")
    return jwt_manager

def init_jwt_manager(keycloak_url: str, realm: str, client_id: str):
    """Initialize global JWT manager"""
    global jwt_manager
    jwt_manager = JWTManager(keycloak_url, realm, client_id)
    logger.info(f"JWT manager initialized for realm: {realm}")