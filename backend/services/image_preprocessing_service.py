"""
Image Preprocessing Service

Responsible for:
- Validating image URLs and local paths
- Converting images to formats suitable for VLM consumption (base64, data URIs)
- Limiting the number of images sent to the VLM (to prevent OOM)
- Returning a clean list of image payloads ready for VLM input

This service is VLM-agnostic and designed to be lightweight with minimal dependencies.
"""

import base64
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class ImagePayload:
    """Standardized image payload for VLM consumption."""

    url: str  # Original URL or path
    data_uri: Optional[str] = None  # Base64 data URI
    format: str = "url"  # "url" or "data_uri"
    mime_type: str = "image/jpeg"
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if image payload is valid."""
        return self.error is None and (self.url or self.data_uri)


class ImagePreprocessingService:
    """
    Service for preprocessing wardrobe item images before sending to VLM.

    Features:
    - URL validation and fetching
    - Base64 encoding for local/remote images
    - Image count limiting
    - Graceful error handling
    - Lightweight with minimal dependencies (httpx only)
    """

    # Configuration
    MAX_IMAGES_PER_REQUEST = 6
    MAX_IMAGE_SIZE_MB = 5
    SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "gif", "webp"}
    TIMEOUT_SECONDS = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the image preprocessing service.

        Args:
            config: Optional configuration dict with:
                - max_images: Maximum images to process
                - max_size_mb: Maximum image size
                - timeout: Request timeout in seconds
                - base_url: Base URL for local paths
        """
        self.config = config or {}
        self.max_images = self.config.get("max_images", self.MAX_IMAGES_PER_REQUEST)
        self.max_size_mb = self.config.get("max_size_mb", self.MAX_IMAGE_SIZE_MB)
        self.timeout = self.config.get("timeout", self.TIMEOUT_SECONDS)
        self.base_url = self.config.get("base_url", "http://127.0.0.1:8000")

    async def preprocess_images(
        self,
        image_urls: List[str],
        return_format: str = "url",
    ) -> List[str]:
        """
        Preprocess a list of images for VLM consumption.

        Args:
            image_urls: List of image URLs or local paths
            return_format: Format to return images in ("url" or "data_uri")

        Returns:
            List of processed image URLs or data URIs
        """
        if not image_urls:
            return []

        limit = min(self.max_images, len(image_urls))
        processed = []

        print(f"[ImagePreprocessing] Processing {limit} images")

        for idx, url in enumerate(image_urls[:limit]):
            try:
                result = await self._process_single_image(url, return_format)
                if result:
                    processed.append(result)
                    print(f"[ImagePreprocessing] Image {idx + 1}/{limit} OK")
            except Exception as e:
                print(f"[ImagePreprocessing] Image {idx + 1} failed: {str(e)}")

        return processed

    async def _process_single_image(
        self, url: str, return_format: str
    ) -> Optional[str]:
        """
        Process a single image.

        Args:
            url: Image URL or local path
            return_format: Format to return ("url" or "data_uri")

        Returns:
            Processed image URL/data URI or None if failed
        """
        try:
            url = url.strip()
            if not url:
                return None

            # Already a data URI?
            if url.startswith("data:"):
                return url

            # URL format requested and already a valid HTTP URL?
            if return_format == "url":
                if url.startswith("http://") or url.startswith("https://"):
                    return url

                # Supabase/CDN URL?
                if "supabase" in url or "cdn" in url:
                    return url

            # Need to convert to base64 data URI
            return await self._url_to_base64_data_uri(url)

        except Exception as e:
            print(f"[ImagePreprocessing] Error processing {url}: {str(e)}")
            return None

    async def _url_to_base64_data_uri(self, url: str) -> Optional[str]:
        """
        Convert URL to Base64 data URI.

        Args:
            url: Image URL or local path

        Returns:
            Data URI string or None if conversion failed
        """
        try:
            # Handle local file paths
            if not url.startswith("http://") and not url.startswith("https://"):
                return self._local_file_to_data_uri(url)

            # Fetch remote image
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                if response.status_code != 200:
                    print(f"[ImagePreprocessing] HTTP {response.status_code} for {url}")
                    return None

                # Check size
                content_length = len(response.content)
                if content_length > self.max_size_mb * 1024 * 1024:
                    print(
                        f"[ImagePreprocessing] Image too large: {content_length / 1024 / 1024:.1f}MB"
                    )
                    return None

                # Get content type
                content_type = response.headers.get("Content-Type", "image/jpeg")
                if not content_type.startswith("image/"):
                    print(f"[ImagePreprocessing] Invalid content type: {content_type}")
                    return None

                # Encode to base64
                b64_img = base64.b64encode(response.content).decode("ascii")
                return f"data:{content_type};base64,{b64_img}"

        except httpx.TimeoutException:
            print(f"[ImagePreprocessing] Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"[ImagePreprocessing] Error converting to base64: {str(e)}")
            return None

    def _local_file_to_data_uri(self, path: str) -> Optional[str]:
        """
        Convert local file to data URI.

        Args:
            path: Local file path

        Returns:
            Data URI or None if failed
        """
        try:
            # Clean path
            clean_path = path.lstrip("/")

            # Try different possible locations
            possible_paths = [
                clean_path,
                os.path.join(os.getcwd(), clean_path),
                os.path.join(os.getcwd(), "backend", clean_path),
                os.path.join(os.getcwd(), "uploads", clean_path),
            ]

            file_path = None
            for p in possible_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    file_path = p
                    break

            if not file_path:
                print(f"[ImagePreprocessing] Local file not found: {path}")
                return None

            # Check size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_size_mb * 1024 * 1024:
                print(
                    f"[ImagePreprocessing] Local file too large: {file_size / 1024 / 1024:.1f}MB"
                )
                return None

            # Read and encode
            with open(file_path, "rb") as f:
                image_data = f.read()

            # Infer MIME type from extension
            _, ext = os.path.splitext(file_path)
            mime_type = self._get_mime_type(ext)

            b64_img = base64.b64encode(image_data).decode("ascii")
            return f"data:{mime_type};base64,{b64_img}"

        except Exception as e:
            print(f"[ImagePreprocessing] Error processing local file: {str(e)}")
            return None

    def _get_mime_type(self, extension: str) -> str:
        """Get MIME type from file extension."""
        ext_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return ext_map.get(extension.lower(), "image/jpeg")

    def get_stats(self) -> Dict[str, Any]:
        """Get service configuration stats."""
        return {
            "max_images_per_request": self.max_images,
            "max_file_size_mb": self.max_size_mb,
            "supported_formats": list(self.SUPPORTED_FORMATS),
            "http_timeout_seconds": self.timeout,
        }
