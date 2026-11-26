-- Any group member can add people; admins keep role/remove settings.
-- Also: set group avatar, set member role, remove/leave member.

CREATE OR REPLACE FUNCTION public.add_group_members(
  p_conversation_id uuid,
  p_member_ids uuid[]
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  me uuid := auth.uid();
  mid uuid;
  added integer := 0;
  is_group boolean;
begin
  if me is null then
    raise exception 'Not authenticated';
  end if;

  select (type = 'group') into is_group
  from public.conversations
  where id = p_conversation_id;

  if is_group is null then
    raise exception 'Conversation not found';
  end if;
  if not is_group then
    raise exception 'Not a group conversation';
  end if;

  if not public.is_conversation_member(p_conversation_id) then
    raise exception 'Only group members can add people';
  end if;

  if p_member_ids is null or cardinality(p_member_ids) = 0 then
    return 0;
  end if;

  foreach mid in array p_member_ids loop
    if mid is distinct from me
       and exists (select 1 from public.profiles where id = mid)
       and not exists (
         select 1
         from public.conversation_members
         where conversation_id = p_conversation_id
           and user_id = mid
       ) then
      insert into public.conversation_members (conversation_id, user_id, role)
      values (p_conversation_id, mid, 'member');
      added := added + 1;
    end if;
  end loop;

  if added > 0 then
    update public.conversations
    set updated_at = now()
    where id = p_conversation_id;
  end if;

  return added;
end;
$function$;

DROP POLICY IF EXISTS members_insert_admin ON public.conversation_members;
CREATE POLICY members_insert_member ON public.conversation_members
  FOR INSERT TO authenticated
  WITH CHECK (public.is_conversation_member(conversation_id));

CREATE OR REPLACE FUNCTION public.set_group_member_role(
  p_conversation_id uuid,
  p_user_id uuid,
  p_role text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  me uuid := auth.uid();
  is_group boolean;
  target_role text;
  admin_count integer;
begin
  if me is null then
    raise exception 'Not authenticated';
  end if;
  if p_role is null or p_role not in ('admin', 'member') then
    raise exception 'Role must be admin or member';
  end if;

  select (type = 'group') into is_group
  from public.conversations
  where id = p_conversation_id;
  if is_group is null then
    raise exception 'Conversation not found';
  end if;
  if not is_group then
    raise exception 'Not a group conversation';
  end if;

  if not public.is_conversation_admin(p_conversation_id) then
    raise exception 'Only group admins can change roles';
  end if;

  select role into target_role
  from public.conversation_members
  where conversation_id = p_conversation_id and user_id = p_user_id;
  if target_role is null then
    raise exception 'User is not a member of this group';
  end if;

  if target_role = 'admin' and p_role = 'member' then
    select count(*) into admin_count
    from public.conversation_members
    where conversation_id = p_conversation_id and role = 'admin';
    if admin_count <= 1 then
      raise exception 'Cannot demote the last admin';
    end if;
  end if;

  update public.conversation_members
  set role = p_role
  where conversation_id = p_conversation_id and user_id = p_user_id;

  update public.conversations
  set updated_at = now()
  where id = p_conversation_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.remove_group_member(
  p_conversation_id uuid,
  p_user_id uuid
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  me uuid := auth.uid();
  is_group boolean;
  target_role text;
  admin_count integer;
begin
  if me is null then
    raise exception 'Not authenticated';
  end if;

  select (type = 'group') into is_group
  from public.conversations
  where id = p_conversation_id;
  if is_group is null then
    raise exception 'Conversation not found';
  end if;
  if not is_group then
    raise exception 'Not a group conversation';
  end if;

  select role into target_role
  from public.conversation_members
  where conversation_id = p_conversation_id and user_id = p_user_id;
  if target_role is null then
    raise exception 'User is not a member of this group';
  end if;

  if p_user_id is distinct from me and not public.is_conversation_admin(p_conversation_id) then
    raise exception 'Only group admins can remove other members';
  end if;

  if target_role = 'admin' then
    select count(*) into admin_count
    from public.conversation_members
    where conversation_id = p_conversation_id and role = 'admin';
    if admin_count <= 1 then
      raise exception 'Cannot remove the last admin';
    end if;
  end if;

  delete from public.conversation_members
  where conversation_id = p_conversation_id and user_id = p_user_id;

  update public.conversations
  set updated_at = now()
  where id = p_conversation_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.set_group_avatar(
  p_conversation_id uuid,
  p_avatar_url text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
declare
  me uuid := auth.uid();
  is_group boolean;
begin
  if me is null then
    raise exception 'Not authenticated';
  end if;

  select (type = 'group') into is_group
  from public.conversations
  where id = p_conversation_id;
  if is_group is null then
    raise exception 'Conversation not found';
  end if;
  if not is_group then
    raise exception 'Not a group conversation';
  end if;
  if not public.is_conversation_member(p_conversation_id) then
    raise exception 'Only group members can update the group photo';
  end if;

  update public.conversations
  set avatar_url = coalesce(p_avatar_url, ''),
      updated_at = now()
  where id = p_conversation_id;
end;
$function$;

REVOKE ALL ON FUNCTION public.add_group_members(uuid, uuid[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.add_group_members(uuid, uuid[]) FROM anon;
GRANT EXECUTE ON FUNCTION public.add_group_members(uuid, uuid[]) TO authenticated;

REVOKE ALL ON FUNCTION public.set_group_member_role(uuid, uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.set_group_member_role(uuid, uuid, text) FROM anon;
GRANT EXECUTE ON FUNCTION public.set_group_member_role(uuid, uuid, text) TO authenticated;

REVOKE ALL ON FUNCTION public.remove_group_member(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.remove_group_member(uuid, uuid) FROM anon;
GRANT EXECUTE ON FUNCTION public.remove_group_member(uuid, uuid) TO authenticated;

REVOKE ALL ON FUNCTION public.set_group_avatar(uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.set_group_avatar(uuid, text) FROM anon;
GRANT EXECUTE ON FUNCTION public.set_group_avatar(uuid, text) TO authenticated;

DROP POLICY IF EXISTS avatars_insert_group_folder ON storage.objects;
CREATE POLICY avatars_insert_group_folder ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = 'groups'
    AND public.is_conversation_member(((storage.foldername(name))[2])::uuid)
  );

DROP POLICY IF EXISTS avatars_update_group_folder ON storage.objects;
CREATE POLICY avatars_update_group_folder ON storage.objects
  FOR UPDATE TO authenticated
  USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = 'groups'
    AND public.is_conversation_member(((storage.foldername(name))[2])::uuid)
  )
  WITH CHECK (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = 'groups'
    AND public.is_conversation_member(((storage.foldername(name))[2])::uuid)
  );

DROP POLICY IF EXISTS avatars_delete_group_folder ON storage.objects;
CREATE POLICY avatars_delete_group_folder ON storage.objects
  FOR DELETE TO authenticated
  USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = 'groups'
    AND public.is_conversation_member(((storage.foldername(name))[2])::uuid)
  );
