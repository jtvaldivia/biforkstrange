-- Historias interactivas: un documento JSON por partida (capítulos, dilema actual, epílogo).
create table if not exists public.stories (
  id uuid primary key,
  profile_id uuid,
  user_id uuid references auth.users(id) on delete cascade,
  doc jsonb not null,
  created_at timestamptz not null default now()
);

alter table public.stories enable row level security;

create policy "read own stories" on public.stories
  for select using (auth.uid() = user_id);
