-- Migration: Create custom access token hook for RBAC
-- Run this in Supabase SQL Editor AFTER 001_create_user_roles.sql
-- Then enable the hook in: Dashboard > Authentication > Hooks

-- Step 1: Create the auth hook function
-- This function runs before every token is issued and adds user_role to the JWT
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
as $$
declare
    claims jsonb;
    user_role public.app_role;
begin
    -- Fetch the user role from the user_roles table
    select role into user_role
    from public.user_roles
    where user_id = (event->>'user_id')::uuid;

    claims := event->'claims';

    if user_role is not null then
        -- Set the user_role claim
        claims := jsonb_set(claims, '{user_role}', to_jsonb(user_role));
    else
        -- Default to 'user' role if no role is assigned
        claims := jsonb_set(claims, '{user_role}', '"user"');
    end if;

    -- Update the claims in the event
    event := jsonb_set(event, '{claims}', claims);

    return event;
end;
$$;

-- Step 2: Grant necessary permissions to supabase_auth_admin
grant usage on schema public to supabase_auth_admin;

grant execute
    on function public.custom_access_token_hook
    to supabase_auth_admin;

-- Step 3: Revoke access from other roles (security best practice)
revoke execute
    on function public.custom_access_token_hook
    from authenticated, anon, public;

-- Step 4: Grant supabase_auth_admin access to read user_roles
grant all
    on table public.user_roles
    to supabase_auth_admin;

-- Step 5: Revoke direct table access from regular users
-- (They can only access via RLS policies we created in 001)
revoke all
    on table public.user_roles
    from authenticated, anon, public;

-- Re-grant SELECT so RLS policies work
grant select on table public.user_roles to authenticated;

-- Step 6: Create policy for auth admin to read user roles
create policy "Allow auth admin to read user roles"
    on public.user_roles
    as permissive
    for select
    to supabase_auth_admin
    using (true);

-- ============================================================
-- IMPORTANT: After running this SQL, you must enable the hook!
--
-- 1. Go to Supabase Dashboard
-- 2. Navigate to: Authentication > Hooks
-- 3. Find "Custom Access Token" hook
-- 4. Select: public.custom_access_token_hook
-- 5. Click "Save"
-- ============================================================
