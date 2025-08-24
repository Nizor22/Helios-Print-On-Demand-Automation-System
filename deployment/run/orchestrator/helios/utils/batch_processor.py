"""
Batch Processing Utility for Helios Autonomous Store
Handles bulk operations, parallel processing, and batch management
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Callable, Optional, Union, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

try:
    from google.cloud import firestore
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False

from .performance_monitor import monitor_performance, get_performance_monitor
from .error_handler import handle_errors, get_error_handler

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for batch items


class BatchStatus(Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"


class ProcessingStrategy(Enum):
    """Processing strategy for batch operations"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CHUNKED = "chunked"
    STREAMING = "streaming"


@dataclass
class BatchItem(Generic[T]):
    """Individual item in a batch"""
    
    id: str
    data: T
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "data": self.data,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


@dataclass
class BatchResult:
    """Result of batch processing"""
    
    batch_id: str
    total_items: int
    successful_items: int
    failed_items: int
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time: Optional[float] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.successful_items / self.total_items) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "batch_id": self.batch_id,
            "total_items": self.total_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time": self.processing_time,
            "success_rate": self.success_rate,
            "errors": self.errors,
            "metadata": self.metadata
        }


class BatchProcessor:
    """
    Batch processing utility for handling large-scale operations
    """
    
    def __init__(
        self, 
        project_id: str = None,
        max_workers: int = None,
        chunk_size: int = 100,
        enable_monitoring: bool = True
    ):
        self.project_id = project_id
        self.max_workers = max_workers or min(multiprocessing.cpu_count() * 2, 32)
        self.chunk_size = chunk_size
        self.enable_monitoring = enable_monitoring
        
        # Initialize clients
        self.firestore_client = None
        self.pubsub_client = None
        
        if self.project_id and GOOGLE_CLOUD_AVAILABLE:
            try:
                if GOOGLE_CLOUD_AVAILABLE:
                    self.firestore_client = firestore.Client(project=project_id)
                if PUBSUB_AVAILABLE:
                    self.pubsub_client = pubsub_v1.PublisherClient()
                logger.info(f"Initialized batch processor clients for project: {project_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize batch processor clients: {str(e)}")
        elif not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud libraries not available, skipping batch processor client setup")
        
        # Performance monitor
        self.performance_monitor = get_performance_monitor(project_id) if enable_monitoring else None
        
        # Error handler
        self.error_handler = get_error_handler(project_id)
    
    async def process_batch(
        self,
        items: List[T],
        processor_func: Callable[[T], Any],
        batch_id: str = None,
        strategy: ProcessingStrategy = ProcessingStrategy.CHUNKED,
        **kwargs
    ) -> BatchResult:
        """
        Process a batch of items using the specified strategy
        
        Args:
            items: List of items to process
            processor_func: Function to process each item
            batch_id: Unique identifier for the batch
            strategy: Processing strategy to use
            **kwargs: Additional arguments for the processor function
            
        Returns:
            BatchResult containing processing results
        """
        
        if not items:
            return BatchResult(
                batch_id=batch_id or "empty_batch",
                total_items=0,
                successful_items=0,
                failed_items=0,
                start_time=datetime.utcnow()
            )
        
        batch_id = batch_id or f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting batch processing: {batch_id} with {len(items)} items using {strategy.value}")
        
        try:
            # Store batch metadata
            await self._store_batch_metadata(batch_id, items, strategy, start_time)
            
            # Process based on strategy
            if strategy == ProcessingStrategy.SEQUENTIAL:
                result = await self._process_sequential(items, processor_func, batch_id, **kwargs)
            elif strategy == ProcessingStrategy.PARALLEL:
                result = await self._process_parallel(items, processor_func, batch_id, **kwargs)
            elif strategy == ProcessingStrategy.CHUNKED:
                result = await self._process_chunked(items, processor_func, batch_id, **kwargs)
            elif strategy == ProcessingStrategy.STREAMING:
                result = await self._process_streaming(items, processor_func, batch_id, **kwargs)
            else:
                raise ValueError(f"Unknown processing strategy: {strategy}")
            
            # Update result with timing
            result.batch_id = batch_id
            result.start_time = start_time
            result.end_time = datetime.utcnow()
            result.processing_time = (result.end_time - start_time).total_seconds()
            
            # Store results
            await self._store_batch_results(batch_id, result)
            
            # Send completion notification
            await self._send_completion_notification(batch_id, result)
            
            logger.info(
                f"Batch {batch_id} completed: {result.successful_items}/{result.total_items} "
                f"successful in {result.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Batch processing failed for {batch_id}: {str(e)}")
            
            # Create failed result
            failed_result = BatchResult(
                batch_id=batch_id,
                total_items=len(items),
                successful_items=0,
                failed_items=len(items),
                start_time=start_time,
                end_time=datetime.utcnow(),
                processing_time=(datetime.utcnow() - start_time).total_seconds(),
                errors=[{"error": str(e), "type": "batch_failure"}]
            )
            
            # Store failed result
            await self._store_batch_results(batch_id, failed_result)
            
            # Handle error
            await self.error_handler.handle_error(
                e, 
                context={"batch_id": batch_id, "strategy": strategy.value}
            )
            
            return failed_result
    
    async def _process_sequential(
        self, 
        items: List[T], 
        processor_func: Callable[[T], Any], 
        batch_id: str,
        **kwargs
    ) -> BatchResult:
        """Process items sequentially"""
        
        successful_items = 0
        failed_items = 0
        errors = []
        
        for i, item in enumerate(items):
            try:
                if asyncio.iscoroutinefunction(processor_func):
                    result = await processor_func(item, **kwargs)
                else:
                    result = processor_func(item, **kwargs)
                
                successful_items += 1
                logger.debug(f"Processed item {i+1}/{len(items)} in batch {batch_id}")
                
            except Exception as e:
                failed_items += 1
                error_info = {"item_index": i, "item_id": getattr(item, 'id', str(i)), "error": str(e)}
                errors.append(error_info)
                
                # Handle individual item error
                await self.error_handler.handle_error(
                    e, 
                    context={"batch_id": batch_id, "item_index": i, "item_id": getattr(item, 'id', str(i))}
                )
        
        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors
        )
    
    async def _process_parallel(
        self, 
        items: List[T], 
        processor_func: Callable[[T], Any], 
        batch_id: str,
        **kwargs
    ) -> BatchResult:
        """Process items in parallel using asyncio"""
        
        async def process_item(item: T, index: int) -> Dict[str, Any]:
            try:
                if asyncio.iscoroutinefunction(processor_func):
                    result = await processor_func(item, **kwargs)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        result = await loop.run_in_executor(executor, processor_func, item, **kwargs)
                
                return {"success": True, "index": index, "result": result}
                
            except Exception as e:
                return {"success": False, "index": index, "error": str(e)}
        
        # Create tasks for all items
        tasks = [process_item(item, i) for i, item in enumerate(items)]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_items = 0
        failed_items = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_items += 1
                errors.append({"error": str(result), "type": "task_exception"})
            elif result["success"]:
                successful_items += 1
            else:
                failed_items += 1
                errors.append(result)
        
        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors
        )
    
    async def _process_chunked(
        self, 
        items: List[T], 
        processor_func: Callable[[T], Any], 
        batch_id: str,
        **kwargs
    ) -> BatchResult:
        """Process items in chunks with controlled concurrency"""
        
        successful_items = 0
        failed_items = 0
        errors = []
        
        # Process in chunks
        for chunk_start in range(0, len(items), self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, len(items))
            chunk = items[chunk_start:chunk_end]
            
            logger.debug(f"Processing chunk {chunk_start//self.chunk_size + 1} for batch {batch_id}")
            
            # Process chunk in parallel
            chunk_result = await self._process_parallel(chunk, processor_func, f"{batch_id}_chunk_{chunk_start//self.chunk_size}", **kwargs)
            
            successful_items += chunk_result.successful_items
            failed_items += chunk_result.failed_items
            errors.extend(chunk_result.errors)
            
            # Small delay between chunks to prevent overwhelming
            await asyncio.sleep(0.1)
        
        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors
        )
    
    async def _process_streaming(
        self, 
        items: List[T], 
        processor_func: Callable[[T], Any], 
        batch_id: str,
        **kwargs
    ) -> BatchResult:
        """Process items in streaming fashion with backpressure control"""
        
        # Create a semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_item_with_semaphore(item: T, index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(processor_func):
                        result = await processor_func(item, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            result = await loop.run_in_executor(executor, processor_func, item, **kwargs)
                    
                    return {"success": True, "index": index, "result": result}
                    
                except Exception as e:
                    return {"success": False, "index": index, "error": str(e)}
        
        # Create tasks with controlled concurrency
        tasks = [process_item_with_semaphore(item, i) for i, item in enumerate(items)]
        
        # Process with backpressure control
        results = []
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            
            # Log progress
            if len(results) % 10 == 0:
                logger.info(f"Processed {len(results)}/{len(items)} items in batch {batch_id}")
        
        # Process results
        successful_items = sum(1 for r in results if r["success"])
        failed_items = len(results) - successful_items
        errors = [r for r in results if not r["success"]]
        
        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            successful_items=successful_items,
            failed_items=failed_items,
            errors=errors
        )
    
    async def _store_batch_metadata(
        self, 
        batch_id: str, 
        items: List[T], 
        strategy: ProcessingStrategy, 
        start_time: datetime
    ):
        """Store batch metadata in Firestore"""
        
        if not self.firestore_client:
            return
        
        try:
            collection_name = "batch_metadata"
            document_id = batch_id
            
            metadata = {
                "batch_id": batch_id,
                "total_items": len(items),
                "strategy": strategy.value,
                "start_time": start_time,
                "status": BatchStatus.PROCESSING.value,
                "created_at": datetime.utcnow()
            }
            
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            doc_ref.set(metadata)
            
        except Exception as e:
            logger.error(f"Failed to store batch metadata: {str(e)}")
    
    async def _store_batch_results(self, batch_id: str, result: BatchResult):
        """Store batch results in Firestore"""
        
        if not self.firestore_client:
            return
        
        try:
            collection_name = "batch_results"
            document_id = batch_id
            
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            doc_ref.set(result.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to store batch results: {str(e)}")
    
    async def _send_completion_notification(self, batch_id: str, result: BatchResult):
        """Send batch completion notification via Pub/Sub"""
        
        if not self.pubsub_client:
            return
        
        try:
            topic_path = self.pubsub_client.topic_path(self.project_id, "helios-batch-completions")
            
            notification_data = {
                "batch_id": batch_id,
                "status": "completed",
                "result": result.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            future = self.pubsub_client.publish(
                topic_path,
                json.dumps(notification_data).encode("utf-8")
            )
            future.result()
            
        except Exception as e:
            logger.error(f"Failed to send completion notification: {str(e)}")
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific batch"""
        
        if not self.firestore_client:
            return None
        
        try:
            # Check metadata
            metadata_doc = self.firestore_client.collection("batch_metadata").document(batch_id).get()
            if metadata_doc.exists:
                metadata = metadata_doc.to_dict()
            else:
                return None
            
            # Check results
            results_doc = self.firestore_client.collection("batch_results").document(batch_id).get()
            if results_doc.exists:
                results = results_doc.to_dict()
                metadata.update(results)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get batch status: {str(e)}")
            return None
    
    async def list_batches(
        self, 
        status: BatchStatus = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List batches with optional filtering"""
        
        if not self.firestore_client:
            return []
        
        try:
            collection_ref = self.firestore_client.collection("batch_metadata")
            
            if status:
                query = collection_ref.where("status", "==", status.value)
            else:
                query = collection_ref
            
            query = query.order_by("created_at", direction="descending").limit(limit)
            
            docs = query.stream()
            batches = [doc.to_dict() for doc in docs]
            
            return batches
            
        except Exception as e:
            logger.error(f"Failed to list batches: {str(e)}")
            return []
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch (if supported by the strategy)"""
        
        # This is a simplified implementation
        # In a real system, you'd need to implement proper cancellation logic
        # based on the processing strategy and current state
        
        try:
            # Update metadata to cancelled
            if self.firestore_client:
                doc_ref = self.firestore_client.collection("batch_metadata").document(batch_id)
                doc_ref.update({"status": BatchStatus.CANCELLED.value})
            
            logger.info(f"Batch {batch_id} marked as cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel batch {batch_id}: {str(e)}")
            return False


# Utility functions for common batch operations
async def process_products_batch(
    products: List[Dict[str, Any]], 
    processor_func: Callable,
    batch_size: int = 50
) -> BatchResult:
    """Process a batch of products"""
    
    processor = BatchProcessor()
    return await processor.process_batch(
        items=products,
        processor_func=processor_func,
        strategy=ProcessingStrategy.CHUNKED,
        chunk_size=batch_size
    )


async def process_trends_batch(
    trends: List[Dict[str, Any]], 
    processor_func: Callable,
    batch_size: int = 100
) -> BatchResult:
    """Process a batch of trends"""
    
    processor = BatchProcessor()
    return await processor.process_batch(
        items=trends,
        processor_func=processor_func,
        strategy=ProcessingStrategy.STREAMING,
        chunk_size=batch_size
    )


# Example usage
if __name__ == "__main__":
    async def example_processor(item: Dict[str, Any]) -> Dict[str, Any]:
        """Example processor function"""
        await asyncio.sleep(0.1)  # Simulate work
        return {"processed": True, "item_id": item.get("id")}
    
    async def main():
        # Create sample data
        items = [{"id": f"item_{i}", "data": f"data_{i}"} for i in range(100)]
        
        # Process batch
        processor = BatchProcessor()
        result = await processor.process_batch(
            items=items,
            processor_func=example_processor,
            strategy=ProcessingStrategy.CHUNKED
        )
        
        print(f"Batch processing completed: {result.to_dict()}")
    
    # Run example
    asyncio.run(main())
