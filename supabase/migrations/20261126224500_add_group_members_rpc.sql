-- Add members to an existing group (admin-only), mirroring create_group_conversation.
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

  if not public.is_conversation_admin(p_conversation_id) then
    raise exception 'Only group admins can add members';
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

REVOKE ALL ON FUNCTION public.add_group_members(uuid, uuid[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.add_group_members(uuid, uuid[]) FROM anon;
GRANT EXECUTE ON FUNCTION public.add_group_members(uuid, uuid[]) TO authenticated;
