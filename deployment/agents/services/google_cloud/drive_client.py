"""
Google Drive Client for Helios Autonomous Store
Handles asset storage, organization, and sharing via Google Drive API
"""

import asyncio
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from loguru import logger

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import io


class GoogleDriveClient:
    """Google Drive client for asset storage and management"""
    
    def __init__(self, service_account_json: str, root_folder_id: str):
        """Initialize Google Drive client
        
        Args:
            service_account_json: Path to service account JSON file or JSON string
            root_folder_id: ID of the root folder for Helios assets
        """
        self.root_folder_id = root_folder_id
        self.credentials = self._get_credentials(service_account_json)
        self.service = build('drive', 'v3', credentials=self.credentials)
        
        # Cache for folder structure
        self._folder_cache = {}
        self._last_cache_update = None
        self._cache_ttl = 600  # 10 minutes
    
    def _get_credentials(self, service_account_json: str) -> Credentials:
        """Get Google credentials from service account"""
        try:
            if service_account_json.startswith('~'):
                import os
                service_account_json = os.path.expanduser(service_account_json)
            
            if service_account_json.endswith('.json'):
                # File path
                return Credentials.from_service_account_file(service_account_json)
            else:
                # JSON string
                import json
                service_account_info = json.loads(service_account_json)
                return Credentials.from_service_account_info(service_account_info)
        except Exception as e:
            logger.error(f"Failed to load service account credentials: {e}")
            raise
    
    async def get_folder_structure(self) -> Dict[str, Any]:
        """Get the folder structure for Helios assets
        
        Returns:
            Dictionary containing folder hierarchy
        """
        try:
            # Check cache first
            if (self._last_cache_update and 
                (datetime.now(timezone.utc) - self._last_cache_update).seconds < self._cache_ttl):
                return self._folder_cache
            
            structure = {
                'root_id': self.root_folder_id,
                'folders': {},
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Get root folder info
            root_info = self.service.files().get(fileId=self.root_folder_id).execute()
            structure['folders']['root'] = {
                'id': root_info['id'],
                'name': root_info['name'],
                'children': []
            }
            
            # Get all subfolders
            query = f"'{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id,name,parents,createdTime)").execute()
            
            for folder in results.get('files', []):
                folder_info = {
                    'id': folder['id'],
                    'name': folder['name'],
                    'created_time': folder.get('createdTime', ''),
                    'children': []
                }
                structure['folders'][folder['id']] = folder_info
                
                # Add to parent's children list
                for parent_id in folder.get('parents', []):
                    if parent_id in structure['folders']:
                        structure['folders'][parent_id]['children'].append(folder['id'])
            
            # Update cache
            self._folder_cache = structure
            self._last_cache_update = datetime.now(timezone.utc)
            
            return structure
            
        except HttpError as e:
            logger.error(f"Failed to get folder structure: {e}")
            raise
    
    async def create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder in Google Drive
        
        Args:
            name: Name of the folder to create
            parent_id: ID of the parent folder (defaults to root)
        
        Returns:
            Dictionary containing folder information
        """
        try:
            if parent_id is None:
                parent_id = self.root_folder_id
            
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            file = self.service.files().create(
                body=file_metadata,
                fields='id,name,parents,createdTime'
            ).execute()
            
            logger.info(f"Created folder: {name} (ID: {file['id']})")
            
            # Invalidate cache
            self._last_cache_update = None
            
            return {
                'id': file['id'],
                'name': file['name'],
                'parents': file.get('parents', []),
                'created_time': file.get('createdTime', '')
            }
            
        except HttpError as e:
            logger.error(f"Failed to create folder {name}: {e}")
            raise
    
    async def ensure_folder_structure(self, path_parts: List[str]) -> str:
        """Ensure a folder structure exists, creating folders as needed
        
        Args:
            path_parts: List of folder names in the path
        
        Returns:
            ID of the final folder in the path
        """
        try:
            current_parent_id = self.root_folder_id
            
            for folder_name in path_parts:
                # Check if folder already exists
                query = f"'{current_parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.service.files().list(q=query, fields="files(id,name)").execute()
                
                if results.get('files'):
                    # Folder exists, use it
                    current_parent_id = results['files'][0]['id']
                else:
                    # Create folder
                    folder_info = await self.create_folder(folder_name, current_parent_id)
                    current_parent_id = folder_info['id']
            
            return current_parent_id
            
        except Exception as e:
            logger.error(f"Failed to ensure folder structure: {e}")
            raise
    
    async def upload_file(self, file_path: Union[str, Path], 
                         folder_id: Optional[str] = None,
                         filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to (defaults to root)
            filename: Optional custom filename for the uploaded file
        
        Returns:
            Dictionary containing file information
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if folder_id is None:
                folder_id = self.root_folder_id
            
            if filename is None:
                filename = file_path.name
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Upload file
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink,webContentLink,createdTime'
            ).execute()
            
            logger.info(f"Uploaded file: {filename} (ID: {file['id']})")
            
            return {
                'id': file['id'],
                'name': file['name'],
                'size': file.get('size', 0),
                'web_view_link': file.get('webViewLink', ''),
                'web_content_link': file.get('webContentLink', ''),
                'created_time': file.get('createdTime', ''),
                'mime_type': mime_type
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise
    
    async def upload_bytes(self, data: bytes, filename: str, 
                          folder_id: Optional[str] = None,
                          mime_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload bytes data to Google Drive
        
        Args:
            data: Bytes data to upload
            filename: Name for the uploaded file
            folder_id: ID of the folder to upload to (defaults to root)
            mime_type: MIME type of the data
        
        Returns:
            Dictionary containing file information
        """
        try:
            if folder_id is None:
                folder_id = self.root_folder_id
            
            if mime_type is None:
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Upload bytes
            media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink,webContentLink,createdTime'
            ).execute()
            
            logger.info(f"Uploaded bytes as file: {filename} (ID: {file['id']})")
            
            return {
                'id': file['id'],
                'name': file['name'],
                'size': file.get('size', 0),
                'web_view_link': file.get('webViewLink', ''),
                'web_content_link': file.get('webContentLink', ''),
                'created_time': file.get('createdTime', ''),
                'mime_type': mime_type
            }
            
        except Exception as e:
            logger.error(f"Failed to upload bytes as file {filename}: {e}")
            raise
    
    async def download_file(self, file_id: str, output_path: Union[str, Path]) -> bool:
        """Download a file from Google Drive
        
        Args:
            file_id: ID of the file to download
            output_path: Path where to save the downloaded file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseUpload(file, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}%")
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(file.getvalue())
            
            logger.info(f"Downloaded file to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return False
    
    async def list_files(self, folder_id: Optional[str] = None, 
                        query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files in a folder
        
        Args:
            folder_id: ID of the folder to list (defaults to root)
            query: Optional query string for filtering
        
        Returns:
            List of file information dictionaries
        """
        try:
            if folder_id is None:
                folder_id = self.root_folder_id
            
            # Build query
            if query:
                base_query = query
            else:
                base_query = f"'{folder_id}' in parents and trashed=false"
            
            results = self.service.files().list(
                q=base_query,
                fields="files(id,name,size,mimeType,createdTime,modifiedTime,webViewLink)",
                pageSize=1000
            ).execute()
            
            files = []
            for file in results.get('files', []):
                file_info = {
                    'id': file['id'],
                    'name': file['name'],
                    'size': file.get('size', 0),
                    'mime_type': file.get('mimeType', ''),
                    'created_time': file.get('createdTime', ''),
                    'modified_time': file.get('modifiedTime', ''),
                    'web_view_link': file.get('webViewLink', '')
                }
                files.append(file_info)
            
            return files
            
        except HttpError as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive
        
        Args:
            file_id: ID of the file to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    async def update_file_permissions(self, file_id: str, 
                                    permission_type: str = 'anyone',
                                    role: str = 'reader') -> bool:
        """Update file permissions for sharing
        
        Args:
            file_id: ID of the file to update permissions for
            permission_type: Type of permission ('user', 'group', 'domain', 'anyone')
            role: Role to assign ('owner', 'writer', 'commenter', 'reader')
        
        Returns:
            True if successful, False otherwise
        """
        try:
            permission = {
                'type': permission_type,
                'role': role
            }
            
            if permission_type == 'anyone':
                permission['withLink'] = True
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"Updated permissions for file {file_id}: {permission_type} -> {role}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to update permissions for file {file_id}: {e}")
            return False
    
    # Helios-specific methods for asset management
    
    async def store_product_image(self, image_data: bytes, trend_name: str, 
                                 product_type: str, design_name: str) -> Dict[str, Any]:
        """Store a product image in the organized folder structure
        
        Args:
            image_data: Image bytes data
            trend_name: Name of the trend
            product_type: Type of product
            design_name: Name of the design
        
        Returns:
            Dictionary containing file information and public URL
        """
        try:
            # Create organized folder structure
            today = datetime.now().strftime('%Y-%m-%d')
            folder_path = ['Product Images', today, trend_name, product_type]
            folder_id = await self.ensure_folder_structure(folder_path)
            
            # Generate filename
            filename = f"{design_name}_{trend_name}_{product_type}.png"
            
            # Upload image
            file_info = await self.upload_bytes(
                data=image_data,
                filename=filename,
                folder_id=folder_id,
                mime_type='image/png'
            )
            
            # Make publicly accessible
            await self.update_file_permissions(file_info['id'], 'anyone', 'reader')
            
            logger.info(f"Stored product image: {filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to store product image: {e}")
            raise
    
    async def store_generated_design(self, design_data: bytes, trend_name: str, 
                                   design_type: str, design_name: str) -> Dict[str, Any]:
        """Store a generated design in the organized folder structure
        
        Args:
            design_data: Design bytes data
            trend_name: Name of the trend
            design_type: Type of design
            design_name: Name of the design
        
        Returns:
            Dictionary containing file information and public URL
        """
        try:
            # Create organized folder structure
            folder_path = ['Generated Designs', trend_name, design_type]
            folder_id = await self.ensure_folder_structure(folder_path)
            
            # Generate filename
            filename = f"{design_name}_{trend_name}_{design_type}.png"
            
            # Upload design
            file_info = await self.upload_bytes(
                data=design_data,
                filename=filename,
                folder_id=folder_id,
                mime_type='image/png'
            )
            
            # Make publicly accessible
            await self.update_file_permissions(file_info['id'], 'anyone', 'reader')
            
            logger.info(f"Stored generated design: {filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to store generated design: {e}")
            raise
    
    async def store_marketing_assets(self, asset_data: bytes, product_type: str, 
                                   asset_name: str, asset_format: str = 'png') -> Dict[str, Any]:
        """Store marketing assets in the organized folder structure
        
        Args:
            asset_data: Asset bytes data
            product_type: Type of product
            asset_name: Name of the asset
            asset_format: Format of the asset (png, jpg, etc.)
        
        Returns:
            Dictionary containing file information and public URL
        """
        try:
            # Create organized folder structure
            folder_path = ['Marketing Assets', product_type]
            folder_id = await self.ensure_folder_structure(folder_path)
            
            # Generate filename
            filename = f"{asset_name}_{product_type}.{asset_format}"
            
            # Determine MIME type
            mime_type = f"image/{asset_format}" if asset_format in ['png', 'jpg', 'jpeg', 'gif'] else 'application/octet-stream'
            
            # Upload asset
            file_info = await self.upload_bytes(
                data=asset_data,
                filename=filename,
                folder_id=folder_id,
                mime_type=mime_type
            )
            
            # Make publicly accessible
            await self.update_file_permissions(file_info['id'], 'anyone', 'reader')
            
            logger.info(f"Stored marketing asset: {filename}")
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to store marketing asset: {e}")
            raise
    
    async def get_public_url(self, file_id: str) -> Optional[str]:
        """Get the public URL for a file
        
        Args:
            file_id: ID of the file
        
        Returns:
            Public URL if available, None otherwise
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink,webContentLink'
            ).execute()
            
            return file.get('webViewLink') or file.get('webContentLink')
            
        except HttpError as e:
            logger.error(f"Failed to get public URL for file {file_id}: {e}")
            return None
