# shared_architecture/connections/service_discovery.py

import socket
import os
import logging
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceType(Enum):
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    MONGODB = "mongodb"
    TIMESCALEDB = "timescaledb"
    POSTGRES = "postgres"

class Environment(Enum):
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"

# Default ports for services
SERVICE_PORTS = {
    ServiceType.REDIS: 6379,
    ServiceType.RABBITMQ: 5672,
    ServiceType.MONGODB: 27017,
    ServiceType.TIMESCALEDB: 5432,
    ServiceType.POSTGRES: 5432,
}

# Service name mappings for different environments
SERVICE_NAMES = {
    ServiceType.REDIS: ["redis"],
    ServiceType.RABBITMQ: ["rabbitmq"],
    ServiceType.MONGODB: ["mongo", "mongodb"],
    ServiceType.TIMESCALEDB: ["timescaledb", "postgres"],
    ServiceType.POSTGRES: ["postgres", "timescaledb"],
}

class ServiceDiscovery:
    """Unified service discovery for all backend services"""
    
    def __init__(self):
        self.environment = self._detect_environment()
        logger.info(f"Environment detected: {self.environment.value}")
    
    def _detect_environment(self) -> Environment:
        """Detect the current environment"""
        # Check for explicit environment variable
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var == "local":
            return Environment.LOCAL
        
        # Check for Kubernetes
        if os.getenv("KUBERNETES_SERVICE_HOST") is not None:
            return Environment.KUBERNETES
        
        # Check for Docker
        if os.path.exists("/.dockerenv"):
            return Environment.DOCKER
        
        # Default to local
        return Environment.LOCAL
    
    def resolve_service_host(self, hostname: str, service_type: ServiceType) -> str:
        """
        Resolve service hostname with environment-aware fallbacks
        
        Args:
            hostname: The configured hostname (e.g., from config)
            service_type: The type of service being resolved
            
        Returns:
            The resolved hostname/IP to use
        """
        logger.info(f"Resolving {service_type.value} host: {hostname} in {self.environment.value} environment")
        
        # Local development - use localhost for known service names
        if self.environment == Environment.LOCAL:
            if hostname in self._get_service_names(service_type):
                logger.info(f"Local environment: using localhost for {hostname}")
                return "localhost"
            return hostname
        
        # Kubernetes - service names should work as-is
        if self.environment == Environment.KUBERNETES:
            logger.info(f"Kubernetes environment: using service name {hostname}")
            return hostname
        
        # Docker environment - try hostname first, fallback to IP discovery
        if self.environment == Environment.DOCKER:
            return self._resolve_docker_service(hostname, service_type)
        
        return hostname
    
    def _get_service_names(self, service_type: ServiceType) -> List[str]:
        """Get all possible service names for a service type"""
        return SERVICE_NAMES.get(service_type, [])
    
    def _resolve_docker_service(self, hostname: str, service_type: ServiceType) -> str:
        """Resolve service in Docker environment with fallbacks"""
        # First try the hostname as-is
        port = SERVICE_PORTS.get(service_type, 80)
        
        try:
            socket.gethostbyname(hostname)
            if self._test_connection(hostname, port):
                logger.info(f"DNS resolution and connection successful for {hostname}:{port}")
                return hostname
        except socket.gaierror:
            logger.warning(f"DNS resolution failed for {hostname}")
        
        # If connection test failed or DNS failed, try IP discovery
        logger.warning(f"Trying IP discovery for {service_type.value}...")
        discovered_ip = self._discover_service_ip(service_type)
        
        if discovered_ip:
            logger.info(f"Discovered IP for {service_type.value}: {discovered_ip}")
            return discovered_ip
        else:
            logger.error(f"Could not resolve or discover IP for {hostname}")
            return hostname  # Return original hostname as last resort
    
    def _discover_service_ip(self, service_type: ServiceType) -> Optional[str]:
        """
        Try to discover service IP by attempting connections to common Docker network ranges
        """
        port = SERVICE_PORTS.get(service_type, 80)
        
        # Common Docker network ranges
        network_ranges = [
            "172.18.0.",  # Default bridge network range
            "172.17.0.",  # Docker default bridge
            "172.20.0.",  # Custom bridge networks
            "172.19.0.",  # Additional bridge networks
            "192.168.0.", # Some custom networks
        ]
        
        for network_range in network_ranges:
            for host_num in range(2, 30):  # Try IPs .2 through .29
                test_ip = f"{network_range}{host_num}"
                if self._test_connection(test_ip, port, timeout=1):
                    logger.info(f"Found {service_type.value} at {test_ip}:{port}")
                    return test_ip
        
        return None
    
    def _test_connection(self, host: str, port: int, timeout: int = 2) -> bool:
        """Test if a host:port is reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Connection test failed for {host}:{port} - {e}")
            return False
    
    def get_connection_info(self, hostname: str, service_type: ServiceType) -> Dict[str, str]:
        """
        Get complete connection information for a service
        
        Returns:
            Dictionary with 'host', 'port', 'resolved_host' keys
        """
        resolved_host = self.resolve_service_host(hostname, service_type)
        default_port = SERVICE_PORTS.get(service_type, 80)
        
        return {
            'original_host': hostname,
            'resolved_host': resolved_host,
            'default_port': str(default_port),
            'environment': self.environment.value
        }

# Global service discovery instance
service_discovery = ServiceDiscovery()