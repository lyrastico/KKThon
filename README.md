# KKThon

Plateforme de traitement automatique de documents administratifs (OCR + structuration + conformité).

## Vision (ce que le projet fait)

- Upload multi-documents (pièces comptables sensibles) côté utilisateur.
- Classification automatique (facture, devis, attestation, etc.) et extraction d'informations clés (SIREN/SIRET, montants, dates, IBAN...).
- Vérification “intelligente” et détection d'incohérences entre les documents d'un même client (avec une validation externe du SIREN).
- Stockage selon une logique Data Lake (Medallion) : `raw/` (brut), `bronze/` (OCR), `silver/` (LLM), et un résultat de conformité (“gold analysis”) stocké côté applicatif.

## Architecture (gros blocs)

Le projet est organisé en 3 composants :

1. `service-backend/`
   - API métier en **FastAPI**
   - Auth **Supabase**
   - Persistance **Postgres (Supabase)** + métadonnées fichiers/rapports
   - Upload des documents vers **AWS S3** dans la zone `raw/`
   - Génération du **gold analysis** (rapport de conformité) à partir des fichiers OCR traités

2. `airflow-astro/`
   - Orchestration event-driven via **Apache Airflow (Astronomer)**
   - DAG `process_document_ocr` :
     - `raw/` -> OCR (Google Document AI) -> `bronze/`
     - OCR text -> extraction structurée (Gemini) -> `silver/`
     - Mise à jour de la table Supabase `public.files` (via un PATCH PostgREST)

3. `front/`
   - Interface **Streamlit**
   - Connexion utilisateur (tokens Supabase)
   - Upload documents et consultation des rapports de conformité

## Flux de traitement de bout en bout

1. Upload d'un document
   - Le front appelle `POST /api/v1/files/upload` avec `client_id` + `file` (multipart).
   - Le backend :
     - upsert automatiquement `public.users`
     - upload le fichier sur S3 dans `raw/<sha256>.<ext>`
     - crée une ligne `files` dans l'état `pending`

2. OCR + structuration (automatique)
   - Un système externe déclenche le DAG Airflow `process_document_ocr` via l'API Airflow avec :
     - `dag_run.conf.bucket`
     - `dag_run.conf.key` (chemin S3 du fichier brut, ex. `raw/abc....pdf`)
   - Le DAG :
     - télécharge depuis S3
     - exécute l'OCR Document AI
     - sauvegarde en `bronze/{stem}.json`
     - envoie le texte OCR à Gemini et obtient un JSON structuré
     - sauvegarde en `silver/{stem}.json`
     - met à jour Supabase `public.files` :
       - `type`, `silver_content`, `s3_silver_path`, `processing_status="done"`

3. Rapport de conformité (“gold analysis”)
   - Le front appelle `POST /api/v1/conformity-reports` avec uniquement `client_id`.
   - Le backend :
     - liste les fichiers du client
     - filtre ceux dont `processing_status == "done"`
     - recalcule une analyse “gold” (consensus + checks)
     - valide l'existence du SIREN via `https://recherche-entreprises.api.gouv.fr/...`
     - enregistre `gold_content` dans `conformity_reports`
     - fixe `processing_status` à `"done"` si des fichiers ont été traités, sinon `"error"`

## Prérequis (avant de lancer)

- Supabase :
  - Exécuter `service-backend/supabase_schema.sql` dans le SQL Editor.
  - Configurer les variables d'environnement du backend (voir `service-backend/api/.env.example`).
- AWS S3 :
  - Bucket accessible par le backend (upload `raw/*`).
  - Bucket accessible par Airflow (lecture `raw/` + écriture `bronze/` et `silver/`).
- Airflow / Clouds :
  - Connexion `document_ai` pour Google Document AI.
  - Accès S3 via `s3_bucket_medaillon`.
  - Connexion Supabase via `supabase_access` (fournit `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` dans le champ `extra`).

## Démarrage local (recommandé)

### 1. Lancer le service backend

```bash
cd service-backend
cd api
cp .env.example .env
docker compose up --build
```

- API : `http://localhost:8001`
- OpenAPI : `http://localhost:8001/docs`
- Health : `GET /health`

### 2. Lancer Airflow (Astronomer)

```bash
cd airflow-astro
astro dev start
```

- Airflow Webserver : `http://localhost:8080/`
- Login : `admin` / `admin`

### 3. Lancer le front Streamlit

```bash
cd front
python -m venv .venv
source .venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

Configurer `front/.env` :

```env
API_BASE_URL=http://localhost:8000
```

Lancer :

```bash
streamlit run app.py
```

- Front : `http://localhost:8501`

## Contrat API (côté backend)

Base URL côté front : `API_BASE_URL/api/v1/`

Endpoints clés :

| Méthode | Route | Usage |
|---------|--------|-------|
| POST | `/auth/login` | Connexion |
| POST | `/auth/register` | Inscription |
| GET | `/auth/me` | Profil utilisateur |
| GET/POST/DELETE | `/clients` | Gestion clients |
| GET/POST/DELETE | `/files` | Gestion fichiers |
| POST | `/files/upload` | Upload document (multipart) |
| GET/POST/DELETE | `/conformity-reports` | Rapports de conformité |

### Upload document (exemple)

`POST /api/v1/files/upload` (multipart) :

- `client_id` (form field)
- `file` (UploadFile)
- `Authorization: Bearer <access_token>`

### Génération rapport de conformité

`POST /api/v1/conformity-reports` :

Requête attendue (minimale) :

```json
{
  "client_id": "<uuid>"
}
```

Le backend recalcule `gold_content` et fixe `processing_status` lui-même.

## Déclenchement du DAG OCR Airflow

Le DAG `process_document_ocr` n'est pas schedule (uniquement déclenché via REST API).

Payload attendu dans `dag_run.conf` :

```json
{
  "bucket": "<AWS_S3_BUCKET>",
  "key": "<chemin S3, ex. raw/abc....pdf>"
}
```

### Test de réception de payload

`airflow-astro/dags/test_s3_event_reception.py` : valide que l'event reçu contient bien `bucket` et `key` (il log `dag_run.conf`).

## Sorties (Data Lake)

- `raw/<sha256>.<ext>` : fichier original uploadé par le backend
- `bronze/{stem}.json` : texte OCR + métadonnées Document AI
- `silver/{stem}.json` : JSON structuré Gemini (document détecté, score de confiance, champs extraits)
- `conformity_reports.gold_content` : “gold analysis” (consensus + checks + éventuellement erreurs)

Pour les schémas JSON exacts des fichiers `bronze/` et `silver/`, voir `airflow-astro/dags/process_document_ocr.py` et `airflow-astro/README.md`.
