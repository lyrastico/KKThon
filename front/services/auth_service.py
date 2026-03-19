import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL")
AUTH_URL = f"{BASE_URL}/api/v1/auth"


class AuthServiceError(Exception):
    pass


def login(email: str, password: str) -> dict:
    """Authentifie un utilisateur et retourne access_token, refresh_token, user."""
    response = requests.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if response.status_code == 401:
        raise AuthServiceError("Email ou mot de passe incorrect.")
    if not response.ok:
        detail = response.json().get("detail", "Erreur de connexion.")
        raise AuthServiceError(detail)
    return response.json()


def register(email: str, password: str, full_name: str) -> dict:
    """Crée un nouveau compte utilisateur."""
    response = requests.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": full_name},
        timeout=10,
    )
    if not response.ok:
        detail = response.json().get("detail", "Erreur lors de l'inscription.")
        raise AuthServiceError(detail)
    return response.json()


def refresh_token(refresh_token: str) -> dict:
    """Renouvelle l'access_token à partir du refresh_token."""
    response = requests.post(
        f"{AUTH_URL}/refresh",
        json={"refresh_token": refresh_token},
        timeout=10,
    )
    if not response.ok:
        raise AuthServiceError("Session expirée, veuillez vous reconnecter.")
    return response.json()


def get_me(access_token: str) -> dict:
    """Retourne le profil de l'utilisateur connecté."""
    response = requests.get(
        f"{AUTH_URL}/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if not response.ok:
        raise AuthServiceError("Token invalide ou expiré.")
    return response.json()


def forgot_password(email: str) -> None:
    """Envoie un email de réinitialisation de mot de passe."""
    response = requests.post(
        f"{AUTH_URL}/forgot-password",
        json={"email": email},
        timeout=10,
    )
    if not response.ok:
        detail = response.json().get("detail", "Erreur lors de l'envoi de l'email.")
        raise AuthServiceError(detail)
