"""
Kullanıcı yönetimi + JWT yardımcıları
------------------------------------
* JSON dosyasında kullanıcılar (username, email, pw_hash, role)
* .env'deki ADMIN_USER / ADMIN_PASSWORD her start'ta senkron
* bcrypt ile güvenli parola
* /login için OAuth2PasswordBearer
"""

import os, json, bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

# ───────────────────────────── Ayarlar ────────────────────────────────────────
load_dotenv()

SECRET_KEY       = os.getenv("JWT_SECRET", "change-this-secret")
ALGORITHM        = "HS256"
TOKEN_EXPIRE_MIN = 60

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "secret")

DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# ───────────────────────────── Yardımcı IO ────────────────────────────────────
def _load_users() -> List[Dict]:
    return json.loads(USERS_FILE.read_text()) if USERS_FILE.exists() else []

def _save_users(users: List[Dict]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2))

# ─────────────────────── Parola hash & doğrulama ─────────────────────────────
def _hash_pw(password: str) -> str:
    """plaintext → bcrypt hash (base64 str)"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_pw(password: str, pw_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), pw_hash.encode())

# ─────────────────────── Admin hesabını senkronize et ────────────────────────
def _ensure_admin() -> None:
    users = _load_users()
    admin = next((u for u in users if u["username"] == ADMIN_USER), None)

    if admin:
        updated = False
        # Rol 'admin' değilse düzelt
        if admin.get("role") != "admin":
            admin["role"] = "admin"
            updated = True
        # Parola değiştiyse hash güncelle
        if not _verify_pw(ADMIN_PASS, admin["password_hash"]):
            admin["password_hash"] = _hash_pw(ADMIN_PASS)
            updated = True
        if updated:
            _save_users(users)
    else:
        # Admin yoksa oluştur
        users.append({
            "username": ADMIN_USER,
            "email":   f"{ADMIN_USER}@example.com",
            "password_hash": _hash_pw(ADMIN_PASS),
            "role":    "admin",
            "email_confirmed": True
        })
        _save_users(users)

_ensure_admin()  # modül import edilir edilmez çalışır

# ─────────────────────── Kullanıcı işlemleri ─────────────────────────────────
def register(username: str, email: str, password: str, role: str = "user") -> None:
    role = role.lower()
    users = _load_users()
    if any(u["username"] == username for u in users):
        raise HTTPException(400, "Kullanıcı adı kullanımda")
    users.append({
        "username": username,
        "email": email,
        "password_hash": _hash_pw(password),
        "role": role,
        "email_confirmed": True
    })
    _save_users(users)

def authenticate(username: str, password: str) -> Dict:
    user = next((u for u in _load_users() if u["username"] == username), None)
    if not user or not _verify_pw(password, user["password_hash"]):
        raise HTTPException(400, "Hatalı giriş")
    if not user["email_confirmed"]:
        raise HTTPException(403, "E-posta doğrulanmamış")
    return user

# ───────────────────────────── JWT yardımcıları ───────────────────────────────
def create_access_token(payload: dict) -> str:
    payload = {**payload, "role": str(payload.get("role", "user")).lower()}
    payload["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ─────────────────────── FastAPI bağımlılıkları ──────────────────────────────
def logged_user(user = Depends(get_current_user)):
    return user  # yalnızca “girişli” kontrolü

def admin_only(user = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin yetkisi gerekli")
    return user

# ─────────────────────── Yöneticiye özel yardımcılar ─────────────────────────
def list_users() -> List[Dict]:
    """Kullanıcıları (hash hariç) döndür."""    
    return [
        {"username": u["username"], "email": u["email"], "role": u["role"]}
        for u in _load_users()
    ]

def delete_user(username: str) -> None:
    users = _load_users()
    if not any(u["username"] == username for u in users):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    _save_users([u for u in users if u["username"] != username])
    