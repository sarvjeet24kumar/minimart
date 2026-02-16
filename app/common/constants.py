"""
Application Constants

Single source of truth for magic strings, integers, field lengths,
WebSocket event types, Redis key prefixes, and pagination defaults.
"""

MAX_LENGTH_NAME = 255          
MAX_LENGTH_EMAIL = 255         
MAX_LENGTH_PASSWORD = 255   
MAX_LENGTH_TOKEN = 1024         
MAX_LENGTH_USERNAME = 100     
MAX_LENGTH_SLUG = 100         
MAX_LENGTH_UUID_STR = 36       
MIN_LENGTH_PASSWORD = 8       
MIN_ITEM_QUANTITY = 1      
MAX_CHAT_MESSAGE_LENGTH = 2000 


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


WS_TYPE_CONNECTED = "connected"
WS_TYPE_SUBSCRIBE = "subscribe"
WS_TYPE_PING = "ping"
WS_TYPE_PONG = "pong"
WS_TYPE_ERROR = "error"


WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_FORBIDDEN = 4003



REDIS_PREFIX_OTP = "otp"
REDIS_PREFIX_INVITE = "invite"
REDIS_PREFIX_BLACKLIST = "blacklist"
REDIS_PREFIX_BLACKLIST_ACCESS = "blacklist:access"
REDIS_PREFIX_PASSWORD_RESET = "password_reset"



REDIS_CHANNEL_LIST = "list"



DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1
DEFAULT_CHAT_LIMIT = 50
MAX_CHAT_LIMIT = 100
MIN_CHAT_LIMIT = 1


PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True


TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_INVITE = "invitation"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"
