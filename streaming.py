# -*- coding: utf-8 -*-
from mastodon import StreamListener
from GUI import main
import time
import speak
import sys

class MastodonStreamListener(StreamListener):
	"""Handles Mastodon streaming events"""

	def __init__(self, account):
		super(MastodonStreamListener, self).__init__()
		self.account = account

	def on_update(self, status):
		"""Called when a new status appears in the home timeline"""
		try:
			# Add to home timeline
			if len(self.account.timelines) > 0:
				self.account.timelines[0].load(items=[status])

			# Check if it mentions us
			if hasattr(status, 'mentions'):
				for mention in status.mentions:
					if mention.id == self.account.me.id:
						# Find mentions timeline and add
						for tl in self.account.timelines:
							if tl.type == "mentions":
								tl.load(items=[status])
								break
						break

			# Check if it's from us (add to Sent)
			if status.account.id == self.account.me.id:
				for tl in self.account.timelines:
					if tl.type == "user" and tl.name == "Sent":
						tl.load(items=[status])
						break

			# Check user timelines
			for tl in self.account.timelines:
				if tl.type == "list" and status.account.id in tl.members:
					tl.load(items=[status])
				if tl.type == "user" and tl.user and status.account.id == tl.user.id:
					tl.load(items=[status])
		except Exception as e:
			print(f"Stream update error: {e}")

	def on_notification(self, notification):
		"""Called when a new notification arrives"""
		try:
			# Add to notifications timeline
			for tl in self.account.timelines:
				if tl.type == "notifications":
					tl.load(items=[notification])
					break

			# Also add mentions to mentions timeline as STATUS (not notification)
			if notification.type == "mention" and hasattr(notification, 'status') and notification.status:
				# Extract the status and give it the notification ID for dedup
				status = notification.status
				# Store original ID and set notification ID as primary for timeline tracking
				original_status_id = status.id
				status.id = notification.id
				status._notification_id = notification.id
				status._original_status_id = original_status_id

				for tl in self.account.timelines:
					if tl.type == "mentions":
						tl.load(items=[status])
						break
		except Exception as e:
			print(f"Stream notification error: {e}")

	def on_conversation(self, conversation):
		"""Called when a direct message conversation is updated"""
		try:
			for tl in self.account.timelines:
				if tl.type == "conversations":
					tl.load(items=[conversation])
					break
		except Exception as e:
			print(f"Stream conversation error: {e}")

	def on_delete(self, status_id):
		"""Called when a status is deleted"""
		try:
			for tl in self.account.timelines:
				for i, status in enumerate(tl.statuses):
					if hasattr(status, 'id') and status.id == status_id:
						tl.statuses.pop(i)
						if tl == self.account.currentTimeline and self.account == self.account.app.currentAccount:
							main.window.refreshList()
						break
		except Exception as e:
			print(f"Stream delete error: {e}")

	def on_status_update(self, status):
		"""Called when a status is edited"""
		try:
			for tl in self.account.timelines:
				for i, s in enumerate(tl.statuses):
					if hasattr(s, 'id') and s.id == status.id:
						tl.statuses[i] = status
						if tl == self.account.currentTimeline and self.account == self.account.app.currentAccount:
							main.window.refreshList()
						break
		except Exception as e:
			print(f"Stream status update error: {e}")

	def handle_heartbeat(self):
		"""Called on heartbeat to keep connection alive"""
		pass

	def on_abort(self, err):
		"""Called when stream is aborted"""
		speak.speak(f"Stream disconnected for {self.account.me.acct}")

	def on_unknown_event(self, name, data=None):
		"""Called on unknown events"""
		pass
