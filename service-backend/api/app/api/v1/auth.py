from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    RefreshRequest,
    AuthResponse,
)
from app.services.supabase_auth import get_supabase_public, get_supabase_admin
from app.core.config import settings
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest):
    """
    Inscription **sans e-mail de confirmation** : compte créé déjà confirmé.
    Nécessite `SUPABASE_SERVICE_ROLE_KEY` côté API (jamais côté client).
    """
    if not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Inscription désactivée : configurez SUPABASE_SERVICE_ROLE_KEY sur le backend "
                "(inscription sans vérification e-mail via Admin API)."
            ),
        )
    admin = get_supabase_admin()
    public = get_supabase_public()
    meta = {"full_name": payload.full_name or ""}
    try:
        admin.auth.admin.create_user(
            {
                "email": str(payload.email),
                "password": payload.password,
                "email_confirm": True,
                "user_metadata": meta,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        response = public.auth.sign_in_with_password(
            {"email": str(payload.email), "password": payload.password}
        )
    except Exception as e:
        return AuthResponse(
            access_token=None,
            refresh_token=None,
            user=None,
            session=None,
            message=f"Compte créé (e-mail déjà confirmé). Utilisez POST /auth/login : {e}",
        )

    session = response.session.model_dump() if response.session else None
    user = response.user.model_dump() if response.user else None
    return AuthResponse(
        access_token=session.get("access_token") if session else None,
        refresh_token=session.get("refresh_token") if session else None,
        user=user,
        session=session,
        message="User registered (no email verification)",
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    client = get_supabase_public()
    try:
        response = client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    session = response.session.model_dump() if response.session else None
    user = response.user.model_dump() if response.user else None
    return AuthResponse(
        access_token=session.get("access_token") if session else None,
        refresh_token=session.get("refresh_token") if session else None,
        user=user,
        session=session,
        message="Login successful",
    )


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    client = get_supabase_public()
    client.auth.reset_password_email(payload.email)
    return {"message": "Password reset email sent"}


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(payload: RefreshRequest):
    client = get_supabase_public()
    response = client.auth.refresh_session(payload.refresh_token)
    session = response.session.model_dump() if response.session else None
    user = response.user.model_dump() if response.user else None
    return AuthResponse(
        access_token=session.get("access_token") if session else None,
        refresh_token=session.get("refresh_token") if session else None,
        user=user,
        session=session,
        message="Token refreshed",
    )


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "user_metadata": getattr(current_user, "user_metadata", None) or {},
    }
