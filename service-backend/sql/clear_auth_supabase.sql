-- =============================================================================
-- Vider toute la couche Auth Supabase (tous les utilisateurs / sessions)
-- Projet dev / reset uniquement.
--
-- Effet de bord : public.users → auth.users en ON DELETE CASCADE efface aussi
-- tes lignes métier liées (clients, files, reports) selon ton schéma.
-- =============================================================================

-- 1) Dépendances de sessions
delete from auth.refresh_tokens;

-- 2) MFA (ordre : amr lié aux sessions → challenges → factors)
delete from auth.mfa_amr_claims;
delete from auth.mfa_challenges;
delete from auth.mfa_factors;

delete from auth.sessions;

-- 3) Divers (si erreur "relation does not exist", commente la ligne)
delete from auth.one_time_tokens;
delete from auth.flow_state;

-- 4) Identités puis utilisateurs
delete from auth.identities;
delete from auth.users;
