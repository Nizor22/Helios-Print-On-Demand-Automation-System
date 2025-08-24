"""
Google Secret Manager Client for Helios Autonomous Store
Handles secure storage and retrieval of API keys and credentials
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from loguru import logger

from google.cloud import secretmanager
from google.cloud.secretmanager_v1.types import Secret, SecretVersion
from google.api_core.exceptions import GoogleAPIError


class GoogleSecretManagerClient:
    """Google Secret Manager client for credential management"""
    
    def __init__(self, project_id: str, service_account_json: Optional[str] = None):
        """Initialize Secret Manager client
        
        Args:
            project_id: Google Cloud project ID
            service_account_json: Optional path to service account JSON file
        """
        self.project_id = project_id
        self.client = self._get_client(service_account_json)
        
        # Cache for secrets
        self._secret_cache = {}
        self._last_cache_update = {}
        self._cache_ttl = 3600  # 1 hour
    
    def _get_client(self, service_account_json: Optional[str] = None) -> secretmanager.SecretManagerServiceClient:
        """Get Secret Manager client with optional service account"""
        try:
            if service_account_json:
                import os
                if service_account_json.startswith('~'):
                    service_account_json = os.path.expanduser(service_account_json)
                
                if service_account_json.endswith('.json'):
                    # File path
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_json
                else:
                    # JSON string - write to temporary file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        f.write(service_account_json)
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name
            
            return secretmanager.SecretManagerServiceClient()
            
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {e}")
            raise
    
    def _get_secret_path(self, secret_id: str) -> str:
        """Get the full secret path
        
        Args:
            secret_id: Secret ID (without project path)
        
        Returns:
            Full secret path
        """
        return f"projects/{self.project_id}/secrets/{secret_id}"
    
    def _get_version_path(self, secret_id: str, version_id: str = "latest") -> str:
        """Get the full secret version path
        
        Args:
            secret_id: Secret ID (without project path)
            version_id: Version ID (defaults to "latest")
        
        Returns:
            Full secret version path
        """
        return f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
    
    async def create_secret(self, secret_id: str, description: str = "") -> Dict[str, Any]:
        """Create a new secret
        
        Args:
            secret_id: Unique identifier for the secret
            description: Optional description of the secret
        
        Returns:
            Dictionary containing secret information
        """
        try:
            parent = f"projects/{self.project_id}"
            
            secret = Secret(
                secret_id=secret_id,
                replication={"automatic": {}},
                labels={"helios": "true", "created": datetime.now().strftime('%Y-%m-%d')}
            )
            
            if description:
                secret.labels["description"] = description
            
            secret_obj = self.client.create_secret(
                request={"parent": parent, "secret_id": secret_id, "secret": secret}
            )
            
            logger.info(f"Created secret: {secret_id}")
            
            return {
                'name': secret_obj.name,
                'secret_id': secret_id,
                'create_time': secret_obj.create_time.isoformat(),
                'labels': dict(secret_obj.labels)
            }
            
        except GoogleAPIError as e:
            logger.error(f"Failed to create secret {secret_id}: {e}")
            raise
    
    async def add_secret_version(self, secret_id: str, payload: Union[str, bytes]) -> Dict[str, Any]:
        """Add a new version to an existing secret
        
        Args:
            secret_id: Secret ID
            payload: Secret value (string or bytes)
        
        Returns:
            Dictionary containing version information
        """
        try:
            if isinstance(payload, str):
                payload = payload.encode("UTF-8")
            
            parent = self._get_secret_path(secret_id)
            
            response = self.client.add_secret_version(
                request={"parent": parent, "payload": {"data": payload}}
            )
            
            logger.info(f"Added version to secret: {secret_id}")
            
            return {
                'name': response.name,
                'version_id': response.name.split('/')[-1],
                'create_time': response.create_time.isoformat(),
                'state': response.state.name
            }
            
        except GoogleAPIError as e:
            logger.error(f"Failed to add version to secret {secret_id}: {e}")
            raise
    
    async def get_secret(self, secret_id: str, version_id: str = "latest") -> Optional[str]:
        """Get a secret value
        
        Args:
            secret_id: Secret ID
            version_id: Version ID (defaults to "latest")
        
        Returns:
            Secret value as string, or None if not found
        """
        try:
            # Check cache first
            cache_key = f"{secret_id}:{version_id}"
            if (cache_key in self._last_cache_update and 
                (datetime.now(timezone.utc) - self._last_cache_update[cache_key]).seconds < self._cache_ttl):
                return self._secret_cache.get(cache_key)
            
            name = self._get_version_path(secret_id, version_id)
            
            response = self.client.access_secret_version(request={"name": name})
            
            # Decode the secret payload
            payload = response.payload.data.decode("UTF-8")
            
            # Update cache
            self._secret_cache[cache_key] = payload
            self._last_cache_update[cache_key] = datetime.now(timezone.utc)
            
            logger.info(f"Retrieved secret: {secret_id}")
            return payload
            
        except GoogleAPIError as e:
            logger.error(f"Failed to get secret {secret_id}: {e}")
            return None
    
    async def get_secret_bytes(self, secret_id: str, version_id: str = "latest") -> Optional[bytes]:
        """Get a secret value as bytes
        
        Args:
            secret_id: Secret ID
            version_id: Version ID (defaults to "latest")
        
        Returns:
            Secret value as bytes, or None if not found
        """
        try:
            name = self._get_version_path(secret_id, version_id)
            
            response = self.client.access_secret_version(request={"name": name})
            
            logger.info(f"Retrieved secret bytes: {secret_id}")
            return response.payload.data
            
        except GoogleAPIError as e:
            logger.error(f"Failed to get secret bytes {secret_id}: {e}")
            return None
    
    async def list_secrets(self, filter_str: str = "") -> List[Dict[str, Any]]:
        """List all secrets in the project
        
        Args:
            filter_str: Optional filter string
        
        Returns:
            List of secret information dictionaries
        """
        try:
            parent = f"projects/{self.project_id}"
            
            request = {"parent": parent}
            if filter_str:
                request["filter"] = filter_str
            
            page_result = self.client.list_secrets(request=request)
            
            secrets = []
            for secret in page_result:
                secret_info = {
                    'name': secret.name,
                    'secret_id': secret.name.split('/')[-1],
                    'create_time': secret.create_time.isoformat() if secret.create_time else None,
                    'labels': dict(secret.labels) if secret.labels else {}
                }
                secrets.append(secret_info)
            
            logger.info(f"Listed {len(secrets)} secrets")
            return secrets
            
        except GoogleAPIError as e:
            logger.error(f"Failed to list secrets: {e}")
            raise
    
    async def list_secret_versions(self, secret_id: str) -> List[Dict[str, Any]]:
        """List all versions of a secret
        
        Args:
            secret_id: Secret ID
        
        Returns:
            List of version information dictionaries
        """
        try:
            parent = self._get_secret_path(secret_id)
            
            page_result = self.client.list_secret_versions(request={"parent": parent})
            
            versions = []
            for version in page_result:
                version_info = {
                    'name': version.name,
                    'version_id': version.name.split('/')[-1],
                    'create_time': version.create_time.isoformat() if version.create_time else None,
                    'state': version.state.name,
                    'destroy_time': version.destroy_time.isoformat() if version.destroy_time else None
                }
                versions.append(version_info)
            
            logger.info(f"Listed {len(versions)} versions for secret {secret_id}")
            return versions
            
        except GoogleAPIError as e:
            logger.error(f"Failed to list versions for secret {secret_id}: {e}")
            raise
    
    async def update_secret(self, secret_id: str, description: str = "", 
                           labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Update secret metadata
        
        Args:
            secret_id: Secret ID
            description: New description
            labels: New labels
        
        Returns:
            Dictionary containing updated secret information
        """
        try:
            name = self._get_secret_path(secret_id)
            
            # Get current secret
            secret = self.client.get_secret(request={"name": name})
            
            # Update fields
            if description:
                secret.labels["description"] = description
            
            if labels:
                for key, value in labels.items():
                    secret.labels[key] = value
            
            # Add timestamp
            secret.labels["updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update secret
            updated_secret = self.client.update_secret(
                request={"secret": secret, "update_mask": {"paths": ["labels"]}}
            )
            
            logger.info(f"Updated secret: {secret_id}")
            
            return {
                'name': updated_secret.name,
                'secret_id': secret_id,
                'labels': dict(updated_secret.labels)
            }
            
        except GoogleAPIError as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            raise
    
    async def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret (marks it for deletion)
        
        Args:
            secret_id: Secret ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            name = self._get_secret_path(secret_id)
            
            self.client.delete_secret(request={"name": name})
            
            logger.info(f"Deleted secret: {secret_id}")
            return True
            
        except GoogleAPIError as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False
    
    async def destroy_secret_version(self, secret_id: str, version_id: str) -> bool:
        """Destroy a specific version of a secret
        
        Args:
            secret_id: Secret ID
            version_id: Version ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            name = self._get_version_path(secret_id, version_id)
            
            self.client.destroy_secret_version(request={"name": name})
            
            logger.info(f"Destroyed secret version: {secret_id}:{version_id}")
            return True
            
        except GoogleAPIError as e:
            logger.error(f"Failed to destroy secret version {secret_id}:{version_id}: {e}")
            return False
    
    # Helios-specific methods for credential management
    
    async def get_api_key(self, service_name: str) -> Optional[str]:
        """Get an API key for a specific service
        
        Args:
            service_name: Name of the service (e.g., 'printify', 'etsy', 'gemini')
        
        Returns:
            API key as string, or None if not found
        """
        try:
            secret_id = f"{service_name}-api-key"
            return await self.get_secret(secret_id)
            
        except Exception as e:
            logger.error(f"Failed to get API key for {service_name}: {e}")
            return None
    
    async def store_api_key(self, service_name: str, api_key: str, 
                           description: str = "") -> bool:
        """Store an API key for a specific service
        
        Args:
            service_name: Name of the service
            api_key: The API key to store
            description: Optional description
        
        Returns:
            True if successful, False otherwise
        """
        try:
            secret_id = f"{service_name}-api-key"
            
            # Create secret if it doesn't exist
            try:
                await self.create_secret(secret_id, description)
            except GoogleAPIError:
                # Secret might already exist, continue
                pass
            
            # Add new version
            await self.add_secret_version(secret_id, api_key)
            
            # Update labels
            await self.update_secret(secret_id, description, {
                "service": service_name,
                "type": "api_key",
                "last_updated": datetime.now().isoformat()
            })
            
            logger.info(f"Stored API key for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API key for {service_name}: {e}")
            return False
    
    async def get_credentials(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get credentials for a specific service
        
        Args:
            service_name: Name of the service
        
        Returns:
            Dictionary containing credentials, or None if not found
        """
        try:
            secret_id = f"{service_name}-credentials"
            credentials_json = await self.get_secret(secret_id)
            
            if credentials_json:
                return json.loads(credentials_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get credentials for {service_name}: {e}")
            return None
    
    async def store_credentials(self, service_name: str, credentials: Dict[str, Any], 
                              description: str = "") -> bool:
        """Store credentials for a specific service
        
        Args:
            service_name: Name of the service
            credentials: Dictionary containing credentials
            description: Optional description
        
        Returns:
            True if successful, False otherwise
        """
        try:
            secret_id = f"{service_name}-credentials"
            credentials_json = json.dumps(credentials, indent=2)
            
            # Create secret if it doesn't exist
            try:
                await self.create_secret(secret_id, description)
            except GoogleAPIError:
                # Secret might already exist, continue
                pass
            
            # Add new version
            await self.add_secret_version(secret_id, credentials_json)
            
            # Update labels
            await self.update_secret(secret_id, description, {
                "service": service_name,
                "type": "credentials",
                "last_updated": datetime.now().isoformat()
            })
            
            logger.info(f"Stored credentials for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credentials for {service_name}: {e}")
            return False
    
    async def rotate_api_key(self, service_name: str, new_api_key: str) -> bool:
        """Rotate an API key (store new version and optionally destroy old ones)
        
        Args:
            service_name: Name of the service
            new_api_key: New API key
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store new API key
            success = await self.store_api_key(service_name, new_api_key)
            
            if success:
                # Optionally destroy old versions (keep only latest)
                versions = await self.list_secret_versions(f"{service_name}-api-key")
                
                # Sort by creation time, keep only the latest
                versions.sort(key=lambda x: x['create_time'] or '', reverse=True)
                
                for version in versions[1:]:  # Skip the latest
                    if version['state'] == 'ENABLED':
                        await self.destroy_secret_version(f"{service_name}-api-key", version['version_id'])
                
                logger.info(f"Rotated API key for {service_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to rotate API key for {service_name}: {e}")
            return False
    
    async def get_all_helios_secrets(self) -> Dict[str, Any]:
        """Get all Helios-related secrets
        
        Returns:
            Dictionary containing all secret information
        """
        try:
            # Filter for Helios secrets
            filter_str = "labels.helios=true"
            secrets = await self.list_secrets(filter_str)
            
            result = {
                'project_id': self.project_id,
                'total_secrets': len(secrets),
                'secrets': {}
            }
            
            for secret in secrets:
                secret_id = secret['secret_id']
                versions = await self.list_secret_versions(secret_id)
                
                result['secrets'][secret_id] = {
                    'info': secret,
                    'versions': versions,
                    'latest_value': await self.get_secret(secret_id)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all Helios secrets: {e}")
            return {}
