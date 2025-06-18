import requests
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthenticationException, AuthorizationException
from ..db.models.user import User, UserRole
from ..db.session import get_db
from ..schemas.user import UserCreateSchema

logger = get_logger(__name__)

class KeycloakUserManager:
    """Enhanced Keycloak integration with user provisioning and synchronization"""
    
    def __init__(self, keycloak_url: str, realm: str, client_id: str, client_secret: str, admin_username: str, admin_password: str):
        self.keycloak_url = keycloak_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.admin_username = admin_username
        self.admin_password = admin_password
        self._admin_token = None
        self._admin_token_expires = None
    
    async def get_admin_token(self) -> str:
        """Get admin access token for Keycloak management operations"""
        try:
            if self._admin_token and self._admin_token_expires:
                if datetime.now().timestamp() < self._admin_token_expires - 30:  # 30s buffer
                    return self._admin_token
            
            auth_url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
            
            data = {
                'grant_type': 'password',
                'client_id': 'admin-cli',
                'username': self.admin_username,
                'password': self.admin_password
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(auth_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                self._admin_token = token_data['access_token']
                self._admin_token_expires = datetime.now().timestamp() + token_data.get('expires_in', 300)
                
                logger.info("Successfully obtained Keycloak admin token")
                return self._admin_token
                
        except Exception as e:
            logger.error(f"Failed to get Keycloak admin token: {str(e)}")
            raise AuthenticationException(
                message="Failed to authenticate with Keycloak admin",
                details={"error": str(e)}
            )
    
    async def create_keycloak_user(self, user_data: Dict[str, Any]) -> str:
        """Create user in Keycloak and return user ID"""
        try:
            admin_token = await self.get_admin_token()
            
            users_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
            
            keycloak_user = {
                "username": user_data["email"],
                "email": user_data["email"],
                "firstName": user_data.get("first_name", ""),
                "lastName": user_data.get("last_name", ""),
                "enabled": True,
                "emailVerified": False,
                "credentials": [
                    {
                        "type": "password",
                        "value": user_data["password"],
                        "temporary": False
                    }
                ] if "password" in user_data else []
            }
            
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(users_url, json=keycloak_user, headers=headers)
                
                if response.status_code == 201:
                    # Extract user ID from Location header
                    location = response.headers.get("Location", "")
                    user_id = location.split("/")[-1] if location else None
                    
                    if user_id:
                        logger.info(f"Successfully created Keycloak user: {user_data['email']}")
                        return user_id
                    else:
                        raise Exception("User created but ID not found in response")
                        
                elif response.status_code == 409:
                    # User already exists - get user ID
                    existing_user = await self.get_keycloak_user_by_email(user_data["email"])
                    if existing_user:
                        logger.info(f"Keycloak user already exists: {user_data['email']}")
                        return existing_user["id"]
                    else:
                        raise Exception("User exists but cannot be retrieved")
                else:
                    raise Exception(f"Failed to create user: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Failed to create Keycloak user: {str(e)}")
            raise AuthenticationException(
                message="Failed to create user in Keycloak",
                details={"error": str(e), "email": user_data.get("email")}
            )
    
    async def get_keycloak_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get Keycloak user by email"""
        try:
            admin_token = await self.get_admin_token()
            
            users_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users"
            
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
            
            params = {"email": email, "exact": "true"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(users_url, params=params, headers=headers)
                response.raise_for_status()
                
                users = response.json()
                return users[0] if users else None
                
        except Exception as e:
            logger.error(f"Failed to get Keycloak user by email: {str(e)}")
            return None
    
    async def assign_role_to_user(self, user_id: str, role_name: str):
        """Assign role to Keycloak user"""
        try:
            admin_token = await self.get_admin_token()
            
            # Get available roles
            roles_url = f"{self.keycloak_url}/admin/realms/{self.realm}/roles"
            
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                # Get role definition
                response = await client.get(f"{roles_url}/{role_name}", headers=headers)
                
                if response.status_code == 404:
                    # Role doesn't exist, create it
                    role_data = {
                        "name": role_name,
                        "description": f"Auto-created role: {role_name}"
                    }
                    create_response = await client.post(roles_url, json=role_data, headers=headers)
                    create_response.raise_for_status()
                    
                    # Get the created role
                    response = await client.get(f"{roles_url}/{role_name}", headers=headers)
                
                response.raise_for_status()
                role_data = response.json()
                
                # Assign role to user
                user_roles_url = f"{self.keycloak_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm"
                
                assign_response = await client.post(
                    user_roles_url, 
                    json=[role_data], 
                    headers=headers
                )
                assign_response.raise_for_status()
                
                logger.info(f"Successfully assigned role {role_name} to user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to assign role to user: {str(e)}")
            raise AuthenticationException(
                message="Failed to assign role in Keycloak",
                details={"error": str(e), "user_id": user_id, "role": role_name}
            )
    
    async def sync_user_with_keycloak(self, local_user: User, db: Session) -> bool:
        """Synchronize local user with Keycloak"""
        try:
            # Check if user exists in Keycloak
            keycloak_user = await self.get_keycloak_user_by_email(local_user.email)
            
            if not keycloak_user:
                # Create user in Keycloak
                user_data = {
                    "email": local_user.email,
                    "first_name": local_user.first_name,
                    "last_name": local_user.last_name
                }
                keycloak_user_id = await self.create_keycloak_user(user_data)
                
                # Assign role based on local user role
                role_mapping = {
                    UserRole.ADMIN: "admin",
                    UserRole.EDITOR: "editor", 
                    UserRole.VIEWER: "viewer"
                }
                
                keycloak_role = role_mapping.get(local_user.role, "viewer")
                await self.assign_role_to_user(keycloak_user_id, keycloak_role)
                
                logger.info(f"Successfully synced local user {local_user.email} with Keycloak")
                return True
            else:
                logger.info(f"User {local_user.email} already exists in Keycloak")
                return True
                
        except Exception as e:
            logger.error(f"Failed to sync user with Keycloak: {str(e)}")
            return False

    async def provision_user_from_keycloak(self, keycloak_user_data: Dict[str, Any], db: Session) -> User:
        """Provision local user from Keycloak user data"""
        try:
            # Check if user already exists locally
            existing_user = db.query(User).filter(User.email == keycloak_user_data["email"]).first()
            
            if existing_user:
                logger.info(f"Local user already exists: {keycloak_user_data['email']}")
                return existing_user
            
            # Map Keycloak user to local user schema
            user_create_data = UserCreateSchema(
                first_name=keycloak_user_data.get("firstName", ""),
                last_name=keycloak_user_data.get("lastName", ""),
                email=keycloak_user_data["email"],
                phone_number="",  # Not available from Keycloak by default
                role=UserRole.VIEWER  # Default role, can be updated based on Keycloak roles
            )
            
            # Create local user
            new_user = User(
                first_name=user_create_data.first_name,
                last_name=user_create_data.last_name,
                email=user_create_data.email,
                phone_number=user_create_data.phone_number,
                role=user_create_data.role
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"Successfully provisioned local user from Keycloak: {new_user.email}")
            return new_user
            
        except Exception as e:
            logger.error(f"Failed to provision user from Keycloak: {str(e)}")
            db.rollback()
            raise AuthenticationException(
                message="Failed to provision user from Keycloak",
                details={"error": str(e), "email": keycloak_user_data.get("email")}
            )

# Original functions for backward compatibility
def get_access_token(auth_url: str, client_id: str, client_secret: str, username: str, password: str) -> str:
    """
    Get an access token from Keycloak using username and password.
    
    Args:
        auth_url: Keycloak token endpoint URL
        client_id: Keycloak client ID
        client_secret: Keycloak client secret
        username: User's username/email
        password: User's password
        
    Returns:
        Access token string
        
    Raises:
        Exception: If authentication fails
    """
    data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password
    }
    
    response = requests.post(auth_url, data=data)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"Failed to get access token: {response.text}")


def refresh_access_token(refresh_url: str, client_id: str, client_secret: str, refresh_token: str) -> Dict[str, Any]:
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_url: Keycloak token endpoint URL
        client_id: Keycloak client ID
        client_secret: Keycloak client secret
        refresh_token: Refresh token string
        
    Returns:
        Dictionary containing new access_token and refresh_token
        
    Raises:
        Exception: If token refresh fails
    """
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }
    
    response = requests.post(refresh_url, data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to refresh token: {response.text}")

# Global instance for easier access
keycloak_manager: Optional[KeycloakUserManager] = None

def get_keycloak_manager() -> KeycloakUserManager:
    """Get global Keycloak manager instance"""
    global keycloak_manager
    if keycloak_manager is None:
        raise RuntimeError("Keycloak manager not initialized. Call init_keycloak_manager() first.")
    return keycloak_manager

def init_keycloak_manager(keycloak_url: str, realm: str, client_id: str, client_secret: str, admin_username: str, admin_password: str):
    """Initialize global Keycloak manager"""
    global keycloak_manager
    keycloak_manager = KeycloakUserManager(keycloak_url, realm, client_id, client_secret, admin_username, admin_password)
    logger.info(f"Keycloak manager initialized for realm: {realm}")