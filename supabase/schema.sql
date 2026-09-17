-- Run this in Supabase SQL Editor (Project > SQL Editor > New query)

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  question text not null,
  answer text not null,
  source text check (source in ('company_data_or_general','refused')) not null,
  created_at timestamptz default now()
);

alter table messages enable row level security;

create policy "Users can read own messages"
  on messages for select
  using (auth.uid() = user_id);

create policy "Users can insert own messages"
  on messages for insert
  with check (auth.uid() = user_id);

-- In Supabase Dashboard: Authentication > Providers > enable Google,
-- and add your OAuth client ID/secret from Google Cloud Console.
-- Also add your frontend URL (e.g. http://localhost:5173) under
-- Authentication > URL Configuration > Redirect URLs.
