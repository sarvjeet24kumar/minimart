### Permissions Matrix

#### Platform & Tenant Management

| Action | Super Admin | Tenant Admin | User |
|--------|:---:|:---:|:---:|
| Create tenant | Yes | No | No |
| View all tenants | Yes | No | No |
| View single tenant (with counts) | Yes | No | No |
| Update tenant details (name, slug) | Yes | No | No |
| Activate/Deactivate tenant | Yes | No | No |
| Soft-delete tenant | Yes | No | No |
| Access actual list data (cross-tenant) | No | No | No |

#### User Management

| Action | Super Admin | Tenant Admin | User |
|--------|:---:|:---:|:---:|
| Create Tenant Admin (any tenant) | Yes | No | No |
| Create user in their tenant | No | Yes | No |
| List users | Yes (Tenant Admins only) | Yes (own tenant) | Yes (own tenant, active only) |
| View any user in tenant | Yes (Tenant Admins only) | Yes (own tenant) | Yes (own tenant, active only) |
| View own profile | Yes | Yes | Yes |
| Update any user | Yes (Tenant Admins only) | Yes (own tenant) | No |
| Update own profile | Yes | Yes | Yes |
| Deactivate any user (soft delete) | Yes (not self) | Yes (own tenant, not self) | No |
| Deactivate own account | No (admins blocked) | No (admins blocked) | Yes |

**Key Rules:**
- **Super Admin**: Manages the tenant ecosystem and tenant admins; can only see Tenant Admin accounts, not regular users. Restricted from private shopping list data.
- **Tenant Admin**: Full oversight of users and content within their organization. Cannot deactivate themselves.
- **User**: Collaborative role; can only update/deactivate their own account. Cannot modify own `is_active` or `deleted_at` via update.

#### Shopping List Management

| Action | Super Admin | Tenant Admin | List Owner | List Member |
|--------|:---:|:---:|:---:|:---:|
| Create shopping list | No | Yes | Yes | — |
| View all org lists (incl. deleted via `include_archived`) | No | Yes | No | No |
| View own lists | No | — | Yes | Yes |
| View single list detail | No | Yes | Yes | Yes |
| Update list name | No | Yes | Yes | No |
| Restore deleted list (`deleted_at → null`) | No | Yes | No | No |
| Soft-delete list | No | Yes | Yes | No |
| View deleted lists | No | Yes | No (404) | No (404) |
| View members | No | Yes | Yes | Yes |
| View deleted members (`include_deleted`) | No | Yes | Yes | Yes |
| Remove member from list | No | Yes | Yes | No |
| Update member permissions | No | Yes | Yes | No |

**Key Rules:**
- **Tenant Admin**: Has elevated (override) access to all lists within their organization. Only role that can restore deleted lists and view deleted lists.
- **List Owner**: Full control over list membership, settings, and deletion. Cannot restore deleted lists.
- **Members**: Can only view the list and its members. Cannot modify list settings or manage other members.
- **Owner cannot be removed** or have their permissions modified.

#### Item Management

| Action | Super Admin | Tenant Admin | List Owner | Member (w/ Flag) | Member (Default) |
|--------|:---:|:---:|:---:|:---:|:---:|
| View items | No | Yes | Yes | Yes (`can_view`) | Yes (`can_view`) |
| Add item to list | No | Yes | Yes | Yes (`can_add_item`) | No |
| Update item details | No | Yes | Yes | Yes (`can_update_item`) | No |
| Toggle item status (Purchased) | No | Yes | Yes | Yes (`can_update_item`) | No |
| Delete item (soft) | No | Yes | Yes | Yes (`can_delete_item`) | No |

**Key Permission Flags:**
- **can_view**: Granted to all members by default. Required to view items.
- **can_add_item**: Allows the member to contribute new items to the list.
- **can_update_item**: Allows changing quantities, names, or marking items as purchased.
- **can_delete_item**: Allows soft-deleting items from the list.
- Purchased items **cannot be updated** (hard block regardless of permissions).

#### Invitations & Access

| Action | Super Admin | Tenant Admin | List Owner | User |
|--------|:---:|:---:|:---:|:---:|
| Send invitation | No | Yes | Yes | No |
| Resend invitation email | No | Yes | Yes | No |
| Cancel pending invitation | No | Yes | Yes | No |
| View list invitations | No | Yes | Yes | No |
| View received invites | No | Yes | Yes | Yes |
| Accept invitation | No | No | No | Yes (Invitee) |
| Reject invitation | No | No | No | Yes (Invitee) |

**Key Rules:**
- Cross-tenant invitations are blocked (token encodes `tenant_id`).
- Cannot invite to or accept invites for deleted lists.
- Duplicate membership and duplicate pending invite checks prevent spam.

#### Real-Time Communication (Chat & Notifications)

| Action | Super Admin | Tenant Admin | List Owner | List Member |
|--------|:---:|:---:|:---:|:---:|
| Connect to chat WebSocket | No | Yes | Yes | Yes |
| Send chat message | No | Yes | Yes | Yes |
| View chat history | No | Yes | Yes | Yes |
| Delete own chat message | No | Yes | Yes | Yes |
| Delete any chat message | No | Yes | Yes | No |
| Receive real-time list events | No | Yes | Yes | Yes |
| Receive push notifications | No | Yes | Yes | Yes |

**Key Rules:**
- Cannot send messages to a deleted list.
- Membership is re-verified on every message send.
- Tenant Admin and List Owner can delete any message in the list.
- Notifications are deduplicated: users already watching a list via WebSocket do not receive duplicate notification popups.
