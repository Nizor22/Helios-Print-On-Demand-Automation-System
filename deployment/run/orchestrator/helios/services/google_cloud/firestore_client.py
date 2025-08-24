"""
Google Cloud Firestore Client for Helios Autonomous Store
Handles database operations, caching, and performance optimization
Enhanced with advanced query optimizations and descriptive ID support
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from loguru import logger

from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentReference, CollectionReference, FieldFilter
from google.api_core.exceptions import GoogleAPIError

# Import optimized client for advanced operations
from .firestore_optimizations import OptimizedFirestoreClient


@dataclass
class FirestoreConfig:
    """Configuration for Firestore client"""
    project_id: str
    collection_prefix: str = "helios"
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    batch_size: int = 500
    retry_attempts: int = 3


class FirestoreClient:
    """Google Cloud Firestore client for Helios Autonomous Store"""
    
    def __init__(self, project_id: str, collection_prefix: str = "helios", database: str = "helios-data"):
        self.project_id = project_id
        self.collection_prefix = collection_prefix
        self.database = database
        self.client = firestore.Client(project=project_id, database=database)
        
        # Cache for frequently accessed data
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Collections
        self.collections = {
            # Legacy logical names
            "trends": f"{collection_prefix}_trends",
            "products": f"{collection_prefix}_products",
            "audiences": f"{collection_prefix}_audiences",
            "workflows": f"{collection_prefix}_workflows",
            "analytics": f"{collection_prefix}_analytics",
            "quality_gates": f"{collection_prefix}_quality_gates",
            "performance_metrics": f"{collection_prefix}_performance",
            # Canonical collection names per final overview
            "trend_discoveries": "trend_discoveries",
            "product_candidates": "product_candidates",
            "helios_products": "helios_products",
            "workflow_states": "workflow_states",
        }
        
        # Initialize optimized client for advanced operations
        self._optimized_client = None
        
        logger.info(f"✅ Firestore client initialized for project: {project_id}")
    
    def get_optimized_client(self) -> OptimizedFirestoreClient:
        """Get the optimized Firestore client for advanced operations"""
        if self._optimized_client is None:
            self._optimized_client = OptimizedFirestoreClient(self.project_id, self.database)
        return self._optimized_client

    # --------------- Optimized wrappers (delegating to optimized client) ---------------
    async def get_products_by_trend_category(
        self,
        category: str,
        status: Optional[str] = None,
        limit: int = 50,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Optimized query wrapper for products by trend category"""
        optimized = self.get_optimized_client()
        return await optimized.get_products_by_trend_category(
            category=category, status=status, limit=limit, use_cache=use_cache
        )

    async def get_trending_products_batch(
        self,
        trend_scores_min: float = 7.0,
        days_back: int = 30,
        batch_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Optimized batch query wrapper for trending products"""
        optimized = self.get_optimized_client()
        return await optimized.get_trending_products_batch(
            trend_scores_min=trend_scores_min, days_back=days_back, batch_size=batch_size
        )

    async def get_competitor_analysis_by_keywords(
        self,
        keywords: List[str],
        days_back: int = 7,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Optimized query wrapper for competitor analyses by keywords"""
        optimized = self.get_optimized_client()
        return await optimized.get_competitor_analysis_by_keywords(
            keywords=keywords, days_back=days_back, use_cache=use_cache
        )
    
    def _get_collection(self, collection_name: str) -> CollectionReference:
        """Get a Firestore collection reference"""
        return self.client.collection(self.collections.get(collection_name, collection_name))
    
    def _get_cache_key(self, collection: str, doc_id: str = None, query: str = None) -> str:
        """Generate a cache key for caching"""
        if doc_id:
            return f"{collection}:{doc_id}"
        elif query:
            return f"{collection}:query:{hash(query)}"
        else:
            return f"{collection}:all"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    async def create_document(
        self, 
        collection: str, 
        data: Dict[str, Any], 
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new document in Firestore
        
        Args:
            collection: Collection name
            data: Document data
            doc_id: Optional document ID (auto-generated if not provided)
        
        Returns:
            Dictionary containing document information
        """
        try:
            # Add metadata
            data.update({
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "helios_version": "1.0.0"
            })
            
            col_ref = self._get_collection(collection)
            
            # Auto-generate descriptive ID for products if not provided
            if collection == "products" and not doc_id and data.get("product_name"):
                import re
                product_name = data.get("product_name")
                # Create descriptive ID from product name
                clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', product_name)
                descriptive_id = re.sub(r'\s+', '-', clean_name).lower()
                # Ensure it's not too long
                if len(descriptive_id) > 1500:
                    descriptive_id = descriptive_id[:1500]
                doc_id = descriptive_id
                data["descriptive_id"] = descriptive_id
            
            if doc_id:
                doc_ref = col_ref.document(doc_id)
                doc_ref.set(data)
                document_id = doc_id
            else:
                doc_ref = col_ref.add(data)[1]
                document_id = doc_ref.id
            
            # Invalidate cache
            cache_key = self._get_cache_key(collection, document_id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"✅ Created document in {collection}: {document_id}")
            
            return {
                "id": document_id,
                "collection": collection,
                "data": data,
                "created_at": data["created_at"]
            }
            
        except GoogleAPIError as e:
            logger.error(f"❌ Failed to create document in {collection}: {e}")
            raise
    
    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from Firestore
        
        Args:
            collection: Collection name
            doc_id: Document ID
        
        Returns:
            Document data or None if not found
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(collection, doc_id)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
            
            col_ref = self._get_collection(collection)
            doc_ref = col_ref.document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Cache the result
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = time.time()
                
                logger.info(f"✅ Retrieved document from {collection}: {doc_id}")
                return data
            else:
                logger.warning(f"⚠️ Document not found in {collection}: {doc_id}")
                return None
                
        except GoogleAPIError as e:
            logger.error(f"❌ Failed to get document from {collection}: {e}")
            raise
    
    async def update_document(
        self, 
        collection: str, 
        doc_id: str, 
        data: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """Update a document in Firestore
        
        Args:
            collection: Collection name
            doc_id: Document ID
            data: Data to update
            merge: Whether to merge with existing data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add update timestamp
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            col_ref = self._get_collection(collection)
            doc_ref = col_ref.document(doc_id)
            
            if merge:
                doc_ref.update(data)
            else:
                doc_ref.set(data, merge=False)
            
            # Invalidate cache
            cache_key = self._get_cache_key(collection, doc_id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"✅ Updated document in {collection}: {doc_id}")
            return True
            
        except GoogleAPIError as e:
            logger.error(f"❌ Failed to update document in {collection}: {e}")
            return False
    
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Firestore
        
        Args:
            collection: Collection name
            doc_id: Document ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            col_ref = self._get_collection(collection)
            doc_ref = col_ref.document(doc_id)
            doc_ref.delete()
            
            # Invalidate cache
            cache_key = self._get_cache_key(collection, doc_id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"✅ Deleted document from {collection}: {doc_id}")
            return True
            
        except GoogleAPIError as e:
            logger.error(f"❌ Failed to delete document from {collection}: {e}")
            return False
    
    async def query_documents(
        self, 
        collection: str, 
        field: str, 
        operator: str, 
        value: Any,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query documents in Firestore
        
        Args:
            collection: Collection name
            field: Field to query
            operator: Comparison operator
            value: Value to compare against
            limit: Maximum number of results
        
        Returns:
            List of matching documents
        """
        try:
            col_ref = self._get_collection(collection)

            # Use modern filter API to avoid deprecation warnings and enable composite index usage
            supported_ops = {"==", ">", ">=", "<", "<=", "in", "array_contains", "array_contains_any"}
            if operator not in supported_ops:
                raise ValueError(f"Unsupported operator: {operator}")

            query = col_ref.where(filter=FieldFilter(field, operator, value))
            query = query.limit(limit)
            docs = query.stream()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            logger.info(f"✅ Query returned {len(results)} documents from {collection}")
            return results
            
        except GoogleAPIError as e:
            logger.error(f"❌ Query failed on {collection}: {e}")
            raise
    
    async def batch_write(
        self, 
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform batch write operations
        
        Args:
            operations: List of operations to perform
        
        Returns:
            Dictionary containing batch results
        """
        try:
            batch = self.client.batch()
            results = {
                "total_operations": len(operations),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            for op in operations:
                try:
                    op_type = op["type"]
                    collection = op["collection"]
                    data = op["data"]
                    
                    col_ref = self._get_collection(collection)
                    
                    if op_type == "create":
                        if "doc_id" in op:
                            doc_ref = col_ref.document(op["doc_id"])
                            batch.set(doc_ref, data)
                        else:
                            batch.add(col_ref, data)
                        results["successful"] += 1
                        
                    elif op_type == "update":
                        doc_ref = col_ref.document(op["doc_id"])
                        batch.update(doc_ref, data)
                        results["successful"] += 1
                        
                    elif op_type == "delete":
                        doc_ref = col_ref.document(op["doc_id"])
                        batch.delete(doc_ref)
                        results["successful"] += 1
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "operation": op,
                        "error": str(e)
                    })
            
            # Commit batch
            if results["successful"] > 0:
                batch.commit()
            
            logger.info(f"✅ Batch write completed: {results['successful']} successful, {results['failed']} failed")
            return results
            
        except GoogleAPIError as e:
            logger.error(f"❌ Batch write failed: {e}")
            raise

    # --------------- Idempotency helpers ---------------
    async def find_existing_product(
        self,
        *,
        image_sha256: str,
        blueprint_id: int,
        print_provider_id: int,
        limit: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Find existing product in helios_products by idempotency tuple.

        Uses composite index on (image_sha256, blueprint_id, print_provider_id).
        """
        try:
            col_ref = self._get_collection("helios_products")
            query = (
                col_ref.where(filter=FieldFilter("image_sha256", "==", image_sha256))
                .where(filter=FieldFilter("blueprint_id", "==", int(blueprint_id)))
                .where(filter=FieldFilter("print_provider_id", "==", int(print_provider_id)))
                .limit(limit)
            )
            docs = list(query.stream())
            if docs:
                data = docs[0].to_dict()
                data["id"] = docs[0].id
                return data
            return None
        except Exception as e:
            logger.error(f"❌ Idempotency lookup failed: {e}")
            return None

    async def upsert_helios_product(
        self,
        *,
        document_id: Optional[str],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or update a document in helios_products."""
        try:
            col = "helios_products"
            if document_id:
                await self.update_document(col, document_id, data, merge=True)
                return {"id": document_id, "collection": col}
            else:
                return await self.create_document(col, data)
        except Exception as e:
            logger.error(f"❌ Upsert helios_product failed: {e}")
            raise
    
    # Helios-specific methods for trend and product management
    
    async def store_trend_discovery(
        self, 
        trend_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store trend discovery data
        
        Args:
            trend_data: Trend discovery information
        
        Returns:
            Stored trend data
        """
        try:
            # Ensure required fields
            required_fields = ["trend_name", "keywords", "opportunity_score", "source"]
            for field in required_fields:
                if field not in trend_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Add trend-specific metadata
            trend_data.update({
                "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "discovered",
                "processing_stage": "trend_analysis"
            })
            
            result = await self.create_document("trends", trend_data)
            
            # Also store in analytics collection
            analytics_data = {
                "event_type": "trend_discovered",
                "trend_id": result["id"],
                "trend_name": trend_data["trend_name"],
                "opportunity_score": trend_data["opportunity_score"],
                "timestamp": result["created_at"]
            }
            await self.create_document("analytics", analytics_data)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store trend discovery: {e}")
            raise
    
    async def store_audience_analysis(
        self, 
        audience_data: Dict[str, Any],
        trend_id: str
    ) -> Dict[str, Any]:
        """Store audience analysis data
        
        Args:
            audience_data: Audience analysis information
            trend_id: Associated trend ID
        
        Returns:
            Stored audience data
        """
        try:
            # Link to trend
            audience_data["trend_id"] = trend_id
            audience_data["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
            audience_data["status"] = "analyzed"
            
            result = await self.create_document("audiences", audience_data)
            
            # Update trend status
            await self.update_document("trends", trend_id, {
                "processing_stage": "audience_analysis_complete",
                "audience_analysis_id": result["id"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store audience analysis: {e}")
            raise
    
    async def store_product_strategy(
        self, 
        strategy_data: Dict[str, Any],
        trend_id: str,
        audience_id: str
    ) -> Dict[str, Any]:
        """Store product strategy data
        
        Args:
            strategy_data: Product strategy information
            trend_id: Associated trend ID
            audience_id: Associated audience analysis ID
        
        Returns:
            Stored strategy data
        """
        try:
            # Link to trend and audience
            strategy_data.update({
                "trend_id": trend_id,
                "audience_id": audience_id,
                "strategy_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "developed"
            })
            
            result = await self.create_document("products", strategy_data)
            
            # Update trend status
            await self.update_document("trends", trend_id, {
                "processing_stage": "product_strategy_complete",
                "product_strategy_id": result["id"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store product strategy: {e}")
            raise
    
    async def store_workflow_state(
        self, 
        workflow_id: str,
        stage: str,
        status: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Store workflow state information
        
        Args:
            workflow_id: Unique workflow identifier
            stage: Current workflow stage
            status: Stage status
            data: Additional stage data
        
        Returns:
            Stored workflow state
        """
        try:
            workflow_data = {
                "workflow_id": workflow_id,
                "stage": stage,
                "status": status,
                "stage_timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {}
            }
            
            result = await self.create_document("workflows", workflow_data)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store workflow state: {e}")
            raise
    
    async def store_performance_metrics(
        self, 
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store performance metrics
        
        Args:
            metrics: Performance metrics data
        
        Returns:
            Stored metrics data
        """
        try:
            # Add timestamp
            metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            result = await self.create_document("performance_metrics", metrics)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store performance metrics: {e}")
            raise
    
    async def get_trend_workflow_status(self, trend_id: str) -> Dict[str, Any]:
        """Get the complete workflow status for a trend
        
        Args:
            trend_id: Trend ID
        
        Returns:
            Workflow status information
        """
        try:
            # Get trend document
            trend_doc = await self.get_document("trends", trend_id)
            if not trend_doc:
                return {"error": "Trend not found"}
            
            # Get associated documents
            workflow_status = {
                "trend_id": trend_id,
                "trend_name": trend_doc.get("trend_name"),
                "current_stage": trend_doc.get("processing_stage", "unknown"),
                "stages": {}
            }
            
            # Get audience analysis if available
            if "audience_analysis_id" in trend_doc:
                audience_doc = await self.get_document("audiences", trend_doc["audience_analysis_id"])
                if audience_doc:
                    workflow_status["stages"]["audience_analysis"] = {
                        "status": "complete",
                        "timestamp": audience_doc.get("analysis_timestamp"),
                        "confidence": audience_doc.get("confidence_level")
                    }
            
            # Get product strategy if available
            if "product_strategy_id" in trend_doc:
                strategy_doc = await self.get_document("products", trend_doc["product_strategy_id"])
                if strategy_doc:
                    workflow_status["stages"]["product_strategy"] = {
                        "status": "complete",
                        "timestamp": strategy_doc.get("strategy_timestamp"),
                        "profit_margin": strategy_doc.get("profit_margin")
                    }
            
            # Get workflow states
            workflow_states = await self.query_documents(
                "workflows", "workflow_id", "==", trend_id, 100
            )
            
            workflow_status["workflow_states"] = workflow_states
            
            return workflow_status
            
        except Exception as e:
            logger.error(f"❌ Failed to get workflow status: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_data(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old data from Firestore
        
        Args:
            days_old: Age threshold for cleanup
        
        Returns:
            Cleanup results
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            cleanup_results = {
                "collections_processed": [],
                "total_deleted": 0,
                "errors": []
            }
            
            # Process each collection
            for collection_name in self.collections.values():
                try:
                    # Query for old documents
                    old_docs = await self.query_documents(
                        collection_name, "created_at", "<", cutoff_iso, 1000
                    )
                    
                    if old_docs:
                        # Delete old documents
                        delete_ops = []
                        for doc in old_docs:
                            delete_ops.append({
                                "type": "delete",
                                "collection": collection_name,
                                "doc_id": doc["id"]
                            })
                        
                        if delete_ops:
                            batch_result = await self.batch_write(delete_ops)
                            cleanup_results["total_deleted"] += batch_result["successful"]
                        
                        cleanup_results["collections_processed"].append({
                            "collection": collection_name,
                            "documents_deleted": len(old_docs)
                        })
                        
                except Exception as e:
                    cleanup_results["errors"].append({
                        "collection": collection_name,
                        "error": str(e)
                    })
            
            logger.info(f"✅ Cleanup completed: {cleanup_results['total_deleted']} documents deleted")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return {"error": str(e)}
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections
        
        Returns:
            Collection statistics
        """
        try:
            stats = {
                "project_id": self.project_id,
                "collections": {},
                "total_documents": 0,
                "cache_status": {
                    "cached_keys": len(self._cache),
                    "cache_size_mb": len(json.dumps(self._cache)) / (1024 * 1024)
                }
            }
            
            for collection_name in self.collections.values():
                try:
                    # Get collection reference
                    col_ref = self._get_collection(collection_name)
                    
                    # Count documents (this is approximate for large collections)
                    docs = col_ref.limit(1000).stream()
                    doc_count = len(list(docs))
                    
                    stats["collections"][collection_name] = {
                        "document_count": doc_count,
                        "estimated_size_mb": doc_count * 0.001  # Rough estimate
                    }
                    
                    stats["total_documents"] += doc_count
                    
                except Exception as e:
                    stats["collections"][collection_name] = {
                        "error": str(e)
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the Firestore client"""
        try:
            # Clear cache
            self._cache.clear()
            self._cache_timestamps.clear()
            
            # Close client
            self.client.close()
            
            logger.info("✅ Firestore client closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing Firestore client: {e}")


# Convenience functions
async def get_trend_workflow_status_firestore(trend_id: str, project_id: str) -> Dict[str, Any]:
    """Convenience function for getting trend workflow status"""
    client = FirestoreClient(project_id)
    try:
        return await client.get_trend_workflow_status(trend_id)
    finally:
        await client.close()


async def store_trend_discovery_firestore(trend_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """Convenience function for storing trend discovery"""
    client = FirestoreClient(project_id)
    try:
        return await client.store_trend_discovery(trend_data)
    finally:
        await client.close()
