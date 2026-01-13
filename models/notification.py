"""Universal notification representation for multi-platform support."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass
class UniversalNotification:
    """Universal notification representation that works across platforms."""
    id: str
    type: str  # 'follow', 'favourite', 'reblog', 'mention', 'poll', etc.
    account: 'UniversalUser'  # Who triggered the notification
    created_at: datetime
    status: Optional['UniversalStatus'] = None  # The related status, if any

    # Original platform object
    _platform_data: Any = None
    _platform: str = ""

    def __getattr__(self, name):
        """Fallback to platform data for attributes we don't have."""
        if name.startswith('_'):
            raise AttributeError(name)
        if self._platform_data is not None and hasattr(self._platform_data, name):
            return getattr(self._platform_data, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
