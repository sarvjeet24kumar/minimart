"""
Application Constants

Single source of truth for magic strings, integers, field lengths,
WebSocket event types, Redis key prefixes, and pagination defaults.
"""

# Field Lengths
MAX_LENGTH_NAME = 255          
MIN_LENGTH_NAME = 1
MAX_LENGTH_EMAIL = 255         
MAX_LENGTH_PASSWORD_HASH = 255   
MAX_LENGTH_PASSWORD_RAW = 128
MIN_LENGTH_PASSWORD = 8       
MIN_LENGTH_PASSWORD_LOGIN = 1
MAX_LENGTH_TOKEN = 1024         
MIN_LENGTH_TOKEN = 1
MAX_LENGTH_USERNAME = 100     
MIN_LENGTH_USERNAME = 3
MAX_LENGTH_SLUG = 100         
MIN_LENGTH_SLUG = 1
MAX_LENGTH_UUID_STR = 36       
MAX_CHAT_MESSAGE_LENGTH = 2000 
MIN_LENGTH_CHAT_MESSAGE = 1

# Item Constants
MIN_ITEM_QUANTITY = 1      
MAX_ITEM_QUANTITY = 1000000
DEFAULT_ITEM_QUANTITY = 1

# Validation Patterns
REGEX_USERNAME = r"^[a-zA-Z0-9_]+$"
REGEX_SLUG = r"^[a-z0-9-]+$"
OTP_LENGTH = 6

# Standard Response Messages
MSG_OTP_SENT = "OTP sent successfully"
MSG_INVITE_SENT = "Invitation sent successfully"

# Normalization
NORMALIZATION_BYPASS_FIELDS = {
    "password",
    "current_password",
    "new_password",
    "confirm_password",
    "token",
    "refresh_token",
    "otp",
    "role",
    "status",
    "type",
}

# WebSocket Event Types
WS_EVENT_ITEM_ADDED = "item_added"
WS_EVENT_ITEM_UPDATED = "item_updated"
WS_EVENT_ITEM_DELETED = "item_deleted"
WS_EVENT_MEMBER_JOINED = "member_joined"
WS_EVENT_MEMBER_REMOVED = "member_removed"
WS_EVENT_MEMBER_LEFT = "member_left"
WS_EVENT_INVITE_CREATED = "invite_created"
WS_EVENT_INVITE_ACCEPTED = "invite_accepted"
WS_EVENT_INVITE_REJECTED = "invite_rejected"
WS_EVENT_INVITE_CANCELLED = "invite_cancelled"
WS_EVENT_LIST_UPDATED = "list_updated"
WS_EVENT_LIST_DELETED = "list_deleted"
WS_EVENT_CHAT_MESSAGE = "chat_message"
WS_EVENT_PERMISSIONS_UPDATED = "permissions_updated"

# WebSocket Handshake Types
WS_TYPE_CONNECTED = "connected"
WS_TYPE_SUBSCRIBE = "subscribe"
WS_TYPE_PING = "ping"
WS_TYPE_PONG = "pong"
WS_TYPE_ERROR = "error"

# WebSocket Close Codes
WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_FORBIDDEN = 4003

# Redis Key Prefixes
REDIS_PREFIX_OTP = "otp"
REDIS_PREFIX_INVITE = "invite"
REDIS_PREFIX_BLACKLIST = "blacklist"
REDIS_PREFIX_BLACKLIST_ACCESS = "blacklist:access"
REDIS_PREFIX_PASSWORD_RESET = "password_reset"

# Redis Channels
REDIS_CHANNEL_LIST = "list"

# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1
DEFAULT_CHAT_LIMIT = 50
MAX_CHAT_LIMIT = 100
MIN_CHAT_LIMIT = 1

# Password Policy (Centralized)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True

# Token Types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_INVITE = "invitation"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"
