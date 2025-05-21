# votesys/app/main.py

import os
import json
import traceback
from pathlib import Path
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
from . import xml_utils
from .auth import (
    register,
    authenticate,
    create_access_token,
    logged_user,
    admin_only,
    get_current_user
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─── REGISTER / LOGIN / LOGOUT ────────────────────────────────────────────────

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register")
async def api_register(data: RegisterRequest):
    try:
        register(data.username, data.email, data.password, role="user")
        return {"msg": "Kayıt başarılı (e-posta doğrulandı sayıldı)"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Kayıt başarısız: " + str(e))

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def api_login(form: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate(form.username, form.password)
        token = create_access_token({"sub": user["username"], "role": user["role"]})
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Giriş işleminde hata: " + str(e))

@app.get("/logout")
async def logout():
    return RedirectResponse("/", status_code=302)


# ─── UI ROUTES ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/poll.html", response_class=HTMLResponse)
async def poll_page(request: Request, id: int = Query(..., description="Anket ID")):
    return templates.TemplateResponse("poll.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin_list.html", {"request": request})

@app.get("/admin/create", response_class=HTMLResponse)
async def admin_create_page(request: Request):
    return templates.TemplateResponse("admin_create.html", {"request": request})


# ─── API: POLLS ───────────────────────────────────────────────────────────────

@app.get("/api/polls", response_model=List[int])
async def api_poll_ids():
    try:
        return xml_utils.list_poll_ids()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Anket listesi alınamadı: " + str(e))

@app.get("/api/polls/{poll_id}", response_model=Poll)
async def api_get_poll(poll_id: int):
    try:
        return xml_utils.read_poll(poll_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Anket bulunamadı")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Anket okunamadı: " + str(e))


class VoteRequest(BaseModel):
    option_id: int

@app.post(
    "/api/polls/{poll_id}/vote",
    response_model=Poll,
    dependencies=[Depends(logged_user)]
)
async def api_vote(
    poll_id: int,
    vote: VoteRequest,
    user = Depends(get_current_user)
):
    try:
        poll = xml_utils.read_poll(poll_id)

        # 1) Sahibi kendi anketine oy veremez
        if poll.owner == user["sub"]:
            raise HTTPException(status_code=403, detail="Kendi anketinize oy veremezsiniz")

        # 2) Tekrar oy kontrolü
        voter_file = Path(f"{xml_utils._poll_filepath(poll_id)[:-4]}_voters.json")
        voters = json.loads(voter_file.read_text()) if voter_file.exists() else []
        if user["sub"] in voters:
            raise HTTPException(status_code=403, detail="Bu ankete zaten oy verdiniz")

        # 3) Oy ekle
        for opt in poll.options:
            if opt.id == vote.option_id:
                opt.votes += 1
                xml_utils.write_poll(poll)
                voters.append(user["sub"])
                voter_file.write_text(json.dumps(voters))
                return poll

        raise HTTPException(status_code=400, detail="Seçenek bulunamadı")

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Oy verilemedi: " + str(e))


@app.post(
    "/api/polls",
    response_model=Poll,
    status_code=201,
    dependencies=[Depends(logged_user)]
)
async def api_create_poll(
    poll: Poll,
    user = Depends(get_current_user)
):
    try:
        if poll.id in xml_utils.list_poll_ids():
            raise HTTPException(status_code=400, detail="Bu ID zaten mevcut")
        poll.owner = user["sub"]
        xml_utils.write_poll(poll)
        return poll

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Anket oluşturulamadı: " + str(e))


@app.delete(
    "/api/polls/{poll_id}",
    dependencies=[Depends(admin_only)]
)
async def api_delete_poll(poll_id: int):
    try:
        # XML dosyasını sil
        path = Path(xml_utils._poll_filepath(poll_id))
        if path.exists():
            path.unlink()
        # Oy kullanmışları silelim
        voter_file = path.with_name(path.stem + "_voters.json")
        if voter_file.exists():
            voter_file.unlink()
        return {"msg": "Anket silindi"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Silme işlemi başarısız: " + str(e))
