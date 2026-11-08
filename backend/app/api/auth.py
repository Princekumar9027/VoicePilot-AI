from datetime import datetime, timedelta, timezone

try:
    # OAuth is optional for local development. Authlib/JoseRFC can require
    # cryptography, which may be unavailable on restricted Windows systems.
    from authlib.integrations.starlette_client import OAuth, OAuthError
    OAUTH_AVAILABLE = True
except (ImportError, OSError):
    OAuth = None

    class OAuthError(Exception):
        pass

    OAUTH_AVAILABLE = False
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.database.session import get_db
from app.models.entities import AuditLog, OAuthAccount, RefreshToken, User
from app.schemas.auth import AuthOut, LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

oauth = OAuth() if OAUTH_AVAILABLE else None
PROVIDERS: list[str] = []

if oauth is not None and settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    PROVIDERS.append("google")

if oauth is not None and settings.github_client_id and settings.github_client_secret:
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    PROVIDERS.append("github")

if oauth is not None and settings.microsoft_client_id and settings.microsoft_client_secret:
    oauth.register(
        name="microsoft",
        client_id=settings.microsoft_client_id,
        client_secret=settings.microsoft_client_secret,
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        access_token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        api_base_url="https://graph.microsoft.com/v1.0/",
        client_kwargs={"scope": "User.Read"},
    )
    PROVIDERS.append("microsoft")


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def issue_tokens(db: Session, user: User, request: Request) -> TokenOut:
    raw = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=now() + timedelta(days=settings.refresh_token_days),
            device=(request.headers.get("user-agent") or "")[:255],
            ip_address=request.client.host if request.client else None,
        )
    )
    user.last_login = now()
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), refresh_token=raw)


@router.get("/providers")
def providers() -> dict:
    return {
        "google": "google" in PROVIDERS,
        "github": "github" in PROVIDERS,
        "microsoft": "microsoft" in PROVIDERS,
    }


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        phone=body.phone,
        password_hash=hash_password(body.password),
        role="USER",
    )
    db.add(user)
    db.add(AuditLog(actor_id=None, action="user.register", target=email))
    db.commit()
    tokens = issue_tokens(db, user, request)
    return AuthOut(**tokens.model_dump(), user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    generic = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if user is None or not user.password_hash:
        raise generic
    if user.locked_until and aware(user.locked_until) > now():
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again later")
    if not verify_password(body.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.max_failed_logins:
            user.locked_until = now() + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
        db.commit()
        raise generic
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")
    user.failed_attempts = 0
    user.locked_until = None
    tokens = issue_tokens(db, user, request)
    return AuthOut(**tokens.model_dump(), user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token)))
    if record is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if record.revoked:
        for item in db.scalars(select(RefreshToken).where(RefreshToken.user_id == record.user_id)):
            item.revoked = True
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token reuse detected. Please sign in again")
    if aware(record.expires_at) < now():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account unavailable")
    record.revoked = True
    db.commit()
    return issue_tokens(db, user, request)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token)))
    if record:
        record.revoked = True
        db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/sessions")
def sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
    ).all()
    return [
        {"id": r.id, "device": r.device, "ip_address": r.ip_address, "created_at": r.created_at, "expires_at": r.expires_at}
        for r in rows
        if aware(r.expires_at) > now()
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(RefreshToken, session_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    record.revoked = True
    db.commit()


def redirect_uri(provider: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/api/auth/{provider}/callback"


def find_or_link_user(db: Session, provider: str, provider_id: str, email: str, name: str, verified: bool) -> User:
    account = db.scalar(
        select(OAuthAccount).where(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == provider_id)
    )
    if account:
        return db.get(User, account.user_id)
    email = email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=name or email.split("@")[0], role="USER", email_verified=verified)
        db.add(user)
        db.flush()
        db.add(AuditLog(actor_id=None, action="user.register_oauth", target=email, detail={"provider": provider}))
    elif not verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provider email is not verified, cannot link account")
    db.add(OAuthAccount(user_id=user.id, provider=provider, provider_user_id=provider_id, email=email))
    db.commit()
    return user


def get_client(provider: str):
    if oauth is None or provider not in PROVIDERS:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OAuth login is unavailable in this environment")
    return getattr(oauth, provider)


def failure(reason: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/login?error={reason}")


@router.get("/{provider}")
async def oauth_start(provider: str, request: Request):
    if provider not in ("google", "github", "microsoft"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")
    client = get_client(provider)
    return await client.authorize_redirect(request, redirect_uri(provider))


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in ("google", "github", "microsoft"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")
    client = get_client(provider)
    try:
        token = await client.authorize_access_token(request)
        if provider == "google":
            info = token.get("userinfo") or {}
            provider_id, email = str(info.get("sub", "")), info.get("email", "")
            name, verified = info.get("name", ""), bool(info.get("email_verified"))
        elif provider == "github":
            profile = (await client.get("user", token=token)).json()
            emails = (await client.get("user/emails", token=token)).json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            provider_id, email = str(profile.get("id", "")), (primary or {}).get("email", "")
            name, verified = profile.get("name") or profile.get("login", ""), primary is not None
        else:
            profile = (await client.get("me", token=token)).json()
            provider_id = str(profile.get("id", ""))
            email = profile.get("mail") or profile.get("userPrincipalName") or ""
            name, verified = profile.get("displayName", ""), bool(profile.get("mail"))
    except (OAuthError, Exception):
        return failure("oauth_failed")
    if not provider_id or not email:
        return failure("no_email")
    try:
        user = find_or_link_user(db, provider, provider_id, email, name, verified)
    except HTTPException:
        return failure("unverified_email")
    if not user.is_active:
        return failure("disabled")
    tokens = issue_tokens(db, user, request)
    query = urlencode({"access_token": tokens.access_token, "refresh_token": tokens.refresh_token})
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/oauth/callback#{query}")
