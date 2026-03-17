# Backend FastAPI + Supabase

Backend prêt à brancher sur **Supabase Postgres** avec :
- FastAPI
- SQLAlchemy async
- Docker
- Alembic
- structure modulaire
- endpoints CRUD de base

## 1. Démarrage rapide

```bash
cp .env.example .env
# remplace DATABASE_URL / SYNC_DATABASE_URL par ton URL Supabase Postgres si tu veux pointer directement dessus

docker compose up --build
```

API locale :
- `http://localhost:8000`
- docs Swagger : `http://localhost:8000/docs`

## 2. Brancher Supabase

Dans Supabase > Project Settings > Database, récupère la chaîne de connexion Postgres.

Exemple :
```env
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:[PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
SYNC_DATABASE_URL=postgresql+psycopg://postgres.xxxxx:[PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

## 3. Arborescence

- `app/main.py` : entrée FastAPI
- `app/core/config.py` : settings
- `app/db/session.py` : sessions SQLAlchemy
- `app/models/` : modèles ORM
- `app/schemas/` : schémas Pydantic
- `app/api/v1/` : routes API
- `alembic/` : migrations

## 4. Endpoints inclus

- `GET /health`
- `GET /api/v1/organizations`
- `POST /api/v1/organizations`
- `GET /api/v1/subjects`
- `POST /api/v1/subjects`
- `GET /api/v1/documents`
- `POST /api/v1/documents`

## 5. Suite recommandée

1. Exécuter ton SQL de création des tables dans Supabase
2. Adapter les modèles si besoin
3. Ajouter le RLS côté Supabase
4. Ajouter authentification JWT Supabase
5. Ajouter upload Storage + pipeline OCR / IA

## 6. Alembic

Base prévue pour Alembic, mais comme tu as déjà ton schéma SQL côté Supabase, le plus simple au début est :
- créer les tables dans Supabase via SQL Editor
- utiliser ce backend comme couche API métier

Tu peux ensuite ajouter des migrations Alembic si tu veux gérer tout par code.
