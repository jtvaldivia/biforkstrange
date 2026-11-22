-- Perfil del gemelo digital: un documento JSON por persona (encuestas adaptativas, examen a ciegas, notas).
-- `version` permite escrituras condicionales: una pestaña vieja no pisa datos más nuevos.
create table if not exists public.twin_profiles (
  id uuid primary key,
  user_id uuid references auth.users(id) on delete cascade,
  version integer not null default 0,
  doc jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.twin_profiles enable row level security;

-- cada usuario lee su propio perfil; el backend escribe con service key (salta RLS)
create policy "read own twin profile" on public.twin_profiles
  for select using (auth.uid() = user_id);
