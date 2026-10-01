"""
Authentication module for Pacfully.
- Password hashing with bcrypt (direct, no passlib)
- JWT access tokens via python-jose
- /api/auth/login  — returns token + user info
- /api/auth/me     — returns current user from token
- /api/auth/users  — list / create / delete users (admin only)
"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import bcrypt as _bcrypt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise RuntimeError("SECRET_KEY must be configured in production.")
    secret_path = Path(__file__).resolve().parent.parent / "data" / ".development-secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        secret_path.touch(exist_ok=False)
        SECRET_KEY = secrets.token_urlsafe(32)
        secret_path.write_text(SECRET_KEY, encoding="utf-8")
    except FileExistsError:
        SECRET_KEY = secret_path.read_text(encoding="utf-8").strip()

ALGORITHM      = "HS256"
TOKEN_EXPIRE_H = 24
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/auth", tags=["auth"])


# ── Password helpers ──────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────

def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_H)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── FastAPI dependencies ──────────────────────────────────────

def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    """Validates JWT and returns the User row. Raises 401 on failure."""
    cred_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise cred_err
    except JWTError:
        raise cred_err

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise cred_err
    return user

def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != "Administrator":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return current


# ── Initial administrator bootstrap ──────────────────────────

INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
INITIAL_ADMIN_NAME = os.getenv("INITIAL_ADMIN_NAME", "Pacfully Administrator").strip()

def seed_users(db: Session):
    """Create the configured administrator only when the users table is empty."""
    if db.query(User).first():
        return
    if not INITIAL_ADMIN_EMAIL or not INITIAL_ADMIN_PASSWORD:
        if ENVIRONMENT == "production":
            raise RuntimeError(
                "Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD before first production startup."
            )
        return
    if len(INITIAL_ADMIN_PASSWORD) < 12:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must be at least 12 characters.")

    db.add(User(
        full_name=INITIAL_ADMIN_NAME or "Pacfully Administrator",
        email=INITIAL_ADMIN_EMAIL,
        hashed_password=hash_password(INITIAL_ADMIN_PASSWORD),
        role="Administrator",
        is_active=True,
    ))
    db.commit()


# ── Pydantic schemas ──────────────────────────────────────────

class LoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    full_name:    str
    email:        str
    role:         str

class UserOut(BaseModel):
    id:         int
    full_name:  str
    email:      str
    role:       str
    is_active:  bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    full_name: str
    email:     str
    password:  str = Field(min_length=12, max_length=72)
    role:      Literal["Administrator", "Estimator", "Viewer"] = "Estimator"

class UserRoleUpdate(BaseModel):
    role: Literal["Administrator", "Estimator", "Viewer"]

class PasswordChange(BaseModel):
    current_password: str
    new_password:     str

class GoogleLoginRequest(BaseModel):
    credential: str


# ── Routes ────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    POST /api/auth/login
    Body (form-encoded): username=<email>&password=<password>
    Returns JWT token + user details.
    """
    user = db.query(User).filter(
        User.email     == form.username.strip().lower(),
        User.is_active == True,
    ).first()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Record last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token({"sub": str(user.id), "email": user.email, "role": user.role})

    return LoginResponse(
        access_token = token,
        user_id      = user.id,
        full_name    = user.full_name,
        email        = user.email,
        role         = user.role,
    )


@router.post("/google", response_model=LoginResponse)
def login_with_google(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token, upsert the user by email, and issue an app JWT."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")

    try:
        claims = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in credential")

    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email address is not verified")

    email = claims["email"].strip().lower()
    full_name = claims.get("name") or email.split("@", 1)[0]
    user = db.query(User).filter(User.email == email).first()

    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    if user is None:
        user = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            role="Estimator",
            is_active=True,
        )
        db.add(user)
    else:
        user.full_name = full_name

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = create_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    """Returns the currently authenticated user's profile."""
    return current


@router.get("/users", response_model=list[UserOut])
def list_users(
    current: User = Depends(require_admin),
    db: Session   = Depends(get_db),
):
    return db.query(User).order_by(User.full_name).all()


@router.post("/users", status_code=201, response_model=UserOut)
def create_user(
    body: UserCreate,
    current: User = Depends(require_admin),
    db: Session   = Depends(get_db),
):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")
    u = User(
        full_name       = body.full_name,
        email           = email,
        hashed_password = hash_password(body.password),
        role            = body.role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current: User = Depends(require_admin),
    db: Session   = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(400, "Cannot deactivate your own account")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.is_active = False
    db.commit()
    return {"message": f"{u.full_name} deactivated"}


@router.put("/users/{user_id}", response_model=UserOut)
def update_user_role(
    user_id: int,
    body: UserRoleUpdate,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(400, "Cannot change your own role")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    current: User = Depends(get_current_user),
    db: Session   = Depends(get_db),
):
    if not verify_password(body.current_password, current.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    current.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
