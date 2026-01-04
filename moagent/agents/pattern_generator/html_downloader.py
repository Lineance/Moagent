"""
HTML Downloader - Downloads HTML files for LLM pattern analysis.

This utility fetches HTML content from URLs and saves it locally
for use with pattern generator agents (both rule-based and LLM-based).
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class HTMLDownloader:
    """
    Downloads HTML files for pattern analysis.

    Features:
    - Fetch HTML from any URL
    - Handle JavaScript-rendered pages (optional)
    - Save to specified directory
    - Clean filenames from URLs
    - Support for authentication headers
    - Progress reporting

    Example:
        >>> downloader = HTMLDownloader()
        >>> file_path = downloader.download(
        ...     "https://example.com/news",
        ...     output_dir="data/samples",
        ...     use_js=False
        ... )
        >>> print(f"Saved to: {file_path}")
    """

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """
        Initialize downloader.

        Args:
            headers: Custom HTTP headers
        """
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.timeout = 30

    def download(
        self,
        url: str,
        output_dir: str = "data/samples",
        filename: Optional[str] = None,
        use_js: bool = False,
        wait_time: int = 2,
        max_retries: int = 3
    ) -> str:
        """
        Download HTML from URL and save to file.

        Args:
            url: URL to download
            output_dir: Directory to save files
            filename: Custom filename (auto-generated if None)
            use_js: Use Playwright for JavaScript rendering
            wait_time: Seconds to wait for JS rendering
            max_retries: Number of retry attempts

        Returns:
            Path to saved file

        Raises:
            Exception: If download fails after retries
        """
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename
        if not filename:
            filename = self._generate_filename(url)

        output_path = Path(output_dir) / filename

        # Download content
        for attempt in range(max_retries):
            try:
                if use_js:
                    html_content = self._download_with_js(url, wait_time)
                else:
                    html_content = self._download_simple(url)

                # Save to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                logger.info(f"✅ Downloaded: {url} → {output_path}")
                logger.info(f"   Size: {len(html_content)} bytes")

                return str(output_path)

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    wait = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait} seconds...")
                    time.sleep(wait)
                else:
                    raise Exception(f"Failed to download {url} after {max_retries} attempts: {e}")

    def download_batch(
        self,
        urls: list,
        output_dir: str = "data/samples",
        use_js: bool = False,
        skip_existing: bool = True
    ) -> Dict[str, str]:
        """
        Download multiple HTML files.

        Args:
            urls: List of URLs to download
            output_dir: Directory to save files
            use_js: Use JavaScript rendering
            skip_existing: Skip if file already exists

        Returns:
            Dict mapping URLs to file paths
        """
        results = {}

        for url in urls:
            filename = self._generate_filename(url)
            output_path = Path(output_dir) / filename

            if skip_existing and output_path.exists():
                logger.info(f"⏭️  Skipped (exists): {url}")
                results[url] = str(output_path)
                continue

            try:
                file_path = self.download(url, output_dir, filename, use_js)
                results[url] = file_path
            except Exception as e:
                logger.error(f"❌ Failed {url}: {e}")
                results[url] = None

        return results

    def _download_simple(self, url: str) -> str:
        """Download HTML using requests with improved error handling."""
        import requests

        response = requests.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
            allow_redirects=True
        )
        response.raise_for_status()

        # Handle encoding - try multiple methods
        # 1. Use apparent encoding (from response content)
        if response.apparent_encoding:
            response.encoding = response.apparent_encoding

        # 2. If that fails or returns None, try explicit encoding
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            # Try UTF-8 first (most common)
            try:
                response.content.decode('utf-8')
                response.encoding = 'utf-8'
            except UnicodeDecodeError:
                # Fall back to apparent_encoding or latin-1
                response.encoding = response.apparent_encoding or 'latin-1'

        return response.text

    def _download_with_js(self, url: str, wait_time: int) -> str:
        """Download HTML using Playwright (JavaScript rendering)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: playwright install")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.headers.get('User-Agent', '')
            )

            try:
                page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
                page.wait_for_timeout(wait_time * 1000)
                html_content = page.content()
            finally:
                browser.close()

            return html_content

    def _generate_filename(self, url: str) -> str:
        """Generate safe filename from URL."""
        parsed = urlparse(url)

        # Extract meaningful parts
        domain = parsed.netloc.replace(':', '_').replace('.', '_')
        path = parsed.path.strip('/').replace('/', '_')

        if not path:
            path = "index"

        # Truncate if too long
        if len(path) > 50:
            path = path[:50]

        # Clean filename (allow alphanumeric, underscore, hyphen)
        clean_domain = "".join(c for c in domain if c.isalnum() or c in ('_', '-'))
        clean_path = "".join(c for c in path if c.isalnum() or c in ('_', '-'))

        return f"{clean_domain}_{clean_path}.html"

    def preview(self, url: str, max_chars: int = 500, use_js: bool = False) -> str:
        """
        Download and preview HTML content.

        Args:
            url: URL to preview
            max_chars: Number of characters to show
            use_js: Use JavaScript rendering

        Returns:
            Preview of HTML content
        """
        try:
            if use_js:
                content = self._download_with_js(url, 2)
            else:
                content = self._download_simple(url)

            preview = content[:max_chars].replace('\n', ' ').replace('\r', '')
            return f"{preview}..."
        except Exception as e:
            return f"Error: {e}"

    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False


class DownloaderFactory:
    """Factory for creating configured downloaders."""

    @staticmethod
    def create_user_agent() -> HTMLDownloader:
        """Create downloader with user-agent headers."""
        return HTMLDownloader({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    @staticmethod
    def create_bot_agent() -> HTMLDownloader:
        """Create downloader with bot headers."""
        return HTMLDownloader({
            "User-Agent": "MoAgent/1.0 (Pattern Analysis Bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml",
        })

    @staticmethod
    def create_stealth_agent() -> HTMLDownloader:
        """Create downloader with stealth headers."""
        return HTMLDownloader({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })


def download_html(
    url: str,
    output_dir: str = "data/samples",
    use_js: bool = False,
    verbose: bool = True
) -> str:
    """
    Convenience function to download HTML.

    Args:
        url: URL to download
        output_dir: Output directory
        use_js: Use JavaScript rendering
        verbose: Print progress

    Returns:
        Path to saved file
    """
    downloader = DownloaderFactory.create_user_agent()

    if verbose:
        print(f"📥 Downloading: {url}")
        if use_js:
            print("   Using JavaScript rendering...")

    file_path = downloader.download(url, output_dir, use_js=use_js)

    if verbose:
        print(f"✅ Saved to: {file_path}")

    return file_path


def download_batch(
    urls: list,
    output_dir: str = "data/samples",
    use_js: bool = False,
    skip_existing: bool = True
) -> Dict[str, str]:
    """
    Convenience function to download multiple HTML files.

    Args:
        urls: List of URLs
        output_dir: Output directory
        use_js: Use JavaScript rendering
        skip_existing: Skip existing files

    Returns:
        Dict mapping URLs to file paths
    """
    downloader = DownloaderFactory.create_user_agent()

    print(f"📥 Downloading {len(urls)} files...")
    results = downloader.download_batch(urls, output_dir, use_js, skip_existing)

    success = sum(1 for v in results.values() if v is not None)
    print(f"✅ Success: {success}/{len(urls)}")

    return results


__all__ = ["HTMLDownloader", "DownloaderFactory", "download_html", "download_batch"]