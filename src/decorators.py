import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional
import time
from .exceptions import NetworkError, RateLimitError


logger = logging.getLogger(__name__)


def retry_on_network_error(
    max_retries: int = 3,
    delay: float = 5.0,
    backoff: float = 2.0,
    exceptions: tuple = (NetworkError,)
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]: 
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Optional[BaseException] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        logger.info(f"Retrying in {current_delay:.1f}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts"
                        )
            
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed without capturing exception")
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Optional[BaseException] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        logger.info(f"Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts"
                        )
            
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed without capturing exception")
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    
    return decorator


def handle_rate_limit(wait_time: int = 900):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                retry_after = e.retry_after or wait_time
                logger.warning(
                    f"Rate limit hit in {func.__name__}. Waiting {retry_after}s..."
                )
                await asyncio.sleep(retry_after)
                logger.info("Retrying after rate limit wait...")
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                retry_after = e.retry_after or wait_time
                logger.warning(
                    f"Rate limit hit in {func.__name__}. Waiting {retry_after}s..."
                )
                time.sleep(retry_after)
                logger.info("Retrying after rate limit wait...")
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_errors(
    error_message: str = "Error occurred",
    reraise: bool = True,
    default_return: Optional[Any] = None
):  
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_message} in {func.__name__}: {e}")
                if reraise:
                    raise
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_message} in {func.__name__}: {e}")
                if reraise:
                    raise
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper 
        else:
            return sync_wrapper 
    
    return decorator

