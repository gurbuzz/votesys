# votesys/app/main.py
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

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ───────── Register / Login / Logout ─────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def api_register(payload: RegisterRequest):
    register(payload.username, payload.email, payload.password)
    return {"msg": "Kayıt başarılı!"}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
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
    return RedirectResponse("/", status_code=302)

# ──────────── UI sayfaları ────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/poll.html", response_class=HTMLResponse)
async def poll_page(request: Request, id: int = Query(..., description="Anket ID")):
    return templates.TemplateResponse("poll.html", {"request": request})

# ★★★ HTML sayfalarda token başlık gönderilemez, o yüzden kontrolü JS’de yapacağız.
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin_list.html", {"request": request})

@app.get("/poll/create", response_class=HTMLResponse)
async def poll_create_page(request: Request):
    return templates.TemplateResponse("admin_create.html", {"request": request})

# ───────── Admin API’leri ─────────
@app.get("/api/users", dependencies=[Depends(admin_only)])
async def api_list_users():
    return list_users()

@app.delete("/api/users/{username}", dependencies=[Depends(admin_only)])
async def api_delete_user(username: str):
    delete_user(username)
    return {"msg": "Kullanıcı silindi"}

# ───────── Poll API’leri (token korumalı) ─────────
@app.get("/api/polls", response_model=List[int])
async def api_poll_ids():
    return xml_utils.list_poll_ids()

@app.get("/api/polls/{poll_id}", response_model=Poll)
async def api_get_poll(poll_id: int):
    return xml_utils.read_poll(poll_id)

class VoteRequest(BaseModel):
    option_id: int

@app.post("/api/polls/{poll_id}/vote", response_model=Poll, dependencies=[Depends(logged_user)])
async def api_vote(poll_id: int, vote: VoteRequest, user=Depends(get_current_user)):
    poll = xml_utils.read_poll(poll_id)
    if poll.owner == user["sub"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kendi anketinize oy veremezsiniz")
    voters_path = Path(f"{xml_utils._poll_filepath(poll_id)[:-4]}_voters.json")
    voters = json.loads(voters_path.read_text()) if voters_path.exists() else []
    if user["sub"] in voters:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu ankete zaten oy verdiniz")
    for opt in poll.options:
        if opt.id == vote.option_id:
            opt.votes += 1
            xml_utils.write_poll(poll)
            voters.append(user["sub"])
            voters_path.write_text(json.dumps(voters))
            return poll
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seçenek bulunamadı")

@app.post("/api/polls", response_model=Poll, status_code=201, dependencies=[Depends(logged_user)])
async def api_create_poll(poll: Poll, user=Depends(get_current_user)):
    if poll.id in xml_utils.list_poll_ids():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu ID zaten mevcut")
    poll.owner = user["sub"]
    xml_utils.write_poll(poll)
    return poll

@app.delete("/api/polls/{poll_id}", dependencies=[Depends(admin_only)])
async def api_delete_poll(poll_id: int):
    path = Path(xml_utils._poll_filepath(poll_id))
    if path.exists():
        path.unlink()
    Path(f"{path.with_suffix('').name}_voters.json").unlink(missing_ok=True)
    return {"msg": "Anket silindi"}
