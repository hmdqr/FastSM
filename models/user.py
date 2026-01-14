"""Universal user representation and caching for multi-platform support."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any
import pickle
import os


@dataclass
class UniversalUser:
    """Universal user representation that works across platforms."""
    id: str
    acct: str  # username@instance or just username
    username: str  # Local username without instance
    display_name: str
    note: str = ""  # Bio/description (HTML)
    avatar: Optional[str] = None
    header: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    statuses_count: int = 0
    created_at: Optional[datetime] = None

    # Platform-specific
    url: Optional[str] = None
    bot: bool = False
    locked: bool = False

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

    def __eq__(self, other):
        if isinstance(other, UniversalUser):
            return self.id == other.id and self._platform == other._platform
        return False

    def __hash__(self):
        return hash((self.id, self._platform))


class UserCache:
    """Per-account user cache for looking up users by ID or name."""

    MAX_CACHE_SIZE = 500  # Limit cache to prevent slow startup

    def __init__(self, confpath: str, platform: str, account_id: str):
        self.confpath = confpath
        self.platform = platform
        self.account_id = account_id
        self.users: List[UniversalUser] = []
        self.unknown_users: List[str] = []  # IDs to look up later
        self._cache_file = os.path.join(confpath, f"usercache_{platform}_{account_id}")
        self._loaded = False

    def load(self) -> bool:
        """Load cache from disk (runs in background thread)."""
        import threading
        # Start loading in background so it doesn't block startup
        threading.Thread(target=self._load_async, daemon=True).start()
        return True

    def _load_async(self):
        """Actually load the cache file."""
        try:
            with open(self._cache_file, "rb") as f:
                users = pickle.load(f)
            # Trim to max size (keep most recent)
            if len(users) > self.MAX_CACHE_SIZE:
                users = users[:self.MAX_CACHE_SIZE]
            self.users = users
            self._loaded = True
        except:
            self.users = []
            self._loaded = True

    def save(self):
        """Save cache to disk."""
        try:
            # Trim to max size before saving
            users_to_save = self.users[:self.MAX_CACHE_SIZE]
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "wb") as f:
                pickle.dump(users_to_save, f)
        except Exception as e:
            print(f"Error saving user cache: {e}")

    def add_user(self, user: UniversalUser):
        """Add or update a user in the cache."""
        if user is None:
            return
        # Remove existing entry with same ID
        self.users = [u for u in self.users if u.id != user.id]
        # Insert at front (most recently seen)
        self.users.insert(0, user)
        # Trim if too large
        if len(self.users) > self.MAX_CACHE_SIZE:
            self.users = self.users[:self.MAX_CACHE_SIZE]

    def add_users_from_status(self, status):
        """Extract and cache users from a status."""
        if hasattr(status, 'account') and status.account:
            self.add_user(status.account)
        if hasattr(status, 'reblog') and status.reblog:
            if hasattr(status.reblog, 'account') and status.reblog.account:
                self.add_user(status.reblog.account)
        if hasattr(status, 'quote') and status.quote:
            if hasattr(status.quote, 'account') and status.quote.account:
                self.add_user(status.quote.account)

    def add_users_from_notification(self, notification):
        """Extract and cache users from a notification."""
        if hasattr(notification, 'account') and notification.account:
            self.add_user(notification.account)
        if hasattr(notification, 'status') and notification.status:
            self.add_users_from_status(notification.status)

    def lookup_by_id(self, user_id: str) -> Optional[UniversalUser]:
        """Look up a user by ID."""
        for user in self.users:
            if str(user.id) == str(user_id):
                return user
        # Add to unknown list for later lookup
        if user_id not in self.unknown_users:
            self.unknown_users.append(user_id)
        return None

    def lookup_by_name(self, name: str, use_api_callback=None) -> Optional[UniversalUser]:
        """Look up a user by acct/username."""
        name = name.lstrip('@').lower()

        for user in self.users:
            if user.acct.lower() == name or user.acct.split('@')[0].lower() == name:
                return user

        # Try API lookup if callback provided
        if use_api_callback:
            user = use_api_callback(name)
            if user:
                self.add_user(user)
                return user

        return None

    def clear(self):
        """Clear the cache."""
        self.users = []
        self.unknown_users = []
