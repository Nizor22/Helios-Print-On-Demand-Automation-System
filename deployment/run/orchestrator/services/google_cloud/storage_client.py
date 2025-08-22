"""
Google Cloud Storage Client for Helios Autonomous Store
Handles file operations, asset management, and performance optimization
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, BinaryIO
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

from google.cloud import storage
from google.cloud.storage import Blob, Bucket
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError


@dataclass
class StorageConfig:
    """Configuration for Cloud Storage client"""
    project_id: str
    bucket_name: str
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    max_retries: int = 3
    chunk_size: int = 256 * 1024  # 256KB chunks


class CloudStorageClient:
    """Google Cloud Storage client for Helios Autonomous Store"""
    
    def __init__(self, project_id: str, bucket_name: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)
        
        # Cache for frequently accessed metadata
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Asset directories
        self.asset_dirs = {
            "product_designs": "product-designs",
            "marketing_assets": "marketing-assets",
            "trend_visuals": "trend-visuals",
            "audience_data": "audience-data",
            "performance_reports": "performance-reports",
            "ai_generated": "ai-generated"
        }
        
        logger.info(f"✅ Cloud Storage client initialized for bucket: {bucket_name}")
    
    def _get_cache_key(self, operation: str, path: str = None, query: str = None) -> str:
        """Generate a cache key for caching"""
        if path:
            return f"{operation}:{path}"
        elif query:
            return f"{operation}:query:{hash(query)}"
        else:
            return f"{operation}:all"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    async def upload_file(
        self, 
        file_path: Union[str, Path], 
        destination_blob_name: str,
        content_type: str = None,
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Upload a file to Cloud Storage
        
        Args:
            file_path: Local file path
            destination_blob_name: Destination blob name in storage
            content_type: MIME type of the file
            metadata: Additional metadata to store
        
        Returns:
            Upload result information
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Create blob
            blob = self.bucket.blob(destination_blob_name)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Add Helios metadata
            helios_metadata = {
                "helios_version": "1.0.0",
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "original_filename": file_path.name,
                "file_size_bytes": file_path.stat().st_size
            }
            
            if blob.metadata:
                blob.metadata.update(helios_metadata)
            else:
                blob.metadata = helios_metadata
            
            # Upload file
            blob.upload_from_filename(str(file_path))
            
            # Generate URLs
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob_name}"
            signed_url = None
            try:
                signed_url = blob.generate_signed_url(
                    expiration=timedelta(hours=24), version="v4", method="GET"
                )
            except Exception:
                signed_url = None
            
            result = {
                "status": "success",
                "bucket": self.bucket_name,
                "blob_name": destination_blob_name,
                "public_url": public_url,
                "size_bytes": file_path.stat().st_size,
                "content_type": blob.content_type,
                "metadata": blob.metadata,
                "upload_timestamp": helios_metadata["upload_timestamp"],
                "signed_url": signed_url
            }
            
            logger.info(f"✅ File uploaded successfully: {destination_blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ File upload failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "file_path": str(file_path),
                "destination": destination_blob_name
            }
    
    async def upload_bytes(
        self, 
        data: bytes, 
        destination_blob_name: str,
        content_type: str = None,
        metadata: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Upload bytes data to Cloud Storage
        
        Args:
            data: Bytes data to upload
            destination_blob_name: Destination blob name in storage
            content_type: MIME type of the data
            metadata: Additional metadata to store
        
        Returns:
            Upload result information
        """
        try:
            # Create blob
            blob = self.bucket.blob(destination_blob_name)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Add Helios metadata
            helios_metadata = {
                "helios_version": "1.0.0",
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_size_bytes": len(data),
                "source": "bytes_upload"
            }
            
            if blob.metadata:
                blob.metadata.update(helios_metadata)
            else:
                blob.metadata = helios_metadata
            
            # Upload bytes
            blob.upload_from_string(data)
            
            # Generate URLs
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{destination_blob_name}"
            signed_url = None
            try:
                signed_url = blob.generate_signed_url(
                    expiration=timedelta(hours=24), version="v4", method="GET"
                )
            except Exception:
                signed_url = None
            
            result = {
                "status": "success",
                "bucket": self.bucket_name,
                "blob_name": destination_blob_name,
                "public_url": public_url,
                "size_bytes": len(data),
                "content_type": blob.content_type,
                "metadata": blob.metadata,
                "upload_timestamp": helios_metadata["upload_timestamp"],
                "signed_url": signed_url
            }
            
            logger.info(f"✅ Bytes uploaded successfully: {destination_blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bytes upload failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "destination": destination_blob_name
            }
    
    async def download_file(
        self, 
        source_blob_name: str, 
        destination_file_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """Download a file from Cloud Storage
        
        Args:
            source_blob_name: Source blob name in storage
            destination_file_path: Local destination file path
        
        Returns:
            Download result information
        """
        try:
            destination_file_path = Path(destination_file_path)
            
            # Ensure destination directory exists
            destination_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get blob
            blob = self.bucket.blob(source_blob_name)
            
            if not blob.exists():
                return {
                    "status": "error",
                    "error": "Blob not found",
                    "source_blob": source_blob_name
                }
            
            # Download file
            blob.download_to_filename(str(destination_file_path))
            
            result = {
                "status": "success",
                "source_blob": source_blob_name,
                "destination_file": str(destination_file_path),
                "size_bytes": destination_file_path.stat().st_size,
                "content_type": blob.content_type,
                "metadata": blob.metadata,
                "download_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"✅ File downloaded successfully: {source_blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ File download failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source_blob": source_blob_name,
                "destination": str(destination_file_path)
            }
    
    async def download_bytes(self, source_blob_name: str) -> Dict[str, Any]:
        """Download bytes data from Cloud Storage
        
        Args:
            source_blob_name: Source blob name in storage
        
        Returns:
            Download result with bytes data
        """
        try:
            # Get blob
            blob = self.bucket.blob(source_blob_name)
            
            if not blob.exists():
                return {
                    "status": "error",
                    "error": "Blob not found",
                    "source_blob": source_blob_name
                }
            
            # Download bytes
            data = blob.download_as_bytes()
            
            result = {
                "status": "success",
                "source_blob": source_blob_name,
                "data": data,
                "size_bytes": len(data),
                "content_type": blob.content_type,
                "metadata": blob.metadata,
                "download_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"✅ Bytes downloaded successfully: {source_blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bytes download failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source_blob": source_blob_name
            }
    
    async def delete_blob(self, blob_name: str) -> Dict[str, Any]:
        """Delete a blob from Cloud Storage
        
        Args:
            blob_name: Name of the blob to delete
        
        Returns:
            Deletion result information
        """
        try:
            # Get blob
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                return {
                    "status": "error",
                    "error": "Blob not found",
                    "blob_name": blob_name
                }
            
            # Delete blob
            blob.delete()
            
            result = {
                "status": "success",
                "blob_name": blob_name,
                "deletion_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"✅ Blob deleted successfully: {blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Blob deletion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "blob_name": blob_name
            }
    
    async def list_blobs(
        self, 
        prefix: str = None, 
        delimiter: str = None,
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """List blobs in the bucket
        
        Args:
            prefix: Prefix to filter blobs
            delimiter: Delimiter for hierarchical listing
            max_results: Maximum number of results
        
        Returns:
            List of blobs with metadata
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key("list_blobs", prefix or "all")
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
            
            # List blobs
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                delimiter=delimiter,
                max_results=max_results
            )
            
            blob_list = []
            for blob in blobs:
                blob_info = {
                    "name": blob.name,
                    "size_bytes": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "metadata": blob.metadata or {},
                    "public_url": f"https://storage.googleapis.com/{self.bucket_name}/{blob.name}"
                }
                blob_list.append(blob_info)
            
            result = {
                "status": "success",
                "bucket": self.bucket_name,
                "prefix": prefix,
                "delimiter": delimiter,
                "total_blobs": len(blob_list),
                "blobs": blob_list
            }
            
            # Cache the result
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            
            logger.info(f"✅ Listed {len(blob_list)} blobs in bucket")
            return result
            
        except Exception as e:
            logger.error(f"❌ Blob listing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "bucket": self.bucket_name
            }
    
    async def get_blob_metadata(self, blob_name: str) -> Dict[str, Any]:
        """Get metadata for a specific blob
        
        Args:
            blob_name: Name of the blob
        
        Returns:
            Blob metadata information
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key("blob_metadata", blob_name)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
            
            # Get blob
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                return {
                    "status": "error",
                    "error": "Blob not found",
                    "blob_name": blob_name
                }
            
            # Reload to get latest metadata
            blob.reload()
            
            metadata = {
                "status": "success",
                "blob_name": blob.name,
                "bucket": self.bucket_name,
                "size_bytes": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "metadata": blob.metadata or {},
                "public_url": f"https://storage.googleapis.com/{self.bucket_name}/{blob.name}",
                "md5_hash": blob.md5_hash,
                "etag": blob.etag
            }
            
            # Cache the result
            self._cache[cache_key] = metadata
            self._cache_timestamps[cache_key] = time.time()
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to get blob metadata: {e}")
            return {
                "status": "error",
                "error": str(e),
                "blob_name": blob_name
            }
    
    async def update_blob_metadata(
        self, 
        blob_name: str, 
        metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update metadata for a blob
        
        Args:
            blob_name: Name of the blob
            metadata: New metadata to set
        
        Returns:
            Update result information
        """
        try:
            # Get blob
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                return {
                    "status": "error",
                    "error": "Blob not found",
                    "blob_name": blob_name
                }
            
            # Add update timestamp
            metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Update metadata
            blob.metadata = metadata
            blob.patch()
            
            # Invalidate cache
            cache_key = self._get_cache_key("blob_metadata", blob_name)
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            result = {
                "status": "success",
                "blob_name": blob_name,
                "metadata": metadata,
                "update_timestamp": metadata["last_updated"]
            }
            
            logger.info(f"✅ Blob metadata updated: {blob_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to update blob metadata: {e}")
            return {
                "status": "error",
                "error": str(e),
                "blob_name": blob_name
            }
    
    # Helios-specific methods for asset management
    
    async def store_product_design(
        self, 
        design_data: bytes,
        trend_name: str,
        design_type: str,
        content_type: str = "image/png"
    ) -> Dict[str, Any]:
        """Store a product design asset
        
        Args:
            design_data: Design image data
            trend_name: Associated trend name
            design_type: Type of design
            content_type: MIME type of the design
        
        Returns:
            Storage result information
        """
        try:
            # Generate blob name
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            blob_name = f"{self.asset_dirs['product_designs']}/{trend_name}/{design_type}_{timestamp}.png"
            
            # Add metadata
            metadata = {
                "trend_name": trend_name,
                "design_type": design_type,
                "asset_category": "product_design",
                "generation_timestamp": timestamp,
                "helios_asset": "true"
            }
            
            # Upload design
            result = await self.upload_bytes(
                design_data, 
                blob_name, 
                content_type, 
                metadata
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Product design stored: {blob_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store product design: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trend_name": trend_name,
                "design_type": design_type
            }
    
    async def store_marketing_asset(
        self, 
        asset_data: bytes,
        trend_name: str,
        asset_type: str,
        content_type: str = "image/png"
    ) -> Dict[str, Any]:
        """Store a marketing asset
        
        Args:
            asset_data: Asset data
            trend_name: Associated trend name
            asset_type: Type of marketing asset
            content_type: MIME type of the asset
        
        Returns:
            Storage result information
        """
        try:
            # Generate blob name
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            blob_name = f"{self.asset_dirs['marketing_assets']}/{trend_name}/{asset_type}_{timestamp}.png"
            
            # Add metadata
            metadata = {
                "trend_name": trend_name,
                "asset_type": asset_type,
                "asset_category": "marketing",
                "generation_timestamp": timestamp,
                "helios_asset": "true"
            }
            
            # Upload asset
            result = await self.upload_bytes(
                asset_data, 
                blob_name, 
                content_type, 
                metadata
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Marketing asset stored: {blob_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store marketing asset: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trend_name": trend_name,
                "asset_type": asset_type
            }
    
    async def store_trend_visual(
        self, 
        visual_data: bytes,
        trend_name: str,
        visual_type: str,
        content_type: str = "image/png"
    ) -> Dict[str, Any]:
        """Store a trend visualization
        
        Args:
            visual_data: Visualization data
            trend_name: Associated trend name
            visual_type: Type of visualization
            content_type: MIME type of the visual
        
        Returns:
            Storage result information
        """
        try:
            # Generate blob name
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            blob_name = f"{self.asset_dirs['trend_visuals']}/{trend_name}/{visual_type}_{timestamp}.png"
            
            # Add metadata
            metadata = {
                "trend_name": trend_name,
                "visual_type": visual_type,
                "asset_category": "trend_visual",
                "generation_timestamp": timestamp,
                "helios_asset": "true"
            }
            
            # Upload visual
            result = await self.upload_bytes(
                visual_data, 
                blob_name, 
                content_type, 
                metadata
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Trend visual stored: {blob_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store trend visual: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trend_name": trend_name,
                "visual_type": visual_type
            }
    
    async def get_trend_assets(self, trend_name: str) -> Dict[str, Any]:
        """Get all assets for a specific trend
        
        Args:
            trend_name: Name of the trend
        
        Returns:
            List of trend assets
        """
        try:
            assets = {
                "trend_name": trend_name,
                "product_designs": [],
                "marketing_assets": [],
                "trend_visuals": [],
                "total_assets": 0
            }
            
            # Get product designs
            designs = await self.list_blobs(
                prefix=f"{self.asset_dirs['product_designs']}/{trend_name}/"
            )
            if designs["status"] == "success":
                assets["product_designs"] = designs["blobs"]
                assets["total_assets"] += len(designs["blobs"])
            
            # Get marketing assets
            marketing = await self.list_blobs(
                prefix=f"{self.asset_dirs['marketing_assets']}/{trend_name}/"
            )
            if marketing["status"] == "success":
                assets["marketing_assets"] = marketing["blobs"]
                assets["total_assets"] += len(marketing["blobs"])
            
            # Get trend visuals
            visuals = await self.list_blobs(
                prefix=f"{self.asset_dirs['trend_visuals']}/{trend_name}/"
            )
            if visuals["status"] == "success":
                assets["trend_visuals"] = visuals["blobs"]
                assets["total_assets"] += len(visuals["blobs"])
            
            logger.info(f"✅ Retrieved {assets['total_assets']} assets for trend: {trend_name}")
            return assets
            
        except Exception as e:
            logger.error(f"❌ Failed to get trend assets: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trend_name": trend_name
            }
    
    async def cleanup_old_assets(self, days_old: int = 90) -> Dict[str, Any]:
        """Clean up old assets from storage
        
        Args:
            days_old: Age threshold for cleanup
        
        Returns:
            Cleanup results
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            cleanup_results = {
                "total_deleted": 0,
                "deleted_by_category": {},
                "errors": []
            }
            
            # Process each asset directory
            for category, directory in self.asset_dirs.items():
                try:
                    # List all blobs in directory
                    blobs = await self.list_blobs(prefix=f"{directory}/")
                    
                    if blobs["status"] == "success":
                        deleted_count = 0
                        
                        for blob in blobs["blobs"]:
                            try:
                                # Check if blob is old enough
                                created_date = datetime.fromisoformat(blob["created"])
                                if created_date < cutoff_date:
                                    # Delete old blob
                                    delete_result = await self.delete_blob(blob["name"])
                                    if delete_result["status"] == "success":
                                        deleted_count += 1
                                        cleanup_results["total_deleted"] += 1
                                    
                            except Exception as e:
                                cleanup_results["errors"].append({
                                    "blob": blob["name"],
                                    "error": str(e)
                                })
                        
                        cleanup_results["deleted_by_category"][category] = deleted_count
                        
                except Exception as e:
                    cleanup_results["errors"].append({
                        "category": category,
                        "error": str(e)
                    })
            
            logger.info(f"✅ Asset cleanup completed: {cleanup_results['total_deleted']} assets deleted")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"❌ Asset cleanup failed: {e}")
            return {"error": str(e)}
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics
        
        Returns:
            Storage statistics information
        """
        try:
            stats = {
                "bucket_name": self.bucket_name,
                "project_id": self.project_id,
                "categories": {},
                "total_assets": 0,
                "total_size_bytes": 0,
                "cache_status": {
                    "cached_keys": len(self._cache),
                    "cache_size_mb": len(json.dumps(self._cache)) / (1024 * 1024)
                }
            }
            
            # Get stats for each category
            for category, directory in self.asset_dirs.items():
                try:
                    blobs = await self.list_blobs(prefix=f"{directory}/")
                    
                    if blobs["status"] == "success":
                        category_stats = {
                            "asset_count": len(blobs["blobs"]),
                            "total_size_bytes": sum(blob["size_bytes"] for blob in blobs["blobs"]),
                            "oldest_asset": min((blob["created"] for blob in blobs["blobs"]), default=None),
                            "newest_asset": max((blob["created"] for blob in blobs["blobs"]), default=None)
                        }
                        
                        stats["categories"][category] = category_stats
                        stats["total_assets"] += category_stats["asset_count"]
                        stats["total_size_bytes"] += category_stats["total_size_bytes"]
                        
                except Exception as e:
                    stats["categories"][category] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the Cloud Storage client"""
        try:
            # Clear cache
            self._cache.clear()
            self._cache_timestamps.clear()
            
            # Close client
            self.client.close()
            
            logger.info("✅ Cloud Storage client closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing Cloud Storage client: {e}")


# Convenience functions
async def store_product_design_storage(
    design_data: bytes,
    trend_name: str,
    design_type: str,
    project_id: str,
    bucket_name: str
) -> Dict[str, Any]:
    """Convenience function for storing product design"""
    client = CloudStorageClient(project_id, bucket_name)
    try:
        return await client.store_product_design(design_data, trend_name, design_type)
    finally:
        await client.close()


async def get_trend_assets_storage(trend_name: str, project_id: str, bucket_name: str) -> Dict[str, Any]:
    """Convenience function for getting trend assets"""
    client = CloudStorageClient(project_id, bucket_name)
    try:
        return await client.get_trend_assets(trend_name)
    finally:
        await client.close()
