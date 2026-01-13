"""Mastodon platform implementation."""

from .account import MastodonAccount
from .models import (
    mastodon_status_to_universal,
    mastodon_user_to_universal,
    mastodon_notification_to_universal,
)

__all__ = [
    'MastodonAccount',
    'mastodon_status_to_universal',
    'mastodon_user_to_universal',
    'mastodon_notification_to_universal',
]

# Register this platform
from platforms import register_platform
register_platform('mastodon', MastodonAccount)
