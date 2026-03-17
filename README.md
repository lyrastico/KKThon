# SUJET DU PROJET

Traitement automatique de documents administratifs

Vous allez développer en équipe une plateforme permettant :

i - l’upload multi-documents : pièces comptables sensibles

ii - Classification automatique : factures, devis, attestation, etc.

iii - Extraction des informations clés via OCR robustes : num SIREN, montants, ...

iv - Vérification intelligente et détection automatique d’incohérences entre ces différents documents (éventuellement documents frauduleux) : incohérence entre SIRET et sur attestation et celle sur facture, par exemple

v - Stockage suivant une logique Data Lake : raw zone, clean zone et curated zone ; Architecture Medallion : bronze, silver et gold

vi - Remplissage automatique de 2 front-ends ; applications métiers, par exemple : CRM et outil de conformité (éventuellement BDD fournisseur)

# STRUCTURE DU PROJET

amazon s3 bucket qui contient une archi data lake :
- raw <- fichiers bruts (images, pdf, etc...)
- bronze <- fichiers traités par OCR
- silver <- fichiers traités par LLM
- gold <- remontée des incohérences entre les différents documents d'un même client

orchestration airflow via astro (astronomer) :
- raw -> bronze (OCR)
- bronze -> silver (LLM)
- silver -> gold (Remonter des incohérences)

un OCR cloud (Document AI) qui va analyser les documents et les transformer en texte :
- raw -> text -> bronze (au format parquet ou json, à définir)

un LLM qui va analyser le texte et nous donner l'information de manière structurée :
- text -> json -> silver (au format parquet ou json, à définir)

1 frontend streamlit ou l'on s'authentifie en tant que gestionnaire de clients, un client regroupe plusieurs documents :
- factures
- devis
- KBIS
- etc...
le gestionnaire de clients vérifie que chacun des ses clients est bien conforme à la réglementation (RGPD, LGPD, etc...), il est aidé par notre outil qui croise les informations entre les différents documents.

le streamlit est appuyé par une DB Supabase pour : 
- les comptes gestionnaires de clients
- les clients
- les documents (accès à la silver & raw zone requise)
- les incohérences (accès à la gold & silver zone requise)

# BDD

1. Structure générale

utilisateurs : profiles
entreprises clientes : organizations
membres d’une entreprise : organization_members
dossiers / clients finaux : subjects
types de documents : document_types
documents métiers : documents
fichiers uploadés : document_files
analyses IA document : analysis_runs
détails des analyses document : analysis_findings
analyses de cohérence dossier : subject_consistency_runs
détails des incohérences dossier : subject_findings
historique : document_events

2 . Tables 

profiles
Profil applicatif d’un utilisateur.

Champs :
- id
- email
- full_name
- is_active
- created_at
- updated_at


organizations
Entreprise cliente de la plateforme.

Champs :
- id
- name
- slug
- is_active
- created_at
- updated_at


organization_members
Lien entre un utilisateur et une organisation avec son rôle.

Champs :
- id
- organization_id
- user_id
- role
- invited_by
- created_at


subjects
Dossier / client final géré par une organisation.

Champs :
- id
- organization_id
- type
- external_ref
- display_name
- legal_identifier
- metadata
- created_by
- created_at
- updated_at


document_types
Catalogue des types de documents.

Champs :
- id
- code
- label
- description
- is_active
- created_at


documents
Objet métier principal représentant un document dans l’application.

Champs :
- id
- organization_id
- subject_id
- document_type_id
- title
- status
- current_file_id
- latest_analysis_run_id
- compliance_status
- review_status
- reviewed_by
- reviewed_at
- uploaded_by
- metadata
- created_at
- updated_at


document_files
Fichier physique réellement stocké dans le bucket S3.

Champs :
- id
- document_id
- storage_bucket
- storage_path
- original_filename
- mime_type
- extension
- size_bytes
- sha256
- page_count
- version_no
- upload_status
- uploaded_by
- created_at


analysis_runs
Historique des analyses IA au niveau document.
Cette table porte les sorties bronze et silver.

Champs :
- id
- document_id
- document_file_id
- model_name
- model_version
- status
- bronze_status
- silver_status
- bronze_output
- silver_output
- error_message
- created_at
- started_at
- finished_at


analysis_findings
Détails issus des analyses documentaires.
Cette table sert surtout à stocker les contrôles techniques, les champs extraits, les alertes et les checks de conformité au niveau document.

Champs :
- id
- analysis_run_id
- finding_type
- code
- label
- severity
- is_pass
- confidence
- message
- extracted_value
- details
- created_at


subject_consistency_runs
Historique des analyses gold au niveau dossier / client final.
Cette table sert à comparer les résultats silver de plusieurs documents d’un même subject.

Champs :
- id
- subject_id
- status
- input_analysis_run_ids
- gold_output
- error_message
- created_at
- started_at
- finished_at


subject_findings
Détails des incohérences ou cohérences détectées au niveau dossier.

Champs :
- id
- subject_consistency_run_id
- code
- label
- severity
- is_pass
- confidence
- message
- details
- created_at


document_events
Historique des événements liés à un document.

Champs :
- id
- document_id
- actor_user_id
- event_type
- payload
- created_at

3. Logique métier des tables

profiles
Stocke le profil applicatif de chaque utilisateur connecté.

organizations
Représente une entreprise cliente de la plateforme.

organization_members
Permet de gérer les rôles et l’appartenance d’un utilisateur à une organisation.

subjects
Représente le dossier client final sur lequel les documents sont déposés et analysés.

document_types
Normalise les types de documents supportés par la plateforme.

documents
Représente le document métier dans l’application, indépendamment du fichier physique.

document_files
Stocke la référence du fichier physique dans S3, ainsi que ses métadonnées techniques.

analysis_runs
Conserve l’historique du pipeline documentaire pour un document donné.
Contient la sortie bronze et silver.

analysis_findings
Détaille les points remontés par l’analyse d’un document :
- détection du type
- extraction de champ
- contrôles techniques
- contrôles de conformité
- alertes

subject_consistency_runs
Conserve l’historique des analyses gold au niveau dossier.
Permet de recalculer la cohérence globale quand un nouveau document est ajouté.

subject_findings
Détaille les incohérences entre plusieurs documents d’un même dossier :
- noms divergents
- adresses différentes
- dates incohérentes
- informations société contradictoires
- dossier incomplet

document_events
Permet de garder une traçabilité complète des événements sur un document.

