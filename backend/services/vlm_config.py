"""
VLM Configuration Module - Phase 4

Handles configuration for different VLM providers (LLaVA, Mock, etc.).
Loads settings from environment variables with sensible defaults.
Validates configuration and provides methods to switch providers dynamically.

Configuration Priority:
1. Environment variables (highest priority)
2. Config dict passed to functions (medium priority)
3. Class defaults (lowest priority)

Environment Variables:
- VLM_PROVIDER: Which VLM to use (llava, mock, etc.)
- LLAVA_API_ENDPOINT: LLaVA API endpoint URL
- LLAVA_MODEL_NAME: LLaVA model name/ID
- LLAVA_API_KEY: Optional API key for external services
- LLAVA_TIMEOUT: Request timeout in seconds
- ENABLE_VLM: Whether to use real VLM (true/false)
- IMAGE_PREPROCESSING_MAX_IMAGES: Max images per request
- IMAGE_PREPROCESSING_MAX_SIZE_MB: Max image file size
"""

import os
from enum import Enum
from typing import Any, Dict, Optional


class VLMProviderType(str, Enum):
    """Supported VLM providers."""

    LLAVA = "llava"
    MOCK = "mock"
    GPT4V = "gpt4v"  # Future
    CLAUDE_VISION = "claude_vision"  # Future


class VLMConfig:
    """
    Configuration for VLM services.

    This class loads and validates VLM configuration from environment variables
    and provides methods to access configuration for different providers.
    """

    # Default values
    DEFAULT_PROVIDER = VLMProviderType.MOCK
    DEFAULT_TIMEOUT = 300.0  # 5 minutes for CPU/GPU processing
    DEFAULT_MAX_TOKENS = 1024
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MODEL_NAME = "llava:latest"

    # LLaVA defaults
    DEFAULT_LLAVA_ENDPOINT = "http://localhost:11434/v1/chat/completions"

    # Image preprocessing defaults
    DEFAULT_MAX_IMAGES = 6
    DEFAULT_MAX_IMAGE_SIZE_MB = 5

    def __init__(self, env_override: Optional[Dict[str, str]] = None):
        """
        Initialize VLM configuration.

        Args:
            env_override: Optional dict to override environment variables (for testing)
        """
        self.env = env_override or os.environ
        self._load_configuration()

    def _load_configuration(self):
        """Load and validate configuration from environment."""
        # General VLM configuration
        self.enable_vlm = self._get_bool_env("ENABLE_VLM", True)
        self.provider = self._get_enum_env(
            "VLM_PROVIDER", VLMProviderType, self.DEFAULT_PROVIDER
        )

        # LLaVA specific
        self.llava_endpoint = self._get_env(
            "LLAVA_API_ENDPOINT", self.DEFAULT_LLAVA_ENDPOINT
        )
        self.llava_model_name = self._get_env(
            "LLAVA_MODEL_NAME", self.DEFAULT_MODEL_NAME
        )
        self.llava_api_key = self._get_env("LLAVA_API_KEY", "")
        self.llava_timeout = self._get_float_env("LLAVA_TIMEOUT", self.DEFAULT_TIMEOUT)
        self.llava_max_tokens = self._get_int_env(
            "LLAVA_MAX_TOKENS", self.DEFAULT_MAX_TOKENS
        )
        self.llava_temperature = self._get_float_env(
            "LLAVA_TEMPERATURE", self.DEFAULT_TEMPERATURE
        )

        # Image preprocessing
        self.max_images_per_request = self._get_int_env(
            "IMAGE_PREPROCESSING_MAX_IMAGES", self.DEFAULT_MAX_IMAGES
        )
        self.max_image_size_mb = self._get_int_env(
            "IMAGE_PREPROCESSING_MAX_SIZE_MB", self.DEFAULT_MAX_IMAGE_SIZE_MB
        )

    def _get_env(self, key: str, default: str = "") -> str:
        """Get environment variable as string."""
        return self.env.get(key, default)

    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean."""
        value = self.env.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _get_int_env(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        try:
            return int(self.env.get(key, default))
        except (ValueError, TypeError):
            return default

    def _get_float_env(self, key: str, default: float = 0.0) -> float:
        """Get environment variable as float."""
        try:
            return float(self.env.get(key, default))
        except (ValueError, TypeError):
            return default

    def _get_enum_env(self, key: str, enum_class: type, default: Any) -> Any:
        """Get environment variable as enum."""
        value = self.env.get(key, str(default.value))
        try:
            return enum_class(value.lower())
        except (ValueError, KeyError):
            return default

    def get_llava_config(self) -> Dict[str, Any]:
        """Get LLaVA service configuration."""
        return {
            "api_endpoint": self.llava_endpoint,
            "model_name": self.llava_model_name,
            "api_key": self.llava_api_key,
            "timeout": self.llava_timeout,
            "max_tokens": self.llava_max_tokens,
            "temperature": self.llava_temperature,
        }

    def get_image_preprocessing_config(self) -> Dict[str, Any]:
        """Get image preprocessing service configuration."""
        return {
            "max_images": self.max_images_per_request,
            "max_size_mb": self.max_image_size_mb,
            "timeout": 15.0,
            "base_url": "http://127.0.0.1:8000",
        }

    def get_provider_config(
        self, provider: Optional[VLMProviderType] = None
    ) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.

        Args:
            provider: VLM provider to get config for (defaults to configured provider)

        Returns:
            Configuration dict for the provider
        """
        provider = provider or self.provider

        if provider == VLMProviderType.LLAVA:
            return self.get_llava_config()
        elif provider == VLMProviderType.MOCK:
            return {}  # Mock service needs no configuration
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def is_configured(self, provider: Optional[VLMProviderType] = None) -> bool:
        """
        Check if a provider is properly configured.

        Args:
            provider: Provider to check (defaults to configured provider)

        Returns:
            True if provider is configured and ready to use
        """
        provider = provider or self.provider

        if provider == VLMProviderType.MOCK:
            return True  # Mock is always available

        if provider == VLMProviderType.LLAVA:
            # LLaVA needs an endpoint at minimum
            # For local Ollama, endpoint defaults to localhost:11434
            # For external API, endpoint must be configured
            return bool(self.llava_endpoint)

        return False

    def validate_configuration(self) -> tuple[bool, str]:
        """
        Validate current configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enable_vlm:
            return True, "VLM disabled - will use rule-based recommendations"

        if self.provider == VLMProviderType.LLAVA:
            if not self.llava_endpoint:
                return False, "LLAVA_API_ENDPOINT not configured"
            if not self.llava_model_name:
                return False, "LLAVA_MODEL_NAME not configured"
            if self.llava_timeout <= 0:
                return False, "LLAVA_TIMEOUT must be positive"

        if self.max_images_per_request <= 0:
            return False, "IMAGE_PREPROCESSING_MAX_IMAGES must be positive"

        if self.max_image_size_mb <= 0:
            return False, "IMAGE_PREPROCESSING_MAX_SIZE_MB must be positive"

        return True, "Configuration valid"

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration (safe to log).

        Returns:
            Configuration summary dict (with sensitive values redacted)
        """
        return {
            "vlm_enabled": self.enable_vlm,
            "provider": self.provider.value,
            "llava": {
                "endpoint": self.llava_endpoint,
                "model": self.llava_model_name,
                "has_api_key": bool(self.llava_api_key),
                "timeout_seconds": self.llava_timeout,
                "max_tokens": self.llava_max_tokens,
                "temperature": self.llava_temperature,
            },
            "image_preprocessing": {
                "max_images": self.max_images_per_request,
                "max_size_mb": self.max_image_size_mb,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dict (with sensitive values redacted)."""
        return self.get_summary()


# Singleton instance for module-level access
_config_instance: Optional[VLMConfig] = None


def get_vlm_config(env_override: Optional[Dict[str, str]] = None) -> VLMConfig:
    """
    Get or create the global VLM configuration instance.

    Args:
        env_override: Optional env dict override (for testing)

    Returns:
        VLMConfig instance
    """
    global _config_instance

    if env_override or _config_instance is None:
        _config_instance = VLMConfig(env_override)

    return _config_instance


def reset_config():
    """Reset the global config instance (useful for testing)."""
    global _config_instance
    _config_instance = None


# Configuration validation and logging helper
def log_configuration():
    """Log the current VLM configuration (safe for production)."""
    config = get_vlm_config()
    is_valid, message = config.validate_configuration()

    print("\n" + "=" * 70)
    print("VLM CONFIGURATION")
    print("=" * 70)

    summary = config.get_summary()
    print(f"VLM Enabled: {summary['vlm_enabled']}")
    print(f"Provider: {summary['provider']}")
    print(f"Provider Valid: {is_valid} - {message}")

    if summary["vlm_enabled"]:
        print(f"\nLLaVA Configuration:")
        print(f"  Endpoint: {summary['llava']['endpoint']}")
        print(f"  Model: {summary['llava']['model']}")
        print(f"  Timeout: {summary['llava']['timeout_seconds']}s")
        print(f"  Max Tokens: {summary['llava']['max_tokens']}")

        print(f"\nImage Preprocessing:")
        print(f"  Max Images: {summary['image_preprocessing']['max_images']}")
        print(f"  Max Size: {summary['image_preprocessing']['max_size_mb']}MB")

    print("=" * 70 + "\n")
