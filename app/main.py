# votesys/app/main.py

import os
from datetime import timedelta
from typing import List

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Query,
    Depends,
    status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from .models import Poll
from .xml_utils import list_poll_ids, read_poll, write_poll
from .auth import (
    create_access_token,
    get_current_user,
    oauth2_scheme
)

# Uygulama başlat
app = FastAPI()

# Statik ve şablon dizinleri
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Sabit admin bilgisi (prod ortamında env değişkeni ile ayarla)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "secret")


# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Login formunu sunar.
    """
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Kullanıcıyı doğrular, JWT dönüyor.
    """
    if not (form_data.username == ADMIN_USER and form_data.password == ADMIN_PASS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı adı veya şifre hatalı"
        )
    token = create_access_token({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/logout")
async def logout():
    """
    Tarayıcı tarafında token silinecek.
    """
    return RedirectResponse("/", status_code=302)


# ─── UI PAGE ROUTES ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/poll.html", response_class=HTMLResponse)
async def serve_poll_page(request: Request, id: int = Query(..., description="Anket ID")):
    return templates.TemplateResponse("poll.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_list(request: Request):
    return templates.TemplateResponse("admin_list.html", {"request": request})

@app.get("/admin/create", response_class=HTMLResponse)
async def admin_create(request: Request):
    return templates.TemplateResponse("admin_create.html", {"request": request})


# ─── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.get("/api/polls", response_model=List[int])
async def get_poll_ids():
    return list_poll_ids()

@app.get("/api/polls/{poll_id}", response_model=Poll)
async def get_poll(poll_id: int):
    try:
        return read_poll(poll_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Anket bulunamadı")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class VoteRequest(BaseModel):
    option_id: int

@app.post("/api/polls/{poll_id}/vote", response_model=Poll)
async def vote(poll_id: int, vote: VoteRequest):
    try:
        poll = read_poll(poll_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Anket bulunamadı")
    for opt in poll.options:
        if opt.id == vote.option_id:
            opt.votes += 1
            write_poll(poll)
            return poll
    raise HTTPException(status_code=400, detail="Seçenek bulunamadı")

@app.post(
    "/api/polls",
    response_model=Poll,
    status_code=201,
    dependencies=[Depends(get_current_user)]
)
async def create_poll(poll: Poll):
    if poll.id in list_poll_ids():
        raise HTTPException(status_code=400, detail="Bu ID zaten mevcut")
    write_poll(poll)
    return poll
