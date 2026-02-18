"""
Centralized Enums
"""

import enum


class UserRole(enum.StrEnum):
    """User roles for platform-level access control."""

    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    USER = "USER"


class MemberRole(enum.StrEnum):
    """Roles for shopping list membership."""

    OWNER = "OWNER"
    MEMBER = "MEMBER"


class ItemStatus(enum.StrEnum):
    """Status of a shopping list item."""

    PENDING = "PENDING"
    PURCHASED = "PURCHASED"


class InviteStatus(enum.StrEnum):
    """Status of an invitation."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class InviteAction(enum.StrEnum):
    """Actions for responding to an invitation."""

    ACCEPT = "accept"
    REJECT = "reject"


class NotificationType(enum.StrEnum):
    """Types of notifications."""

    LIST_INVITE = "LIST_INVITE"
    INVITE_ACCEPTED = "INVITE_ACCEPTED"
    INVITE_REJECTED = "INVITE_REJECTED"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_UPDATED = "ITEM_UPDATED"
    ITEM_DELETED = "ITEM_DELETED"
    ITEM_PURCHASED = "ITEM_PURCHASED"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    LIST_UPDATED = "LIST_UPDATED"
