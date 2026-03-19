# airflow-astro

Projet Apache Airflow genere avec Astronomer (`astro dev init`).

Ce repo contient un pipeline OCR + structuration pilote par des evenements externes (upload S3 -> Airflow via REST API).

## Contenu du projet

Votre projet Astro contient :

- `dags/` : DAGs Airflow.
- `include/` : modules/plugins personnalises (vide par defaut).
- `packages.txt` : paquets OS (vide par defaut).
- `requirements.txt` : dependances Python utilisees par ce projet.
- `.astro/config.yaml` : metadonnees locales Astro.

## Developpement local (Astronomer)

1. Lancer Airflow localement :
  - `astro dev start`
2. Verifier les containers :
  - `docker ps`
3. Ouvrir l'interface Airflow :
  - `http://localhost:8080/`
  - login : `admin` / `admin`

## Vue d'ensemble des DAGs

### `process_document_ocr` (focus principal)

OCR + extraction d'informations pour des documents administratifs francais :

1. Ingestion via l'API REST d'Airflow lorsque un document est upload dans S3.
2. Telecharge le document depuis S3.
3. Execute l'OCR via Google Document AI.
4. Enregistre le resultat OCR brut dans une zone S3 "bronze".
5. Envoie le texte OCR extrait a Gemini pour extraire des champs structures.
6. Enregistre le JSON structure dans une zone S3 "silver".
7. Met a jour une table Supabase avec le resultat "silver".

### `test_s3_event_reception`

DAG simple pour valider que l'event externe est bien recu par Airflow : il affiche les champs de `dag_run.conf`.

## process_document_ocr.py (details)

### Payload attendu pour le trigger

Le DAG est pilote par evenement et attend que `dag_run.conf` contienne :

```json
{
  "bucket": "s3-agdt-202077714167-eu-north-1-an",
  "key": "raw/document.pdf"
}
```

Si `bucket` ou `key` est manquant, le DAG echoue avec une erreur `ValueError`.

### Connexions Airflow utilisees

Le DAG reference ces identifiants de connexion :

- `s3_bucket_medaillon`
  - Utilise par `S3Hook` pour telecharger le fichier source et ecrire les sorties JSON dans `bronze/` et `silver/`.
- `document_ai`
  - Utilise par les hooks Google pour recuperer les credentials du client Google Document AI.
- `supabase_access`
  - Utilise par `BaseHook.get_connection()` et attend les cles suivantes dans le champ `extra` de la connexion :
    - `SUPABASE_URL`
    - `SUPABASE_SERVICE_ROLE_KEY`

### Parametres OCR Document AI (dans le code)

- `DOCUMENT_AI_PROJECT_ID`: `971677530421`
- `DOCUMENT_AI_LOCATION`: `eu`
- `DOCUMENT_AI_PROCESSOR_ID`: `42d5d89ccd74b863`

Le processor est appele via l'endpoint `documentai.googleapis.com` pour la localisation configuree dans `DOCUMENT_AI_LOCATION`.

### Parametres Gemini (dans le code)

- Modele : `gemini-2.5-flash`
- Endpoint :
  - `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

Le prompt demande au modele de :

- Detecter un type parmi : `Facture`, `Devis`, `Attestation`, `Kbis`, `RIB`, sinon `Inconnu`.
- Extraire uniquement les champs definis dans la section "referentiel" du prompt.
- Retourner un unique objet JSON (sans blocs Markdown).

### Convention de nommage S3 (bronze/silver)

Les noms de fichiers de sortie bronze et silver sont derives du "stem" de la cle d'entree S3 :

- Cle S3 d'entree : `raw/document.pdf`
- Stem du nom : `document`

Ensuite :

- Cle JSON bronze :
  - `bronze/{stem}.json`
- Cle JSON silver :
  - `silver/{stem}.json`

### Flux complet (end-to-end)

Le DAG effectue une jonction finale apres completion de deux branches :

1. Debut commun
  - `download_from_s3`
    - lit `dag_run.conf.bucket` et `dag_run.conf.key`
    - telecharge les bytes depuis S3
    - retourne :
      - `bucket`, `key`, `mime_type`, `content_base64`
      - `mime_type` est infere depuis le nom de fichier ; par defaut `application/pdf`
  - `extract_text_with_document_ai`
    - appelle l'OCR Google Document AI
    - retourne :
      - `bucket`, `key`, `mime_type`
      - `text` (texte OCR complet)
      - `page_count`
      - `confidence` (moyenne des confidences par bloc lorsque disponibles)
2. Branche A (OCR -> bronze)
  - `save_to_bronze`
    - ecrit un JSON S3 dans `bronze/{stem}.json`
3. Branche B (texte OCR -> Gemini -> silver -> Supabase)
  - `extract_structured_with_gemini`
    - envoie le texte OCR a Gemini
    - parse la reponse comme JSON :
      - `_strip_json_fences()` retire les fences optionnelles ```json
      - `json.loads()` parse le JSON
    - normalise :
      - `document_detected` est force a `Inconnu` si non present dans l'ensemble autorise
      - `confidence_score` est converti en float (defaut `0.0`)
      - `data` est garanti comme un objet
  - `save_to_silver`
    - ecrit le JSON structure dans `silver/{stem}.json`
  - `sync_to_supabase`
    - met a jour les lignes de la table Supabase `public.files` :
      - selectionne les lignes avec `s3_raw_path = {input key}`
      - applique un PATCH avec :
        - `s3_silver_path`
        - `silver_content` (payload complet du resultat Gemini)
        - `type` (depuis `result.document_detected`)
        - `processing_status = "done"`
    - echoue si aucune ligne ne matche (attend au moins 1 ligne mise a jour)
4. Etape finale
  - `log_result`
    - affiche ou bronze/silver ont ete sauvegardes
    - affiche le resume de la mise a jour Supabase

### Schema JSON bronze (stocke dans `bronze/...`)

Le fichier bronze contient :

- `source`
  - `bucket`, `key`, `mime_type`
- `processing`
  - `processor_id`, `processor_type`, `processed_at`
- `result`
  - `text`, `page_count`, `confidence`

### Schema JSON silver (stocke dans `silver/...`)

Le fichier silver contient un wrapper autour du resultat Gemini :

- `source`
  - `bucket`, `key`, `mime_type`
- `processing`
  - `model`, `processed_at`
- `result`
  - `document_detected` (string)
  - `confidence_score` (number)
  - `data` (objet contenant les champs extraits)

### Details de mise a jour Supabase

Le DAG appelle le endpoint PostgREST Supabase :

- `PATCH {SUPABASE_URL}/rest/v1/files?s3_raw_path=eq.{encoded_path}`

Headers :

- `apikey: {SUPABASE_SERVICE_ROLE_KEY}`
- `Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}`

Champs du body envoyes :

- `s3_silver_path`
- `silver_content`
- `type`
- `processing_status`

## Lancer le DAG

En general, ce DAG n'est pas schedule. Il est plutot declenche via l'API REST d'Airflow avec le payload `dag_run.conf` decrit plus haut.

Pour tester l'integration de bout en bout, commence par :

- `test_s3_event_reception` (verifie que l'event atteint bien Airflow)

