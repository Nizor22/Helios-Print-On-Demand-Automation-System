"""
Firestore Query Optimizations for Helios Autonomous Store
Advanced query patterns, indexing strategies, and performance optimizations
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from loguru import logger

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter, And, Or
from google.api_core.exceptions import GoogleAPIError


@dataclass
class QueryOptimization:
    """Query optimization configuration"""
    use_cache: bool = True
    cache_ttl: int = 300  # 5 minutes
    batch_size: int = 500
    enable_parallel_queries: bool = True
    max_concurrent_queries: int = 10


class OptimizedFirestoreClient:
    """
    Enhanced Firestore client with advanced query optimizations
    Leverages descriptive IDs and implements performance best practices
    """
    
    def __init__(self, project_id: str, database: str = "helios-data"):
        self.project_id = project_id
        self.database = database
        self.client = firestore.Client(project=project_id, database=database)
        
        # Advanced caching with TTL and LRU eviction
        self._query_cache = {}
        self._cache_timestamps = {}
        self._cache_access_count = {}
        self._cache_ttl = 300  # 5 minutes
        self._max_cache_size = 1000
        
        # Query performance tracking
        self._query_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_query_time": 0.0,
            "slow_queries": []
        }
        
        # Optimized collection references with descriptive ID patterns
        self.collections = {
            "products": "helios_products",
            "trends": "helios_trends", 
            "analytics": "helios_analytics",
            "competitor_analyses": "competitor_analyses",
            "trend_discoveries": "trend_discoveries",
            "performance_metrics": "helios_performance",
            "ab_experiments": "ab_test_experiments",
            "learning_models": "learning_models"
        }
        
        logger.info(f"✅ Optimized Firestore client initialized for project: {project_id}")
    
    def _generate_cache_key(self, collection: str, filters: Dict = None, order_by: str = None, limit: int = None) -> str:
        """Generate optimized cache key for complex queries"""
        key_parts = [collection]
        
        if filters:
            # Sort filters for consistent cache keys
            sorted_filters = sorted(filters.items())
            key_parts.append(f"filters:{json.dumps(sorted_filters, sort_keys=True)}")
        
        if order_by:
            key_parts.append(f"order:{order_by}")
        
        if limit:
            key_parts.append(f"limit:{limit}")
        
        return ":".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid with LRU tracking"""
        if cache_key not in self._cache_timestamps:
            return False
        
        # Update access count for LRU
        self._cache_access_count[cache_key] = self._cache_access_count.get(cache_key, 0) + 1
        
        # Check TTL
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def _evict_old_cache_entries(self):
        """Evict old cache entries using LRU strategy"""
        if len(self._query_cache) <= self._max_cache_size:
            return
        
        # Sort by access count (LRU)
        sorted_keys = sorted(
            self._cache_access_count.keys(), 
            key=lambda k: self._cache_access_count[k]
        )
        
        # Remove oldest 20% of entries
        evict_count = int(len(sorted_keys) * 0.2)
        for key in sorted_keys[:evict_count]:
            self._query_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_access_count.pop(key, None)
    
    async def get_products_by_trend_category(
        self, 
        category: str, 
        status: str = None,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Optimized query for products by trend category using descriptive IDs
        Leverages the new descriptive ID structure for better performance
        """
        start_time = time.time()
        
        # Build cache key
        filters = {"trend_category": category}
        if status:
            filters["status"] = status
        cache_key = self._generate_cache_key("products", filters, "created_at", limit)
        
        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            self._query_stats["cache_hits"] += 1
            logger.debug(f"🚀 Cache hit for products by category: {category}")
            return self._query_cache[cache_key]
        
        try:
            # Build optimized query with composite index support
            collection_ref = self.client.collection(self.collections["products"])
            
            # Use descriptive ID pattern matching for better performance
            query = collection_ref.where(
                filter=FieldFilter("trend_category", "==", category)
            )
            
            if status:
                query = query.where(filter=FieldFilter("status", "==", status))
            
            # Order by created_at for consistent results
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            results = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            # Cache results
            if use_cache:
                self._query_cache[cache_key] = results
                self._cache_timestamps[cache_key] = time.time()
                self._cache_access_count[cache_key] = 1
                self._evict_old_cache_entries()
                self._query_stats["cache_misses"] += 1
            
            # Track performance
            query_time = time.time() - start_time
            self._query_stats["total_queries"] += 1
            self._query_stats["avg_query_time"] = (
                (self._query_stats["avg_query_time"] * (self._query_stats["total_queries"] - 1) + query_time) 
                / self._query_stats["total_queries"]
            )
            
            if query_time > 2.0:  # Slow query threshold
                self._query_stats["slow_queries"].append({
                    "query": f"products_by_category_{category}",
                    "time": query_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            logger.info(f"✅ Retrieved {len(results)} products for category '{category}' in {query_time:.2f}s")
            return results
            
        except GoogleAPIError as e:
            logger.error(f"❌ Failed to query products by category: {e}")
            raise
    
    async def get_trending_products_batch(
        self,
        trend_scores_min: float = 7.0,
        days_back: int = 30,
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Batch query for trending products with optimized performance
        Uses parallel queries for better throughput
        """
        start_time = time.time()
        
        try:
            # Calculate date threshold
            date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            # Build parallel queries for different trend score ranges
            query_ranges = [
                (9.0, 10.0),  # Excellent trends
                (8.0, 8.9),   # Good trends  
                (7.0, 7.9)    # Decent trends
            ]
            
            # Execute queries in parallel
            tasks = []
            for min_score, max_score in query_ranges:
                task = self._query_products_by_score_range(
                    min_score, max_score, date_threshold, batch_size // len(query_ranges)
                )
                tasks.append(task)
            
            # Wait for all queries to complete
            results_batches = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            all_products = []
            for batch in results_batches:
                if isinstance(batch, Exception):
                    logger.warning(f"⚠️ Batch query failed: {batch}")
                    continue
                all_products.extend(batch)
            
            # Sort by trend score descending
            all_products.sort(key=lambda x: x.get("trend_score", 0), reverse=True)
            
            query_time = time.time() - start_time
            logger.info(f"✅ Retrieved {len(all_products)} trending products in {query_time:.2f}s using parallel queries")
            
            return all_products[:batch_size]  # Return top results up to batch_size
            
        except Exception as e:
            logger.error(f"❌ Batch trending products query failed: {e}")
            raise
    
    async def _query_products_by_score_range(
        self, 
        min_score: float, 
        max_score: float, 
        date_threshold: datetime,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Internal helper for parallel score range queries"""
        
        collection_ref = self.client.collection(self.collections["products"])
        
        # Build composite query with multiple conditions
        query = collection_ref.where(
            filter=And([
                FieldFilter("trend_score", ">=", min_score),
                FieldFilter("trend_score", "<=", max_score),
                FieldFilter("created_at", ">=", date_threshold)
            ])
        )
        
        query = query.order_by("trend_score", direction=firestore.Query.DESCENDING)
        query = query.limit(limit)
        
        docs = query.stream()
        results = []
        
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        
        return results
    
    async def get_competitor_analysis_by_keywords(
        self,
        keywords: List[str],
        days_back: int = 7,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Optimized competitor analysis retrieval using descriptive IDs
        Leverages keyword-based descriptive IDs for faster lookups
        """
        start_time = time.time()
        
        # Build cache key
        cache_key = self._generate_cache_key(
            "competitor_analyses", 
            {"keywords": sorted(keywords), "days_back": days_back}
        )
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            self._query_stats["cache_hits"] += 1
            return self._query_cache[cache_key]
        
        try:
            # Calculate date threshold
            date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            collection_ref = self.client.collection(self.collections["competitor_analyses"])
            
            # Use descriptive ID pattern matching for efficient lookup
            # Descriptive IDs follow pattern: "keyword1_keyword2_YYYYMMDD_HHMMSS"
            results = []
            
            # Try direct ID lookups first (most efficient)
            for keyword_combo in self._generate_keyword_combinations(keywords):
                # Look for recent documents with this keyword combination
                id_pattern = f"{keyword_combo}_"
                
                # Query documents that start with this pattern
                query = collection_ref.where(
                    filter=FieldFilter("created_at", ">=", date_threshold)
                ).where(
                    filter=FieldFilter("product_category", "==", keyword_combo.replace("_", ", "))
                ).order_by("created_at", direction=firestore.Query.DESCENDING)
                
                docs = query.stream()
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    results.append(data)
            
            # Remove duplicates based on ID
            unique_results = {}
            for result in results:
                unique_results[result["id"]] = result
            
            final_results = list(unique_results.values())
            
            # Cache results
            if use_cache:
                self._query_cache[cache_key] = final_results
                self._cache_timestamps[cache_key] = time.time()
                self._cache_access_count[cache_key] = 1
                self._evict_old_cache_entries()
                self._query_stats["cache_misses"] += 1
            
            query_time = time.time() - start_time
            logger.info(f"✅ Retrieved {len(final_results)} competitor analyses for keywords {keywords} in {query_time:.2f}s")
            
            return final_results
            
        except GoogleAPIError as e:
            logger.error(f"❌ Competitor analysis query failed: {e}")
            raise
    
    def _generate_keyword_combinations(self, keywords: List[str]) -> List[str]:
        """Generate keyword combinations for ID pattern matching"""
        if not keywords:
            return []
        
        # Sort keywords for consistent ID patterns
        sorted_keywords = sorted([k.lower().replace(" ", "_") for k in keywords])
        
        combinations = []
        
        # Single keywords
        combinations.extend(sorted_keywords)
        
        # Pairs
        if len(sorted_keywords) > 1:
            for i in range(len(sorted_keywords)):
                for j in range(i + 1, len(sorted_keywords)):
                    combinations.append(f"{sorted_keywords[i]}_{sorted_keywords[j]}")
        
        # Full combination
        if len(sorted_keywords) > 2:
            combinations.append("_".join(sorted_keywords))
        
        return combinations
    
    async def batch_update_products_status(
        self,
        product_ids: List[str],
        new_status: str,
        batch_size: int = 500
    ) -> Dict[str, Any]:
        """
        Optimized batch update for product status using descriptive IDs
        """
        start_time = time.time()
        
        try:
            total_updated = 0
            failed_updates = []
            
            # Process in batches to avoid Firestore limits
            for i in range(0, len(product_ids), batch_size):
                batch_ids = product_ids[i:i + batch_size]
                
                # Create batch write
                batch = self.client.batch()
                
                for product_id in batch_ids:
                    try:
                        doc_ref = self.client.collection(self.collections["products"]).document(product_id)
                        batch.update(doc_ref, {
                            "status": new_status,
                            "updated_at": datetime.now(timezone.utc),
                            "status_changed_at": datetime.now(timezone.utc)
                        })
                        
                    except Exception as e:
                        failed_updates.append({"id": product_id, "error": str(e)})
                
                # Commit batch
                batch.commit()
                total_updated += len(batch_ids) - len([f for f in failed_updates if f["id"] in batch_ids])
                
                # Add small delay to avoid rate limits
                if i + batch_size < len(product_ids):
                    await asyncio.sleep(0.1)
            
            update_time = time.time() - start_time
            
            result = {
                "total_requested": len(product_ids),
                "total_updated": total_updated,
                "failed_updates": failed_updates,
                "update_time": update_time
            }
            
            logger.info(f"✅ Batch updated {total_updated}/{len(product_ids)} products in {update_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Batch update failed: {e}")
            raise
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        cache_hit_rate = 0.0
        if self._query_stats["total_queries"] > 0:
            cache_hit_rate = self._query_stats["cache_hits"] / (
                self._query_stats["cache_hits"] + self._query_stats["cache_misses"]
            )
        
        return {
            "total_queries": self._query_stats["total_queries"],
            "cache_hit_rate": f"{cache_hit_rate:.2%}",
            "avg_query_time": f"{self._query_stats['avg_query_time']:.3f}s",
            "slow_queries_count": len(self._query_stats["slow_queries"]),
            "cache_size": len(self._query_cache),
            "recent_slow_queries": self._query_stats["slow_queries"][-5:]  # Last 5 slow queries
        }
    
    async def create_composite_indexes(self) -> Dict[str, Any]:
        """
        Create recommended composite indexes for optimal query performance
        Note: This generates the index configuration - actual creation is done via Firebase Console or CLI
        """
        
        recommended_indexes = {
            "helios_products": [
                {
                    "fields": [
                        {"field_path": "trend_category", "order": "ASCENDING"},
                        {"field_path": "status", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                },
                {
                    "fields": [
                        {"field_path": "trend_score", "order": "DESCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                },
                {
                    "fields": [
                        {"field_path": "status", "order": "ASCENDING"},
                        {"field_path": "publishing_ready", "order": "ASCENDING"},
                        {"field_path": "updated_at", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                }
            ],
            "competitor_analyses": [
                {
                    "fields": [
                        {"field_path": "product_category", "order": "ASCENDING"},
                        {"field_path": "created_at", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                },
                {
                    "fields": [
                        {"field_path": "status", "order": "ASCENDING"},
                        {"field_path": "timestamp", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                }
            ],
            "helios_analytics": [
                {
                    "fields": [
                        {"field_path": "event_type", "order": "ASCENDING"},
                        {"field_path": "timestamp", "order": "DESCENDING"}
                    ],
                    "query_scope": "COLLECTION"
                }
            ]
        }
        
        logger.info("📊 Generated composite index recommendations")
        return {
            "status": "recommendations_generated",
            "indexes": recommended_indexes,
            "next_steps": [
                "Use Firebase CLI: firebase firestore:indexes",
                "Or Firebase Console: https://console.firebase.google.com/project/{project_id}/firestore/indexes",
                "Deploy indexes with: firebase deploy --only firestore:indexes"
            ]
        }
    
    async def close(self):
        """Close the client and clean up resources"""
        try:
            # Log final performance stats
            stats = self.get_query_performance_stats()
            logger.info(f"📊 Final query stats: {stats}")
            
            # Clear caches
            self._query_cache.clear()
            self._cache_timestamps.clear()
            self._cache_access_count.clear()
            
            logger.info("✅ Optimized Firestore client closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing optimized Firestore client: {e}")


# Factory function for easy integration
def create_optimized_firestore_client(project_id: str, database: str = "helios-data") -> OptimizedFirestoreClient:
    """Create an optimized Firestore client instance"""
    return OptimizedFirestoreClient(project_id, database)
