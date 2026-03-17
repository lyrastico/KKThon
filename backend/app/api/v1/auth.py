from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import RegisterRequest, LoginRequest, ForgotPasswordRequest, RefreshRequest, AuthResponse
from app.services.supabase_auth import get_supabase_public
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest):
    client = get_supabase_public()
    try:
        response = client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"full_name": payload.full_name}},
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    session = response.session.model_dump() if response.session else None
    user = response.user.model_dump() if response.user else None

    return AuthResponse(
        access_token=session.get("access_token") if session else None,
        refresh_token=session.get("refresh_token") if session else None,
        user=user,
        session=session,
        message="User registered",
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
        "user_metadata": current_user.user_metadata,
    }