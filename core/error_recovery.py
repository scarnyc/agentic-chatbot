# core/error_recovery.py

import time
import random
import asyncio
import logging
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of failures that can occur."""
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    OVERLOAD = "overload"
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    UNKNOWN = "unknown"

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    retry_on: List[FailureType] = field(default_factory=lambda: [
        FailureType.RATE_LIMIT,
        FailureType.SERVER_ERROR,
        FailureType.OVERLOAD,
        FailureType.NETWORK,
        FailureType.TIMEOUT
    ])

@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    error: Exception
    timestamp: datetime
    failure_type: FailureType

@dataclass
class CircuitBreakerState:
    """State of the circuit breaker."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 5
    recovery_timeout: float = 60.0

class ErrorRecoveryManager:
    """Advanced error recovery with circuit breaker and retry logic."""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreakerState()
        self.retry_history: List[RetryAttempt] = []
        self.success_count = 0
        self.total_attempts = 0
        
    def classify_error(self, error: Exception) -> FailureType:
        """Classify an error to determine retry strategy."""
        if hasattr(error, 'status_code'):
            status_code = error.status_code
            if status_code == 429:
                return FailureType.RATE_LIMIT
            elif status_code in [500, 502, 503]:
                return FailureType.SERVER_ERROR
            elif status_code == 529:
                return FailureType.OVERLOAD
            elif status_code in [401, 403]:
                return FailureType.AUTHENTICATION
            elif status_code == 404:
                return FailureType.PERMISSION
        
        error_str = str(error).lower()
        if any(term in error_str for term in ['timeout', 'timed out']):
            return FailureType.TIMEOUT
        elif any(term in error_str for term in ['network', 'connection', 'dns']):
            return FailureType.NETWORK
        
        return FailureType.UNKNOWN
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if we should retry based on error type and attempt count."""
        failure_type = self.classify_error(error)
        
        # Check if we've exceeded max attempts
        if attempt >= self.retry_config.max_attempts:
            return False
        
        # Check if error type is retryable
        if failure_type not in self.retry_config.retry_on:
            return False
        
        # Check circuit breaker state
        if self.circuit_breaker.state == "OPEN":
            if self._should_attempt_recovery():
                self.circuit_breaker.state = "HALF_OPEN"
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                return False
        
        return True
    
    def calculate_delay(self, attempt: int, failure_type: FailureType) -> float:
        """Calculate delay before retry with exponential backoff and jitter."""
        # Base delay calculation
        if failure_type == FailureType.RATE_LIMIT:
            # More aggressive backoff for rate limits
            delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        elif failure_type == FailureType.OVERLOAD:
            # Linear backoff for overload
            delay = self.retry_config.base_delay * (attempt + 1) * 2
        else:
            # Standard exponential backoff
            delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** (attempt - 1))
        
        # Apply jitter to avoid thundering herd
        jitter = delay * self.retry_config.jitter_factor * random.random()
        delay += jitter
        
        # Cap at max delay
        return min(delay, self.retry_config.max_delay)
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.circuit_breaker.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.circuit_breaker.last_failure_time
        return time_since_failure.total_seconds() >= self.circuit_breaker.recovery_timeout
    
    def _record_failure(self, error: Exception):
        """Record a failure and update circuit breaker state."""
        self.circuit_breaker.failure_count += 1
        self.circuit_breaker.last_failure_time = datetime.now()
        
        if (self.circuit_breaker.failure_count >= self.circuit_breaker.failure_threshold and 
            self.circuit_breaker.state == "CLOSED"):
            self.circuit_breaker.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.circuit_breaker.failure_count} failures")
    
    def _record_success(self):
        """Record a successful operation."""
        self.success_count += 1
        
        if self.circuit_breaker.state == "HALF_OPEN":
            # Reset circuit breaker on successful recovery
            self.circuit_breaker.state = "CLOSED"
            self.circuit_breaker.failure_count = 0
            self.circuit_breaker.last_failure_time = None
            logger.info("Circuit breaker closed after successful recovery")
        elif self.circuit_breaker.state == "CLOSED":
            # Gradually reduce failure count on success
            self.circuit_breaker.failure_count = max(0, self.circuit_breaker.failure_count - 1)
    
    async def execute_with_retry(
        self, 
        operation: Callable,
        operation_name: str = "API_CALL",
        notify_callback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> Any:
        """Execute an operation with automatic retry logic."""
        self.total_attempts += 1
        last_error = None
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                # Notify about retry attempt if callback provided
                if notify_callback and attempt > 1:
                    await notify_callback({
                        "type": "retry_attempt",
                        "attempt": attempt,
                        "max_attempts": self.retry_config.max_attempts,
                        "operation": operation_name
                    })
                
                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Record success
                self._record_success()
                
                if attempt > 1:
                    logger.info(f"{operation_name} succeeded on attempt {attempt}")
                    if notify_callback:
                        await notify_callback({
                            "type": "retry_success",
                            "attempt": attempt,
                            "operation": operation_name
                        })
                
                return result
                
            except Exception as error:
                last_error = error
                failure_type = self.classify_error(error)
                
                logger.warning(f"{operation_name} failed on attempt {attempt}: {error} (type: {failure_type})")
                
                # Record the failure
                self._record_failure(error)
                
                # Check if we should retry
                if not self.should_retry(error, attempt):
                    logger.error(f"{operation_name} failed permanently after {attempt} attempts")
                    break
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt, failure_type)
                
                # Record retry attempt
                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    delay=delay,
                    error=error,
                    timestamp=datetime.now(),
                    failure_type=failure_type
                )
                self.retry_history.append(retry_attempt)
                
                # Notify about retry delay
                if notify_callback:
                    await notify_callback({
                        "type": "retry_delay",
                        "attempt": attempt,
                        "delay": delay,
                        "failure_type": failure_type.value,
                        "operation": operation_name
                    })
                
                logger.info(f"Retrying {operation_name} in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_attempts})")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if notify_callback:
            await notify_callback({
                "type": "retry_exhausted",
                "operation": operation_name,
                "final_error": str(last_error)
            })
        
        raise last_error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry and circuit breaker statistics."""
        recent_failures = [
            attempt for attempt in self.retry_history 
            if attempt.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        failure_types = {}
        for attempt in recent_failures:
            failure_type = attempt.failure_type.value
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        success_rate = (self.success_count / self.total_attempts * 100) if self.total_attempts > 0 else 100
        
        return {
            "success_count": self.success_count,
            "total_attempts": self.total_attempts,
            "success_rate_percent": round(success_rate, 2),
            "recent_failures_1h": len(recent_failures),
            "failure_types_1h": failure_types,
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "last_failure": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
            },
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "base_delay": self.retry_config.base_delay,
                "max_delay": self.retry_config.max_delay
            }
        }

# Global error recovery manager
error_recovery = ErrorRecoveryManager()

def get_error_recovery_stats() -> Dict[str, Any]:
    """Get global error recovery statistics."""
    return error_recovery.get_stats()