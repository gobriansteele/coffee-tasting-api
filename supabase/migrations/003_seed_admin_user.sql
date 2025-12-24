-- Migration: Seed initial admin user
-- Run this AFTER the auth hook is enabled
-- Replace YOUR_USER_ID with your actual Supabase user UUID

-- Option 1: Add admin role by user ID
-- Find your user ID in: Dashboard > Authentication > Users
-- insert into public.user_roles (user_id, role)
-- values
--     ('YOUR_USER_ID_HERE', 'admin')
-- on conflict (user_id, role) do nothing;

-- Option 2: Add admin role by email (if you know the email)
-- Uncomment and modify this query:
insert into public.user_roles (user_id, role)
select id, 'admin'::public.app_role
from auth.users
where email = 'brsteele2123@gmail.com'
on conflict (user_id, role) do nothing;

-- Verify the role was added:
-- select u.email, ur.role, ur.created_at
-- from public.user_roles ur
-- join auth.users u on u.id = ur.user_id;
