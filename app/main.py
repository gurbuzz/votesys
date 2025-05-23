# votesys/app/main.py
# Online Oylama Sistemi API'sinin ana dosyası

# Gerekli kütüphaneleri içe aktar
import json, traceback
from pathlib import Path
from typing import List

from fastapi import (
    FastAPI, Request, HTTPException, Query,
    Depends, status, Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .models import Poll
from . import xml_utils
from .auth import (
    register, authenticate, create_access_token,
    logged_user, admin_only, get_current_user,
    list_users, delete_user
)

# FastAPI uygulamasını başlat
app = FastAPI()

# Statik dosyalar ve şablon dizinleri
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ───────── Kayıt ve Kimlik Doğrulama ─────────
class RegisterRequest(BaseModel):
    # Kayıt formundan gelecek verinin modeli
    username: str
    email: str
    password: str

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    # Kayıt sayfasını göster
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def api_register(payload: RegisterRequest):
    # Yeni kullanıcı kaydı işlemi
    register(payload.username, payload.email, payload.password)
    return {"msg": "Kayıt başarılı!"}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Giriş sayfasını göster
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    # Kullanıcı doğrulama ve token oluşturma
    user   = authenticate(username, password)
    token  = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "username":     user["username"],
        "role":         user["role"]
    }

@app.get("/logout")
async def logout():
    # Çıkış işlemi, ana sayfaya yönlendirir
    return RedirectResponse("/", status_code=302)

# ─────────── UI Sayfaları ───────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Anasayfa şablonunu yükle
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/poll.html", response_class=HTMLResponse)
async def poll_page(request: Request, id: int = Query(..., description="Anket ID")):
    # Anket sayfasını göster, JS ile veriler alınacak
    return templates.TemplateResponse("poll.html", {"request": request})

# ★★★ HTML sayfalarda token başlık gönderilemez, o yüzden kontrolü JS’de yapacağız.
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    # Yönetici paneli için kullanıcı listesi sayfası
    return templates.TemplateResponse("admin_list.html", {"request": request})

@app.get("/poll/create", response_class=HTMLResponse)
async def poll_create_page(request: Request):
    # Yeni anket oluşturma sayfası
    return templates.TemplateResponse("admin_create.html", {"request": request})

# ───────── Admin API’leri ─────────
@app.get("/api/users", dependencies=[Depends(admin_only)])
async def api_list_users():
    # Tüm kullanıcıları listele (sadece admin)
    return list_users()

@app.delete("/api/users/{username}", dependencies=[Depends(admin_only)])
async def api_delete_user(username: str):
    # Belirli bir kullanıcıyı sil (sadece admin)
    delete_user(username)
    return {"msg": "Kullanıcı silindi"}

# ───────── Poll API’leri (Token Korumalı) ─────────
@app.get("/api/polls", response_model=List[int])
async def api_poll_ids():
    # Mevcut anket ID’lerini getir
    return xml_utils.list_poll_ids()

@app.get("/api/polls/{poll_id}", response_model=Poll)
async def api_get_poll(poll_id: int):
    # Tek bir anketin detayını oku
    return xml_utils.read_poll(poll_id)

class VoteRequest(BaseModel):
    # Oy verme isteği modeli
    option_id: int

@app.post("/api/polls/{poll_id}/vote", response_model=Poll, dependencies=[Depends(logged_user)])
async def api_vote(poll_id: int, vote: VoteRequest, user=Depends(get_current_user)):
    # Anket sahibinin kendi anketine oy vermesini engelle
    poll = xml_utils.read_poll(poll_id)
    if poll.owner == user["sub"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kendi anketinize oy veremezsiniz")
    # Daha önce oy verildiyse engelle
    voters_path = Path(f"{xml_utils._poll_filepath(poll_id)[:-4]}_voters.json")
    voters = json.loads(voters_path.read_text()) if voters_path.exists() else []
    if user["sub"] in voters:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu ankete zaten oy verdiniz")
    # Seçeneği bul ve oy sayısını artır, sonra kaydet
    for opt in poll.options:
        if opt.id == vote.option_id:
            opt.votes += 1
            xml_utils.write_poll(poll)
            voters.append(user["sub"])
            voters_path.write_text(json.dumps(voters))
            return poll
    # Geçersiz seçenek isteği
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seçenek bulunamadı")

@app.post("/api/polls", response_model=Poll, status_code=201, dependencies=[Depends(logged_user)])
async def api_create_poll(poll: Poll, user=Depends(get_current_user)):
    # Aynı ID ile yeni anket oluşturmayı engelle
    if poll.id in xml_utils.list_poll_ids():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu ID zaten mevcut")
    # Anket sahibini ayarla ve XML dosyasını oluştur
    poll.owner = user["sub"]
    xml_utils.write_poll(poll)
    return poll

@app.delete("/api/polls/{poll_id}", dependencies=[Depends(admin_only)])
async def api_delete_poll(poll_id: int):
    # Anketi ve ilgili voter kaydını sil (sadece admin)
    path = Path(xml_utils._poll_filepath(poll_id))
    if path.exists():
        path.unlink()
    Path(f"{path.with_suffix('').name}_voters.json").unlink(missing_ok=True)
    return {"msg": "Anket silindi"}
