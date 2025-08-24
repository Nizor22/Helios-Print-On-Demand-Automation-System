from __future__ import annotations

import asyncio
import time
import random
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5           # Number of failures before opening circuit
    recovery_timeout: float = 60.0       # Time to wait before trying half-open
    expected_exception: type = Exception  # Exception type to count as failure
    success_threshold: int = 2           # Number of successes to close circuit
    timeout: float = 30.0                # Timeout for individual operations


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0


@dataclass
class CircuitBreakerStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """Circuit breaker implementation with configurable failure thresholds."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.stats.current_state == CircuitState.OPEN:
                if time.time() - self.stats.last_failure_time > self.config.recovery_timeout:
                    logger.info("Circuit breaker attempting recovery - transitioning to half-open")
                    self.stats.current_state = CircuitState.HALF_OPEN
                else:
                    raise Exception(f"Circuit breaker is OPEN - failing fast. Last failure: {self.stats.last_failure_time}")
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else asyncio.to_thread(func, *args, **kwargs),
                timeout=self.config.timeout
            )
            
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful operation."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()
            
            if self.stats.current_state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    logger.info("Circuit breaker recovered - transitioning to CLOSED")
                    self.stats.current_state = CircuitState.CLOSED
                    self.stats.circuit_closes += 1
                    self.stats.consecutive_successes = 0
    
    async def _on_failure(self, error: Exception):
        """Handle failed operation."""
        async with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = time.time()
            
            if (self.stats.current_state == CircuitState.CLOSED and 
                self.stats.consecutive_failures >= self.config.failure_threshold):
                logger.warning(f"Circuit breaker opening after {self.stats.consecutive_failures} consecutive failures")
                self.stats.current_state = CircuitState.OPEN
                self.stats.circuit_opens += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "state": self.stats.current_state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": (self.stats.successful_requests / self.stats.total_requests 
                           if self.stats.total_requests > 0 else 0),
            "circuit_opens": self.stats.circuit_opens,
            "circuit_closes": self.stats.circuit_closes,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time
        }
    
    def reset(self):
        """Reset circuit breaker to initial state."""
        async def _reset():
            async with self._lock:
                self.stats = CircuitBreakerStats()
                logger.info("Circuit breaker reset to initial state")
        
        # Run reset in background if not in async context
        try:
            asyncio.create_task(_reset())
        except RuntimeError:
            # Not in async context, run synchronously
            pass


class ExponentialBackoffRetry:
    """Exponential backoff retry mechanism with jitter."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await asyncio.to_thread(func, *args, **kwargs)
                return result
                
            except Exception as e:
                last_exception = e
                if attempt == self.config.max_attempts - 1:
                    logger.error(f"Final retry attempt failed: {e}")
                    raise
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
        
        return delay * self.config.backoff_factor


class DeadLetterQueue:
    """Dead letter queue for failed operations that need manual review."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    async def add_failed_operation(self, operation: Dict[str, Any], error: Exception, context: Dict[str, Any] = None):
        """Add failed operation to dead letter queue."""
        async with self._lock:
            if len(self.queue) >= self.max_size:
                # Remove oldest entry
                self.queue.pop(0)
            
            failed_entry = {
                "operation": operation,
                "error": str(error),
                "error_type": type(error).__name__,
                "timestamp": time.time(),
                "context": context or {},
                "retry_count": operation.get("retry_count", 0)
            }
            
            self.queue.append(failed_entry)
            logger.warning(f"Operation added to dead letter queue: {error}")
    
    async def get_failed_operations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get failed operations from queue."""
        async with self._lock:
            return self.queue[-limit:] if limit else self.queue.copy()
    
    async def remove_operation(self, index: int) -> bool:
        """Remove operation from dead letter queue."""
        async with self._lock:
            if 0 <= index < len(self.queue):
                self.queue.pop(index)
                return True
            return False
    
    async def retry_operation(self, index: int, max_retries: int = 3) -> bool:
        """Retry operation from dead letter queue."""
        async with self._lock:
            if 0 <= index < len(self.queue):
                operation = self.queue[index]
                current_retries = operation.get("retry_count", 0)
                
                if current_retries >= max_retries:
                    logger.error(f"Operation exceeded max retries: {operation}")
                    return False
                
                # Update retry count
                operation["retry_count"] = current_retries + 1
                operation["last_retry"] = time.time()
                
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        return {
            "queue_size": len(self.queue),
            "max_size": self.max_size,
            "utilization": len(self.queue) / self.max_size if self.max_size > 0 else 0,
            "oldest_entry": self.queue[0]["timestamp"] if self.queue else None,
            "newest_entry": self.queue[-1]["timestamp"] if self.queue else None
        }


class ErrorRecoveryManager:
    """Central error recovery manager coordinating circuit breakers, retries, and dead letter queue."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}
        self.dead_letter_queue = DeadLetterQueue()
        self._default_circuit_config = CircuitBreakerConfig()
        self._default_retry_config = RetryConfig()
    
    def register_service(self, service_name: str, 
                        circuit_config: Optional[CircuitBreakerConfig] = None,
                        retry_config: Optional[RetryConfig] = None):
        """Register a service with error recovery."""
        self.circuit_breakers[service_name] = CircuitBreaker(
            circuit_config or self._default_circuit_config
        )
        self.retry_configs[service_name] = retry_config or self._default_retry_config
        
        logger.info(f"Registered service '{service_name}' with error recovery")
    
    async def execute_with_recovery(self, service_name: str, func: Callable[..., T], 
                                  *args, **kwargs) -> T:
        """Execute function with full error recovery pipeline."""
        if service_name not in self.circuit_breakers:
            self.register_service(service_name)
        
        circuit_breaker = self.circuit_breakers[service_name]
        retry_config = self.retry_configs[service_name]
        
        try:
            # Execute with circuit breaker protection
            result = await circuit_breaker.call(func, *args, **kwargs)
            return result
            
        except Exception as e:
            # If circuit breaker fails, try with retry mechanism
            try:
                retry = ExponentialBackoffRetry(retry_config)
                result = await retry.execute(func, *args, **kwargs)
                return result
                
            except Exception as retry_error:
                # All recovery attempts failed, add to dead letter queue
                operation_context = {
                    "service": service_name,
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "circuit_state": circuit_breaker.stats.current_state.value
                }
                
                await self.dead_letter_queue.add_failed_operation(
                    operation_context, retry_error, {"service": service_name}
                )
                
                raise retry_error
    
    def get_service_stats(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get error recovery statistics for a specific service."""
        if service_name in self.circuit_breakers:
            return {
                "circuit_breaker": self.circuit_breakers[service_name].get_stats(),
                "retry_config": {
                    "max_attempts": self.retry_configs[service_name].max_attempts,
                    "base_delay": self.retry_configs[service_name].base_delay,
                    "max_delay": self.retry_configs[service_name].max_delay
                }
            }
        return None
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall error recovery statistics."""
        service_stats = {}
        for service_name in self.circuit_breakers:
            service_stats[service_name] = self.get_service_stats(service_name)
        
        return {
            "services": service_stats,
            "dead_letter_queue": self.dead_letter_queue.get_stats(),
            "total_services": len(self.circuit_breakers)
        }
    
    async def reset_service(self, service_name: str):
        """Reset error recovery for a specific service."""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name].reset()
            logger.info(f"Reset error recovery for service '{service_name}'")
    
    async def reset_all_services(self):
        """Reset error recovery for all services."""
        for service_name in self.circuit_breakers:
            await self.reset_service(service_name)
        logger.info("Reset error recovery for all services")


# Convenience functions for common error recovery patterns
async def with_error_recovery(service_name: str, func: Callable[..., T], 
                             *args, **kwargs) -> T:
    """Execute function with error recovery using global manager."""
    from .error_recovery import ErrorRecoveryManager
    
    # Get or create global manager
    if not hasattr(with_error_recovery, '_manager'):
        with_error_recovery._manager = ErrorRecoveryManager()
    
    return await with_error_recovery._manager.execute_with_recovery(
        service_name, func, *args, **kwargs
    )


async def with_circuit_breaker(service_name: str, func: Callable[..., T], 
                              *args, **kwargs) -> T:
    """Execute function with just circuit breaker protection."""
    from .error_recovery import ErrorRecoveryManager
    
    if not hasattr(with_circuit_breaker, '_manager'):
        with_circuit_breaker._manager = ErrorRecoveryManager()
    
    if service_name not in with_circuit_breaker._manager.circuit_breakers:
        with_circuit_breaker._manager.register_service(service_name)
    
    circuit_breaker = with_circuit_breaker._manager.circuit_breakers[service_name]
    return await circuit_breaker.call(func, *args, **kwargs)


async def with_retry(service_name: str, func: Callable[..., T], 
                     *args, **kwargs) -> T:
    """Execute function with just retry mechanism."""
    from .error_recovery import ErrorRecoveryManager
    
    if not hasattr(with_retry, '_manager'):
        with_retry._manager = ErrorRecoveryManager()
    
    if service_name not in with_retry._manager.retry_configs:
        with_retry._manager.register_service(service_name)
    
    retry_config = with_retry._manager.retry_configs[service_name]
    retry = ExponentialBackoffRetry(retry_config)
    return await retry.execute(func, *args, **kwargs)
