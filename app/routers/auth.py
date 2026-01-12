from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from app.dependencies import get_db
from app.models import User
from app.config import settings

# --- Auth Config ---
# Validasi SECRET_KEY harus ada di .env untuk security (skip in development if empty)
SECRET_KEY = settings.SECRET_KEY or "dev-secret-key-change-in-production-DO-NOT-USE"
if not SECRET_KEY or SECRET_KEY.strip() == "":
    raise RuntimeError("FATAL: SECRET_KEY tidak ditemukan di .env. Konfigurasi .env terlebih dahulu!")

# Warn if using default key in production
if SECRET_KEY == "dev-secret-key-change-in-production-DO-NOT-USE":
    import logging
    logging.warning("⚠️  Using default SECRET_KEY! Set SECRET_KEY in .env for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Reduced dari 24 hours ke 1 hour untuk security 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "staf"

router = APIRouter(prefix="/auth", tags=["Auth"])

# --- Helpers ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Endpoints ---

@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, password_hash=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": new_user.role, "username": new_user.username}

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "username": user.username}

# Helper to be called from main.py
def create_initial_admin(db: Session):
    admin_user = "pelamampang"
    admin_pass = "pelamampang123"
    
    existing = db.query(User).filter(User.username == admin_user).first()
    if not existing:
        hashed = get_password_hash(admin_pass)
        new_admin = User(username=admin_user, password_hash=hashed, role="admin")
        db.add(new_admin)
        db.commit()

