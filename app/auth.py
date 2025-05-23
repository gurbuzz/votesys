"""
Kullanıcı yönetimi + JWT yardımcıları
------------------------------------
* JSON dosyasında kullanıcılar (username, email, pw_hash, role)
* .env’deki ADMIN_USER / ADMIN_PASSWORD her start’ta senkron
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

# ————————— Ayarlar —————————
# .env’den anahtarları al, JWT ve admin bilgilerini tanımla
load_dotenv()
SECRET_KEY       = os.getenv("JWT_SECRET", "change-this-secret")
ALGORITHM        = "HS256"
TOKEN_EXPIRE_MIN = 60
ADMIN_USER       = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS       = os.getenv("ADMIN_PASSWORD", "secret")
# Kullanıcı verisi klasörü ve dosyası
DATA_DIR   = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"
DATA_DIR.mkdir(exist_ok=True)
# OAuth2 token mekanizması için URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ————— Yardımcı IO İşlemleri —————
def _load_users() -> List[Dict]:
    """users.json varsa oku, yoksa boş liste döndür."""
    return json.loads(USERS_FILE.read_text()) if USERS_FILE.exists() else []

def _save_users(users: List[Dict]) -> None:
    """Kullanıcı listesi JSON olarak kaydet."""
    USERS_FILE.write_text(json.dumps(users, indent=2))


# ————— Parola Hash & Doğrulama —————
def _hash_pw(password: str) -> str:
    """Düz metin şifreyi bcrypt ile hash’le."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_pw(password: str, pw_hash: str) -> bool:
    """Girilen şifre ile hash’i karşılaştır."""
    return bcrypt.checkpw(password.encode(), pw_hash.encode())


# ————— Admin Hesabı Senkronizasyonu —————
def _ensure_admin() -> None:
    """
    .env’deki admin bilgisiyle users.json’u kontrol et.
    Yoksa ekle, varsa rol ve şifre hash’ini güncelle.
    """
    users = _load_users()
    admin = next((u for u in users if u["username"] == ADMIN_USER), None)

    if admin:
        updated = False
        if admin.get("role") != "admin":
            admin["role"] = "admin"; updated = True
        if not _verify_pw(ADMIN_PASS, admin["password_hash"]):
            admin["password_hash"] = _hash_pw(ADMIN_PASS); updated = True
        if updated:
            _save_users(users)
    else:
        users.append({
            "username":       ADMIN_USER,
            "email":          f"{ADMIN_USER}@example.com",
            "password_hash":  _hash_pw(ADMIN_PASS),
            "role":           "admin",
            "email_confirmed": True
        })
        _save_users(users)

# Modül yüklendiğinde admin kontrolünü yap
_ensure_admin()


# ————— Kullanıcı İşlemleri —————
def register(username: str, email: str, password: str, role: str = "user") -> None:
    """Yeni kullanıcı oluşturur; aynı isimde varsa hata fırlatır."""
    users = _load_users()
    if any(u["username"] == username for u in users):
        raise HTTPException(400, "Kullanıcı adı kullanımda")
    users.append({
        "username":      username,
        "email":         email,
        "password_hash": _hash_pw(password),
        "role":          role.lower(),
        "email_confirmed": True
    })
    _save_users(users)

def authenticate(username: str, password: str) -> Dict:
    """
    Kullanıcı adı + şifre kontrolü yapar.
    Başarısızsa veya e-posta onaylı değilse HTTPException fırlatır.
    """
    user = next((u for u in _load_users() if u["username"] == username), None)
    if not user or not _verify_pw(password, user["password_hash"]):
        raise HTTPException(400, "Hatalı giriş")
    if not user["email_confirmed"]:
        raise HTTPException(403, "E-posta doğrulanmamış")
    return user


# ————— JWT Oluşturma & Kullanıcı Getirme —————
def create_access_token(payload: dict) -> str:
    """Payload’a süre sonu ekleyip JWT üretir."""
    payload = {**payload, "role": str(payload.get("role", "user")).lower()}
    payload["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Gelen token’ı doğrular, decode eder.
    Hatalıysa 401 döner.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ————— FastAPI Bağımlılıkları —————
def logged_user(user = Depends(get_current_user)):
    """Giriş yapmış kullanıcıyı sağlar (sadece kontrol)."""
    return user

def admin_only(user = Depends(get_current_user)):
    """Yalnızca admin rolündeyse geçer; değilse 403 döner."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin yetkisi gerekli")
    return user


# ————— Yöneticiye Özel Yardımcılar —————
def list_users() -> List[Dict]:
    """Tüm kullanıcıları şifre hariç listele."""
    return [
        {"username": u["username"], "email": u["email"], "role": u["role"]}
        for u in _load_users()
    ]

def delete_user(username: str) -> None:
    """Verilen kullanıcıyı sil; yoksa 404 döner."""
    users = _load_users()
    if not any(u["username"] == username for u in users):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    _save_users([u for u in users if u["username"] != username])
