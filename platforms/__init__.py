"""Platform registry for multi-platform social media support."""

from typing import Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PlatformAccount

_platforms: Dict[str, Type['PlatformAccount']] = {}


def register_platform(name: str, platform_class: Type['PlatformAccount']):
    """Register a platform implementation."""
    _platforms[name] = platform_class


def get_platform(name: str) -> Type['PlatformAccount']:
    """Get a platform implementation by name."""
    if name not in _platforms:
        raise ValueError(f"Unknown platform: {name}. Available: {list(_platforms.keys())}")
    return _platforms[name]


def list_platforms() -> list:
    """List all registered platform names."""
    return list(_platforms.keys())
