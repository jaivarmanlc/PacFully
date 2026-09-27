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
from typing import Optional

import bcrypt as _bcrypt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ────────────────────────────────────────────────────
SECRET_KEY     = os.getenv("SECRET_KEY", "pacfully-super-secret-key-change-in-prod-2026")
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


# ── Default users seeded on first startup ─────────────────────

DEFAULT_USERS = [
    {"full_name": "Admin",        "email": "admin@pacfully.in",  "password": "admin123",  "role": "Administrator"},
    {"full_name": "Jaya Varma",   "email": "jaya@pacfully.in",   "password": "jaya123",   "role": "Administrator"},
    {"full_name": "Arjun Kapoor", "email": "arjun@pacfully.in",  "password": "arjun123",  "role": "Estimator"    },
    {"full_name": "Priya Menon",  "email": "priya@pacfully.in",  "password": "priya123",  "role": "Viewer"       },
]

def seed_users(db: Session):
    """Insert default users if the users table is empty."""
    if db.query(User).count() == 0:
        for u in DEFAULT_USERS:
            db.add(User(
                full_name       = u["full_name"],
                email           = u["email"],
                hashed_password = hash_password(u["password"]),
                role            = u["role"],
                is_active       = True,
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
    password:  str
    role:      str = "Estimator"

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
