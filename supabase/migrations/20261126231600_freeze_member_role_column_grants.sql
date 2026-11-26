-- Freeze role escalation: clients may only update starred/last_read_at.
-- Role changes go through SECURITY DEFINER RPCs.

DROP POLICY IF EXISTS members_update_own ON public.conversation_members;
CREATE POLICY members_update_own ON public.conversation_members
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

REVOKE UPDATE ON TABLE public.conversation_members FROM authenticated;
GRANT UPDATE (starred, last_read_at) ON TABLE public.conversation_members TO authenticated;

DROP POLICY IF EXISTS members_insert_member ON public.conversation_members;
CREATE POLICY members_insert_member ON public.conversation_members
  FOR INSERT TO authenticated
  WITH CHECK (
    public.is_conversation_member(conversation_id)
    AND role = 'member'
    AND user_id IS DISTINCT FROM auth.uid()
    AND EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = user_id)
  );
