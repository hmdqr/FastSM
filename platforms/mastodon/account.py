"""Mastodon platform account implementation."""

from typing import List, Optional, Any, Dict
from mastodon import Mastodon, MastodonError

from platforms.base import PlatformAccount
from models import UniversalStatus, UniversalUser, UniversalNotification, UserCache
from .models import (
    mastodon_status_to_universal,
    mastodon_user_to_universal,
    mastodon_notification_to_universal,
)


class MastodonAccount(PlatformAccount):
    """Mastodon-specific account implementation."""

    platform_name = "mastodon"

    # Feature flags
    supports_visibility = True
    supports_content_warning = True
    supports_quote_posts = True  # Mastodon 4.0+
    supports_polls = True
    supports_lists = True
    supports_direct_messages = True

    def __init__(self, app, index: int, api: Mastodon, me, confpath: str):
        super().__init__(app, index)
        self.api = api
        self._me = mastodon_user_to_universal(me)
        self._raw_me = me  # Keep original for compatibility
        self.confpath = confpath

        # Initialize user cache
        self.user_cache = UserCache(confpath, 'mastodon', str(self._me.id))
        self.user_cache.load()

        # Get max chars from instance
        try:
            instance_info = api.instance()
            if hasattr(instance_info, 'configuration') and hasattr(instance_info.configuration, 'statuses'):
                self._max_chars = instance_info.configuration.statuses.max_characters
            else:
                self._max_chars = 500
        except:
            self._max_chars = 500

        # Get default visibility
        try:
            self.default_visibility = getattr(me, 'source', {}).get('privacy', 'public')
        except:
            self.default_visibility = 'public'

    @property
    def me(self) -> UniversalUser:
        return self._me

    def _convert_statuses(self, statuses) -> List[UniversalStatus]:
        """Convert a list of Mastodon statuses to universal statuses."""
        return [mastodon_status_to_universal(s) for s in statuses if s]

    def _convert_users(self, users) -> List[UniversalUser]:
        """Convert a list of Mastodon users to universal users."""
        return [mastodon_user_to_universal(u) for u in users if u]

    # ============ Timeline Methods ============

    def get_home_timeline(self, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get home timeline statuses."""
        statuses = self.api.timeline_home(limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        # Cache users
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_mentions(self, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get mentions as statuses (extracted from notifications).

        This is the key method that fixes the mentions buffer - it returns
        actual status objects instead of notification objects.
        """
        notifications = self.api.notifications(mentions_only=True, limit=limit, **kwargs)
        statuses = []

        for notif in notifications:
            if hasattr(notif, 'status') and notif.status:
                status = mastodon_status_to_universal(notif.status)
                if status:
                    # Store notification ID for deduplication
                    status._notification_id = str(notif.id)
                    # Use notification ID as the status ID for this timeline
                    # This ensures proper pagination with since_id/max_id
                    status.id = str(notif.id)
                    statuses.append(status)
                    self.user_cache.add_users_from_status(status)

        return statuses

    def get_notifications(self, limit: int = 40, **kwargs) -> List[UniversalNotification]:
        """Get notifications."""
        notifications = self.api.notifications(limit=limit, **kwargs)
        result = [mastodon_notification_to_universal(n) for n in notifications if n]
        # Cache users
        for notif in result:
            self.user_cache.add_users_from_notification(notif)
        return result

    def get_conversations(self, limit: int = 40, **kwargs) -> List[Any]:
        """Get direct message conversations."""
        # Return raw conversations - these have special structure
        return self.api.conversations(limit=limit, **kwargs)

    def get_favourites(self, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get favourited statuses."""
        statuses = self.api.favourites(limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_user_statuses(self, user_id: str, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get statuses from a specific user."""
        statuses = self.api.account_statuses(id=user_id, limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_list_timeline(self, list_id: str, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get statuses from a list."""
        statuses = self.api.timeline_list(id=list_id, limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_local_timeline(self, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get local timeline (posts from users on this instance)."""
        statuses = self.api.timeline_local(limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_public_timeline(self, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Get federated/public timeline (posts from all known instances)."""
        statuses = self.api.timeline_public(limit=limit, **kwargs)
        result = self._convert_statuses(statuses)
        for status in result:
            self.user_cache.add_users_from_status(status)
        return result

    def get_available_timelines(self) -> List[dict]:
        """Get available custom timelines for this platform."""
        return [
            {'type': 'local', 'id': 'local', 'name': 'Local Timeline', 'description': 'Posts from users on this instance'},
            {'type': 'federated', 'id': 'federated', 'name': 'Federated Timeline', 'description': 'Posts from all known instances'},
        ]

    def search_statuses(self, query: str, limit: int = 40, **kwargs) -> List[UniversalStatus]:
        """Search for statuses."""
        result = self.api.search_v2(q=query, result_type='statuses', limit=limit, **kwargs)
        statuses = result.statuses if hasattr(result, 'statuses') else result.get('statuses', [])
        converted = self._convert_statuses(statuses)
        for status in converted:
            self.user_cache.add_users_from_status(status)
        return converted

    def get_status(self, status_id: str) -> Optional[UniversalStatus]:
        """Get a single status by ID."""
        try:
            status = self.api.status(id=status_id)
            return mastodon_status_to_universal(status)
        except MastodonError:
            return None

    def get_status_context(self, status_id: str) -> Dict[str, List[UniversalStatus]]:
        """Get replies and ancestors of a status."""
        try:
            context = self.api.status_context(id=status_id)
            return {
                'ancestors': self._convert_statuses(context.ancestors if hasattr(context, 'ancestors') else context.get('ancestors', [])),
                'descendants': self._convert_statuses(context.descendants if hasattr(context, 'descendants') else context.get('descendants', [])),
            }
        except MastodonError:
            return {'ancestors': [], 'descendants': []}

    # ============ Action Methods ============

    def post(self, text: str, reply_to_id: Optional[str] = None,
             visibility: Optional[str] = None, spoiler_text: Optional[str] = None,
             **kwargs) -> UniversalStatus:
        """Create a new post/status."""
        if visibility is None:
            visibility = self.default_visibility

        post_kwargs = {
            'status': text,
            'visibility': visibility,
        }

        if spoiler_text:
            post_kwargs['spoiler_text'] = spoiler_text

        if reply_to_id:
            post_kwargs['in_reply_to_id'] = reply_to_id

        post_kwargs.update(kwargs)

        status = self.api.status_post(**post_kwargs)
        return mastodon_status_to_universal(status)

    def quote(self, status, text: str, visibility: Optional[str] = None) -> UniversalStatus:
        """Quote a status."""
        if visibility is None:
            visibility = self.default_visibility

        try:
            # Try native quote (Mastodon 4.0+)
            status_id = status.id if hasattr(status, 'id') else status
            result = self.api.status_post(status=text, quote_id=status_id, visibility=visibility)
        except:
            # Fallback: include link to original post
            original_url = getattr(status, 'url', None)
            if not original_url and hasattr(status, 'account'):
                original_url = f"{self.api.api_base_url}/@{status.account.acct}/{status.id}"
            result = self.api.status_post(status=f"{text}\n\n{original_url}", visibility=visibility)

        return mastodon_status_to_universal(result)

    def boost(self, status_id: str) -> bool:
        """Boost/reblog a status."""
        try:
            self.api.status_reblog(id=status_id)
            return True
        except MastodonError:
            return False

    def unboost(self, status_id: str) -> bool:
        """Remove boost from a status."""
        try:
            self.api.status_unreblog(id=status_id)
            return True
        except MastodonError:
            return False

    def favourite(self, status_id: str) -> bool:
        """Favourite a status."""
        try:
            self.api.status_favourite(id=status_id)
            return True
        except MastodonError:
            return False

    def unfavourite(self, status_id: str) -> bool:
        """Remove favourite from a status."""
        try:
            self.api.status_unfavourite(id=status_id)
            return True
        except MastodonError:
            return False

    def delete_status(self, status_id: str) -> bool:
        """Delete a status."""
        try:
            self.api.status_delete(id=status_id)
            return True
        except MastodonError:
            return False

    # ============ User Methods ============

    def get_user(self, user_id: str) -> Optional[UniversalUser]:
        """Get user by ID."""
        try:
            user = self.api.account(id=user_id)
            universal = mastodon_user_to_universal(user)
            self.user_cache.add_user(universal)
            return universal
        except MastodonError:
            return None

    def search_users(self, query: str, limit: int = 10) -> List[UniversalUser]:
        """Search for users."""
        try:
            results = self.api.account_search(q=query, limit=limit)
            users = self._convert_users(results)
            for user in users:
                self.user_cache.add_user(user)
            return users
        except MastodonError:
            return []

    def lookup_user_by_name(self, name: str) -> Optional[UniversalUser]:
        """Look up user by acct/username - for user cache callback."""
        results = self.search_users(name, limit=1)
        return results[0] if results else None

    def follow(self, user_id: str) -> bool:
        """Follow a user."""
        try:
            self.api.account_follow(id=user_id)
            return True
        except MastodonError:
            return False

    def unfollow(self, user_id: str) -> bool:
        """Unfollow a user."""
        try:
            self.api.account_unfollow(id=user_id)
            return True
        except MastodonError:
            return False

    def block(self, user_id: str) -> bool:
        """Block a user."""
        try:
            self.api.account_block(id=user_id)
            return True
        except MastodonError:
            return False

    def unblock(self, user_id: str) -> bool:
        """Unblock a user."""
        try:
            self.api.account_unblock(id=user_id)
            return True
        except MastodonError:
            return False

    def mute(self, user_id: str) -> bool:
        """Mute a user."""
        try:
            self.api.account_mute(id=user_id)
            return True
        except MastodonError:
            return False

    def unmute(self, user_id: str) -> bool:
        """Unmute a user."""
        try:
            self.api.account_unmute(id=user_id)
            return True
        except MastodonError:
            return False

    def get_followers(self, user_id: str, limit: int = 80) -> List[UniversalUser]:
        """Get followers of a user."""
        try:
            followers = self.api.account_followers(id=user_id, limit=limit)
            users = self._convert_users(followers)
            for user in users:
                self.user_cache.add_user(user)
            return users
        except MastodonError:
            return []

    def get_following(self, user_id: str, limit: int = 80) -> List[UniversalUser]:
        """Get users that a user is following."""
        try:
            following = self.api.account_following(id=user_id, limit=limit)
            users = self._convert_users(following)
            for user in users:
                self.user_cache.add_user(user)
            return users
        except MastodonError:
            return []

    # ============ List Methods ============

    def get_lists(self) -> List[Any]:
        """Get user's lists."""
        try:
            return self.api.lists()
        except MastodonError:
            return []

    def get_list_members(self, list_id: str) -> List[UniversalUser]:
        """Get members of a list."""
        try:
            members = self.api.list_accounts(id=list_id)
            return self._convert_users(members)
        except MastodonError:
            return []

    def add_to_list(self, list_id: str, user_id: str) -> bool:
        """Add user to a list."""
        try:
            self.api.list_accounts_add(id=list_id, account_ids=[user_id])
            return True
        except MastodonError:
            return False

    def remove_from_list(self, list_id: str, user_id: str) -> bool:
        """Remove user from a list."""
        try:
            self.api.list_accounts_delete(id=list_id, account_ids=[user_id])
            return True
        except MastodonError:
            return False
