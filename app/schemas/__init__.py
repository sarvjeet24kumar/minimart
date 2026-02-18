"""Schemas Package"""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    OTPResponse,
    RefreshTokenRequest,
    VerifyEmailRequest,
)
from app.schemas.invitation import (
    InvitationRespondRequest,
    InvitationResponse,
    InviteRequest,
    InviteResponse,
)
from app.schemas.item import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
)
from app.schemas.notification import (
    NotificationFilter,
    NotificationResponse,
    NotificationUpdate,
)
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListDetailResponse,
    ShoppingListResponse,
    ShoppingListUpdate,
)
from app.schemas.shopping_list_member import (
    MemberResponse,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from app.schemas.user import (
    UserAdminResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "VerifyEmailRequest",
    "OTPResponse",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserAdminResponse",
    # Shopping List
    "ShoppingListCreate",
    "ShoppingListUpdate",
    "ShoppingListResponse",
    "ShoppingListDetailResponse",
    # Member
    "MemberResponse",
    "InviteRequest",
    "InviteResponse",
    # Item
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    # Invitation
    "InvitationRespondRequest",
    "InvitationResponse",
    # Notification
    "NotificationFilter",
    "NotificationResponse",
    "NotificationUpdate",
]
