-- Mirror of applied MCP migration: payra_core_schema
-- Source of truth is the live Supabase project; this file documents schema for the repo.

-- profiles, conversations, conversation_members, messages
-- + handle_new_user trigger, get_or_create_direct_conversation, create_group_conversation
-- + chat-images storage bucket + realtime publication
-- See docs/tasks/02_schema_verify.md and subsequent migrations:
--   grant_table_privileges
--   fix_rls_recursion
--   revoke_anon_rpc_execute
