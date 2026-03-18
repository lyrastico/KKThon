# Service backend (KKThon)

API métier **FastAPI** + **Supabase Auth** + **Postgres (Supabase)** + upload **AWS S3** (zone `raw/`).  
Schéma SQL : [`supabase_schema.sql`](supabase_schema.sql). Modèle logique : [`schema_database.md`](schema_database.md) (sans mot de passe en base : auth = `auth.users`).

## Prérequis

1. Projet Supabase : exécuter **`supabase_schema.sql`** dans le SQL Editor.
2. Variables d’environnement (voir [`api/.env.example`](api/.env.example)).
3. Bucket S3 avec credentials autorisant `PutObject` sur `raw/*`.

## Démarrage API

```bash
cd api
cp .env.example .env
# Éditer .env (DATABASE_URL, SUPABASE_*, AWS_*)

docker compose up --build
```

- API : <http://localhost:8001> (port mappé pour ne pas chevaucher l’ancien backend).
- OpenAPI : <http://localhost:8001/docs>
- Health : `GET /health`

### Connexion Postgres Supabase

Utiliser l’URL **pooler** recommandée par Supabase, en **async** :

`postgresql+asyncpg://postgres.[ref]:[PASSWORD]@aws-0-....pooler.supabase.com:6543/postgres`

Sync (Alembic optionnel) : `postgresql+psycopg://...` même hôte/credentials.

## Authentification

Toutes les routes métier (sauf `/api/v1/auth/*`) exigent :

`Authorization: Bearer <access_token>`  
(token renvoyé par `POST /api/v1/auth/login` ou `register`).

**Inscription sans vérification e-mail** : définir **`SUPABASE_SERVICE_ROLE_KEY`** dans l’`.env` du backend uniquement.  
`POST /auth/register` crée l’utilisateur via l’API Admin avec `email_confirm: true`, puis ouvre une session (pas d’e-mail de confirmation).  
Sans cette clé, l’endpoint register renvoie `503`.

| Méthode | Route | Description |
|---------|--------|-------------|
| POST | `/api/v1/auth/register` | Inscription (compte déjà confirmé, tokens si OK) |
| POST | `/api/v1/auth/login` | Connexion |
| POST | `/api/v1/auth/refresh` | Rafraîchir le token |
| POST | `/api/v1/auth/forgot-password` | Email reset |
| GET | `/api/v1/auth/me` | Infos JWT (Supabase) |

À l’inscription, le trigger SQL crée une ligne dans **`public.users`**. Sinon : `POST /api/v1/users/sync`.

## Utilisateurs (`public.users`)

| Méthode | Route | Description |
|---------|--------|-------------|
| POST | `/api/v1/users/sync` | Crée / met à jour la ligne métier pour le JWT |
| GET | `/api/v1/users/me` | Profil courant |
| GET | `/api/v1/users` | Liste (un seul élément : vous) |
| GET | `/api/v1/users/{user_id}` | Détail si `user_id` = vous |
| PATCH | `/api/v1/users/me` | Mise à jour `email`, `fullname` |
| DELETE | `/api/v1/users/me` | Supprime la ligne `public.users` (cascade clients/fichiers/rapports). Le compte **auth.users** reste dans Supabase sauf suppression côté dashboard / Admin API. |

## Clients

| Méthode | Route | Description |
|---------|--------|-------------|
| GET | `/api/v1/clients` | Liste des clients du user |
| POST | `/api/v1/clients` | Création `{ "client_name": "..." }` |
| GET | `/api/v1/clients/{client_id}` | Détail |
| PATCH | `/api/v1/clients/{client_id}` | Mise à jour |
| DELETE | `/api/v1/clients/{client_id}` | Suppression |

## Fichiers

| Méthode | Route | Description |
|---------|--------|-------------|
| POST | `/api/v1/files/upload` | **Multipart** : `client_id` (form) + `file`. Hash SHA-256 → clé S3 `raw/<sha256>.<ext>`, ligne `files` en `pending`. Idempotence : même contenu = même clé = même ligne (retour existant). |
| GET | `/api/v1/files?client_id=...` | Liste par client |
| POST | `/api/v1/files` | Création manuelle si fichier déjà sur S3 |
| GET | `/api/v1/files/{file_id}` | Détail |
| PATCH | `/api/v1/files/{file_id}` | Mise à jour (ex. pour tests ; en prod souvent **Airflow** met à jour `type`, `silver_content`, `processing_status`, `s3_silver_path`) |
| DELETE | `/api/v1/files/{file_id}` | Suppression ligne (objet S3 non supprimé ici) |

**Airflow** : le DAG attend `dag_run.conf` :

```json
{
  "bucket": "<AWS_S3_BUCKET>",
  "key": "<valeur de s3_raw_path, ex. raw/abc....pdf>"
}
```

Le pipeline peut ensuite mettre à jour la table `files` (type document, silver, statut).

## Rapports de conformité

| Méthode | Route | Description |
|---------|--------|-------------|
| GET | `/api/v1/conformity-reports?client_id=...` | Liste |
| POST | `/api/v1/conformity-reports` | Création |
| GET | `/api/v1/conformity-reports/{report_id}` | Détail |
| PATCH | `/api/v1/conformity-reports/{report_id}` | Mise à jour |
| DELETE | `/api/v1/conformity-reports/{report_id}` | Suppression |

## Exemple Streamlit (upload)

```python
import requests

API = "http://localhost:8001"
token = "..."  # après login

client_id = "uuid-du-client"
with open("doc.pdf", "rb") as f:
    r = requests.post(
        f"{API}/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"client_id": client_id},
        files={"file": ("doc.pdf", f, "application/pdf")},
        timeout=120,
    )
r.raise_for_status()
file_row = r.json()
print("s3_raw_path (key Airflow):", file_row["s3_raw_path"])
```

## RLS Supabase

Des policies commentées sont fournies en fin de **`supabase_schema.sql`**.  
Si l’API se connecte avec le rôle **postgres** / service, RLS ne s’applique pas. Active-les seulement pour un accès direct client (anon) sécurisé.

## Arborescence

```
service-backend/
  schema_database.md      # modèle logique
  supabase_schema.sql     # création tables + trigger auth → public.users
  README.md
  api/
    app/
      main.py
      api/v1/             # routes
      models/             # SQLAlchemy
      repositories/
      services/           # Supabase client, S3
    Dockerfile
    docker-compose.yml
    .env.example
```
