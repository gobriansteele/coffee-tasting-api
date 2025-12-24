# Supabase RBAC Setup

These SQL migrations set up Role-Based Access Control (RBAC) using Supabase Auth Hooks.

## Prerequisites

- A Supabase project with authentication enabled
- Access to the Supabase Dashboard

## Setup Steps

### 1. Run the SQL migrations

Execute these in order via **Dashboard > SQL Editor**:

1. `001_create_user_roles.sql` - Creates the roles table and RLS policies
2. `002_create_auth_hook.sql` - Creates the auth hook function
3. `003_seed_admin_user.sql` - (Optional) Seeds your first admin user

### 2. Enable the Auth Hook

After running the SQL migrations:

1. Go to **Dashboard > Authentication > Hooks**
2. Find **Customize Access Token (JWT) Claims**
3. Toggle it **ON**
4. Select schema: `public`
5. Select function: `custom_access_token_hook`
6. Click **Save**

### 3. Add Admin Users

Option A - By User ID:
```sql
INSERT INTO public.user_roles (user_id, role)
VALUES ('your-user-uuid-here', 'admin');
```

Option B - By Email:
```sql
INSERT INTO public.user_roles (user_id, role)
SELECT id, 'admin'::public.app_role
FROM auth.users
WHERE email = 'your-email@example.com';
```

Find user IDs in **Dashboard > Authentication > Users**.

### 4. Verify Setup

After a user logs in (or refreshes their token), their JWT will contain:
```json
{
  "user_role": "admin"  // or "user" if not in user_roles table
}
```

## How It Works

1. User authenticates with Supabase
2. Before issuing the JWT, Supabase calls `custom_access_token_hook`
3. The hook looks up the user's role in `user_roles` table
4. The role is added to the JWT as `user_role` claim
5. Your API reads `user_role` from the JWT to authorize requests

## API Usage

Protect admin endpoints using the `require_admin` dependency:

```python
from app.api.deps.auth import get_current_user_id, require_admin

@router.delete("/admin-only/{id}")
async def admin_endpoint(
    id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    _: str = Depends(require_admin),
):
    # Only admins can reach this code
    ...
```

Or require specific roles:

```python
from app.api.deps.auth import require_role

@router.get("/moderator-endpoint")
async def mod_endpoint(
    _: str = Depends(require_role(["admin", "moderator"])),
):
    ...
```
