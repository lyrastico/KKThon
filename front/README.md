# KKthon - Frontend

Interface web de la plateforme de traitement automatisé de documents administratifs.

## Stack technique

- **Framework** : [Streamlit](https://streamlit.io/) (Python)
- **Visualisation** : Plotly
- **Traitement des données** : Pandas, Polars, PyArrow
- **HTTP** : Requests
- **Navigation** : streamlit-option-menu

## Prérequis

- Python 3.10+
- Backend en cours d'exécution (voir `service-backend/`)

## Installation

```bash
cd front
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine du dossier `front/` :

```env
API_BASE_URL=http://localhost:8000
```

## Lancement

```bash
streamlit run app.py
```

L'application est accessible à `http://localhost:8501`.

## Structure

```
front/
├── app.py                          # Application principale
├── requirements.txt
├── .env
├── components/
│   └── file_progress.py            # Suivi de progression des uploads
└── services/
    ├── auth_service.py             # Authentification
    ├── client_service.py           # Gestion des clients
    ├── file_service.py             # Upload et gestion des fichiers
    └── conformity_report_service.py # Rapports de conformité
```

## Fonctionnalités

### Authentification
- Connexion / inscription
- Gestion des tokens (access + refresh)
- Réinitialisation de mot de passe

### Gestion des clients
- Création, liste et suppression de clients
- Upload de documents par client (PDF, PNG, JPG, JPEG)
- Suivi en temps réel du traitement (OCR → analyse → disponibilité)
- Visualisation des données extraites avec scores de confiance

### Rapports de conformité
- Génération de rapports automatiques par client
- Verdict global (pass / fail / inconnu)
- Détail des contrôles : documents manquants, anomalies détectées, fichiers sources

### Tableau de bord
- Métriques clés : documents traités, précision OCR, temps économisé
- Graphique d'évolution du volume d'extraction

## Pages

| Page | Description |
|------|-------------|
| Tableau de bord | Vue d'ensemble et statistiques |
| Liste clients | Gestion des clients et de leurs documents |
| Historique | Explorateur de données exportées |

## Endpoints API consommés

Base URL : `API_BASE_URL/api/v1/`

| Méthode | Route | Usage |
|---------|-------|-------|
| POST | `/auth/login` | Connexion |
| POST | `/auth/register` | Inscription |
| GET | `/auth/me` | Profil utilisateur |
| GET/POST/DELETE | `/clients` | Gestion clients |
| GET/POST/DELETE | `/files` | Gestion fichiers |
| GET/POST/DELETE | `/conformity-reports` | Rapports de conformité |
