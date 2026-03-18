-- Colle ici ton schéma SQL Supabase validé.
-- Tu peux reprendre le script de création des tables que je t'ai donné juste avant.
-- L'idée : exécuter ce fichier dans Supabase SQL Editor, puis connecter ce backend à ta base.
-- Extensions utiles
create extension if not exists pgcrypto;
 
-- =========================================================
-- 1) Fonction générique updated_at
-- =========================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
 
-- =========================================================
-- 2) TABLE: profiles
-- Profil applicatif d’un utilisateur
-- Lié à auth.users de Supabase
-- =========================================================
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
 
create trigger trg_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();
 
-- =========================================================
-- 3) TABLE: organizations
-- Entreprise cliente
-- =========================================================
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
 
create trigger trg_organizations_updated_at
before update on public.organizations
for each row
execute function public.set_updated_at();
 
-- =========================================================
-- 4) TABLE: organization_members
-- Lien user <-> organization
-- =========================================================
create table if not exists public.organization_members (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null,
  invited_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);
 
create index if not exists idx_org_members_organization_id
  on public.organization_members(organization_id);
 
create index if not exists idx_org_members_user_id
  on public.organization_members(user_id);
 
-- =========================================================
-- 5) TABLE: subjects
-- Dossier / client final
-- =========================================================
create table if not exists public.subjects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  type text not null,
  external_ref text,
  display_name text not null,
  legal_identifier text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
 
create index if not exists idx_subjects_organization_id
  on public.subjects(organization_id);
 
create index if not exists idx_subjects_external_ref
  on public.subjects(external_ref);
 
create index if not exists idx_subjects_legal_identifier
  on public.subjects(legal_identifier);
 
create trigger trg_subjects_updated_at
before update on public.subjects
for each row
execute function public.set_updated_at();
 
-- =========================================================
-- 6) TABLE: document_types
-- Catalogue des types de documents
-- =========================================================
create table if not exists public.document_types (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  label text not null,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
 
-- =========================================================
-- 7) TABLE: documents
-- Document métier principal
-- =========================================================
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  subject_id uuid not null references public.subjects(id) on delete cascade,
  document_type_id uuid references public.document_types(id) on delete set null,
  title text not null,
  status text not null default 'draft',
  current_file_id uuid,
  latest_analysis_run_id uuid,
  compliance_status text,
  review_status text,
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  uploaded_by uuid references public.profiles(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
 
create index if not exists idx_documents_organization_id
  on public.documents(organization_id);
 
create index if not exists idx_documents_subject_id
  on public.documents(subject_id);
 
create index if not exists idx_documents_document_type_id
  on public.documents(document_type_id);
 
create index if not exists idx_documents_status
  on public.documents(status);
 
create trigger trg_documents_updated_at
before update on public.documents
for each row
execute function public.set_updated_at();
 
-- =========================================================
-- 8) TABLE: document_files
-- Fichier physique stocké dans le bucket
-- =========================================================
create table if not exists public.document_files (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  storage_bucket text not null,
  storage_path text not null,
  original_filename text not null,
  mime_type text,
  extension text,
  size_bytes bigint,
  sha256 text,
  page_count integer,
  version_no integer not null default 1,
  upload_status text not null default 'uploaded',
  uploaded_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (document_id, version_no)
);
 
create index if not exists idx_document_files_document_id
  on public.document_files(document_id);
 
create index if not exists idx_document_files_sha256
  on public.document_files(sha256);
 
create index if not exists idx_document_files_storage_path
  on public.document_files(storage_path);
 
-- =========================================================
-- 9) TABLE: analysis_runs
-- Historique des analyses IA document
-- bronze + silver
-- =========================================================
create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  document_file_id uuid references public.document_files(id) on delete set null,
  model_name text not null,
  model_version text,
  status text not null default 'pending',
  bronze_status text,
  silver_status text,
  bronze_output jsonb,
  silver_output jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);
 
create index if not exists idx_analysis_runs_document_id
  on public.analysis_runs(document_id);
 
create index if not exists idx_analysis_runs_document_file_id
  on public.analysis_runs(document_file_id);
 
create index if not exists idx_analysis_runs_status
  on public.analysis_runs(status);
 
create index if not exists idx_analysis_runs_created_at
  on public.analysis_runs(created_at desc);
 
-- =========================================================
-- 10) TABLE: analysis_findings
-- Détails des analyses document
-- =========================================================
create table if not exists public.analysis_findings (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  finding_type text not null,
  code text not null,
  label text not null,
  severity text,
  is_pass boolean,
  confidence numeric(5,4),
  message text,
  extracted_value jsonb,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
 
create index if not exists idx_analysis_findings_analysis_run_id
  on public.analysis_findings(analysis_run_id);
 
create index if not exists idx_analysis_findings_code
  on public.analysis_findings(code);
 
create index if not exists idx_analysis_findings_finding_type
  on public.analysis_findings(finding_type);
 
-- =========================================================
-- 11) TABLE: subject_consistency_runs
-- Analyse gold au niveau dossier
-- =========================================================
create table if not exists public.subject_consistency_runs (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references public.subjects(id) on delete cascade,
  status text not null default 'pending',
  input_analysis_run_ids jsonb not null default '[]'::jsonb,
  gold_output jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);
 
create index if not exists idx_subject_consistency_runs_subject_id
  on public.subject_consistency_runs(subject_id);
 
create index if not exists idx_subject_consistency_runs_status
  on public.subject_consistency_runs(status);
 
create index if not exists idx_subject_consistency_runs_created_at
  on public.subject_consistency_runs(created_at desc);
 
-- =========================================================
-- 12) TABLE: subject_findings
-- Détails des incohérences/cohérences dossier
-- =========================================================
create table if not exists public.subject_findings (
  id uuid primary key default gen_random_uuid(),
  subject_consistency_run_id uuid not null references public.subject_consistency_runs(id) on delete cascade,
  code text not null,
  label text not null,
  severity text,
  is_pass boolean,
  confidence numeric(5,4),
  message text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
 
create index if not exists idx_subject_findings_run_id
  on public.subject_findings(subject_consistency_run_id);
 
create index if not exists idx_subject_findings_code
  on public.subject_findings(code);
 
-- =========================================================
-- 13) TABLE: document_events
-- Historique d’événements
-- =========================================================
create table if not exists public.document_events (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  actor_user_id uuid references public.profiles(id) on delete set null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
 
create index if not exists idx_document_events_document_id
  on public.document_events(document_id);
 
create index if not exists idx_document_events_actor_user_id
  on public.do