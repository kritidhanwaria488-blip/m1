"""
Phase 4.0: HTTP Fetcher Module

Handles fetching of URLs with rate limiting, timeouts, and error handling.
"""

import hashlib
import time
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of fetching a single URL."""
    
    url: str
    scheme_id: str
    success: bool
    status_code: Optional[int] = None
    content: Optional[str] = None
    content_hash: Optional[str] = None
    error: Optional[str] = None
    fetch_time_ms: Optional[int] = None
    timestamp: Optional[str] = None


class HTTPFetcher:
    """
    HTTP fetcher with rate limiting, retries, and error handling.
    
    Attributes:
        user_agent: User-Agent string for requests
        timeout: Request timeout in seconds
        rate_limit_delay: Delay between requests in seconds
        max_retries: Number of retries for failed requests
    """
    
    def __init__(
        self,
        user_agent: str = "MutualFundFAQ-Assistant/1.0",
        timeout: int = 30,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        
        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default headers
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        
        logger.info(f"Initialized HTTPFetcher with timeout={timeout}s, rate_limit={rate_limit_delay}s")
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content (first 16 chars)."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def fetch(self, url: str, scheme_id: str) -> FetchResult:
        """
        Fetch a single URL with rate limiting and error handling.
        
        Args:
            url: URL to fetch
            scheme_id: Identifier for the scheme (for logging)
            
        Returns:
            FetchResult with content or error details
        """
        import datetime
        
        start_time = time.time()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        logger.info(f"Fetching {scheme_id}: {url}")
        
        try:
            # Rate limiting
            if hasattr(self, '_last_fetch_time'):
                elapsed = time.time() - self._last_fetch_time
                if elapsed < self.rate_limit_delay:
                    sleep_time = self.rate_limit_delay - elapsed
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            # Make request
            response = self.session.get(url, timeout=self.timeout)
            self._last_fetch_time = time.time()
            
            # Calculate fetch time
            fetch_time_ms = int((time.time() - start_time) * 1000)
            
            # Check status
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.reason}"
                logger.warning(f"Failed to fetch {url}: {error_msg}")
                return FetchResult(
                    url=url,
                    scheme_id=scheme_id,
                    success=False,
                    status_code=response.status_code,
                    error=error_msg,
                    fetch_time_ms=fetch_time_ms,
                    timestamp=timestamp
                )
            
            # Get content
            content = response.text
            
            # Check for empty content
            if not content or len(content.strip()) == 0:
                return FetchResult(
                    url=url,
                    scheme_id=scheme_id,
                    success=False,
                    status_code=response.status_code,
                    error="Empty response body",
                    fetch_time_ms=fetch_time_ms,
                    timestamp=timestamp
                )
            
            # Compute hash
            content_hash = self._compute_hash(content)
            
            logger.info(f"Successfully fetched {url} ({len(content)} bytes, hash: {content_hash})")
            
            return FetchResult(
                url=url,
                scheme_id=scheme_id,
                success=True,
                status_code=response.status_code,
                content=content,
                content_hash=content_hash,
                fetch_time_ms=fetch_time_ms,
                timestamp=timestamp
            )
            
        except requests.exceptions.Timeout:
            fetch_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Timeout fetching {url} after {self.timeout}s")
            return FetchResult(
                url=url,
                scheme_id=scheme_id,
                success=False,
                error=f"Request timeout after {self.timeout}s",
                fetch_time_ms=fetch_time_ms,
                timestamp=timestamp
            )
            
        except requests.exceptions.RequestException as e:
            fetch_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Request error fetching {url}: {e}")
            return FetchResult(
                url=url,
                scheme_id=scheme_id,
                success=False,
                error=str(e),
                fetch_time_ms=fetch_time_ms,
                timestamp=timestamp
            )
            
        except Exception as e:
            fetch_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Unexpected error fetching {url}")
            return FetchResult(
                url=url,
                scheme_id=scheme_id,
                success=False,
                error=f"Unexpected error: {str(e)}",
                fetch_time_ms=fetch_time_ms,
                timestamp=timestamp
            )
    
    def fetch_all(self, urls: list[dict]) -> list[FetchResult]:
        """
        Fetch multiple URLs sequentially with rate limiting.
        
        Args:
            urls: List of dicts with 'url' and 'scheme_id' keys
            
        Returns:
            List of FetchResult objects
        """
        results = []
        
        logger.info(f"Starting batch fetch of {len(urls)} URLs")
        
        for i, url_config in enumerate(urls, 1):
            url = url_config.get('url')
            scheme_id = url_config.get('scheme_id')
            
            if not url or not scheme_id:
                logger.warning(f"Skipping invalid URL config: {url_config}")
                continue
            
            result = self.fetch(url, scheme_id)
            results.append(result)
            
            # Progress logging
            if i % 5 == 0 or i == len(urls):
                logger.info(f"Progress: {i}/{len(urls)} URLs processed")
        
        # Summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Batch fetch complete: {success_count}/{len(results)} successful")
        
        return results
