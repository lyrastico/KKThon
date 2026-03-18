-- =============================================================================
-- KKThon service-backend — schéma Supabase (public.users, clients, files, conformity_reports)
-- Exécuter dans Supabase SQL Editor (après création du projet).
-- Pas de colonne password : l’auth reste sur auth.users (Supabase Auth).
-- =============================================================================

create extension if not exists pgcrypto;

-- -----------------------------------------------------------------------------
-- updated_at automatique
-- -----------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- -----------------------------------------------------------------------------
-- public.users — profil métier 1:1 avec auth.users (pas de mot de passe ici)
-- -----------------------------------------------------------------------------
create table if not exists public.users (
  user_id uuid primary key references auth.users (id) on delete cascade,
  email text,
  fullname text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_users_email on public.users (email);

create trigger trg_users_updated_at
before update on public.users
for each row
execute function public.set_updated_at();

-- Création automatique d’une ligne public.users à l’inscription Supabase Auth
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (user_id, email, fullname)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'fullname')
  )
  on conflict (user_id) do update
    set email = excluded.email,
        fullname = coalesce(excluded.fullname, public.users.fullname),
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_auth_user();

-- -----------------------------------------------------------------------------
-- clients
-- -----------------------------------------------------------------------------
create table if not exists public.clients (
  client_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (user_id) on delete cascade,
  client_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_clients_user_id on public.clients (user_id);

create trigger trg_clients_updated_at
before update on public.clients
for each row
execute function public.set_updated_at();

-- -----------------------------------------------------------------------------
-- files (raw S3 : raw/<sha256>.<ext> — Airflow complète type, silver, statut…)
-- -----------------------------------------------------------------------------
create table if not exists public.files (
  file_id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients (client_id) on delete cascade,
  original_filename text not null,
  s3_raw_path text not null,
  s3_silver_path text,
  silver_content jsonb,
  file_format text,
  type text,
  processing_status text not null default 'pending'
    check (processing_status in ('pending', 'error', 'done')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_files_s3_raw_path unique (s3_raw_path)
);

create index if not exists idx_files_client_id on public.files (client_id);
create index if not exists idx_files_processing_status on public.files (processing_status);

create trigger trg_files_updated_at
before update on public.files
for each row
execute function public.set_updated_at();

-- -----------------------------------------------------------------------------
-- conformity_reports
-- -----------------------------------------------------------------------------
create table if not exists public.conformity_reports (
  report_id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients (client_id) on delete cascade,
  gold_content jsonb,
  s3_gold_path text,
  silver_content jsonb,
  processing_status text not null default 'pending'
    check (processing_status in ('pending', 'error', 'done')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_conformity_reports_client_id on public.conformity_reports (client_id);

create trigger trg_conformity_reports_updated_at
before update on public.conformity_reports
for each row
execute function public.set_updated_at();

-- =============================================================================
-- RLS (optionnel) — décommenter pour activer l’accès direct depuis le front
-- Le backend FastAPI utilise souvent le rôle service_role / connexion directe :
-- dans ce cas RLS ne s’applique pas. Pour client Supabase (anon) uniquement :
-- =============================================================================
-- alter table public.users enable row level security;
-- alter table public.clients enable row level security;
-- alter table public.files enable row level security;
-- alter table public.conformity_reports enable row level security;
--
-- create policy "users_select_own" on public.users for select using (auth.uid() = user_id);
-- create policy "users_update_own" on public.users for update using (auth.uid() = user_id);
--
-- create policy "clients_all_own" on public.clients for all
--   using (user_id = auth.uid()) with check (user_id = auth.uid());
--
-- create policy "files_via_client" on public.files for all
--   using (
--     exists (select 1 from public.clients c where c.client_id = files.client_id and c.user_id = auth.uid())
--   ) with check (
--     exists (select 1 from public.clients c where c.client_id = files.client_id and c.user_id = auth.uid())
--   );
--
-- create policy "reports_via_client" on public.conformity_reports for all
--   using (
--     exists (select 1 from public.clients c where c.client_id = conformity_reports.client_id and c.user_id = auth.uid())
--   ) with check (
--     exists (select 1 from public.clients c where c.client_id = conformity_reports.client_id and c.user_id = auth.uid())
--   );
