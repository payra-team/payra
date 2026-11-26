-- Prevent role escalation via direct table writes.
-- Role changes must go through set_group_member_role / remove_group_member RPCs.

DROP POLICY IF EXISTS members_insert_member ON public.conversation_members;
CREATE POLICY members_insert_member ON public.conversation_members
  FOR INSERT TO authenticated
  WITH CHECK (
    public.is_conversation_member(conversation_id)
    AND role = 'member'
    AND user_id IS DISTINCT FROM auth.uid()
    AND EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = user_id)
  );

DROP POLICY IF EXISTS members_update_own ON public.conversation_members;
CREATE POLICY members_update_own ON public.conversation_members
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (
    user_id = auth.uid()
    AND role = (
      SELECT cm.role
      FROM public.conversation_members cm
      WHERE cm.conversation_id = conversation_members.conversation_id
        AND cm.user_id = auth.uid()
    )
  );
