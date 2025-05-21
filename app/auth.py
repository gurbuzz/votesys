import os, json, bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

# .env'den değişkenleri oku
load_dotenv()

# ------------ Ayarlar ---------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "change-this-secret")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MIN = 60

DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# ------------ Yardımcı IO -----------------------------------------------------
def _load_users() -> list[Dict]:
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return []

def _save_users(users: list[Dict]):
    USERS_FILE.write_text(json.dumps(users, indent=2))

# ------------ Parola işlemleri ------------------------------------------------
def _hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def _verify_pw(pw: str, pw_hash: str) -> bool:
    return bcrypt.checkpw(pw.encode(), pw_hash.encode())

# ------------ Kayıt & Kimlik --------------------------------------------------
def register(username: str, email: str, password: str, role: str = "user"):
    users = _load_users()
    if any(u["username"] == username for u in users):
        raise HTTPException(400, "Kullanıcı adı kullanımda")
    users.append({
        "username": username,
        "email": email,
        "password_hash": _hash_pw(password),
        "role": role,
        "email_confirmed": True   # aktif doğrulama yok; mock
    })
    _save_users(users)

def authenticate(username: str, password: str) -> Dict:
    for u in _load_users():
        if u["username"] == username and _verify_pw(password, u["password_hash"]):
            if not u["email_confirmed"]:
                raise HTTPException(403, "E-posta doğrulanmamış")
            return u
    raise HTTPException(400, "Hatalı giriş")

# ------------ JWT -------------------------------------------------------------
def create_access_token(data: dict) -> str:
    payload = data | {
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ------------ Role-based bağımlılıklar ---------------------------------------
def logged_user(u = Depends(get_current_user)):
    return u  # yalnızca login kontrolü

def admin_only(u = Depends(get_current_user)):
    if u.get("role") != "admin":
        raise HTTPException(403, "Admin yetkisi gerekli")
    return u
