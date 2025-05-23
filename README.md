# XML Tabanlı Online Oylama Sistemi (VoteSys)

Bu proje, anketlerin ve oyların tamamen XML dosyalarında saklandığı, FastAPI tabanlı bir RESTful web servisi ve basit bir web arayüzü sunar.

---

## 🚀 Özellikler

- **Yönetici**:  
  - Anket oluşturma (`/poll/create`)  
  - Anketleri ve kullanıcıları listeleme ve silme (`/admin`)  
- **Kayıtlı Kullanıcı**:  
  - Anket oluşturma  
  - Ankete oy verme (bir kez)  
- **Ziyaretçi**:  
  - Anket listesini görüntüleme (`/`)  
  - Anket detaylarını ve sonuçları görme (`/poll.html?id={id}`)  
- **XML Tabanlı**:  
  - `app/data/poll_{id}.xml` dosyalarında saklama  
  - `app/poll.xsd` ile XSD doğrulama  
- **Güvenlik**:  
  - JWT ile kimlik doğrulama (login/register)  
  - Kullanıcı rolleri: `admin` ve `user`  
- **Test & CI**:  
  - `pytest` + `httpx` ile otomatik API ve XML testleri  
- **Docker & Live-Reload**:  
  - `docker-compose` ile “tek komut” ayağa kaldırma  
  - Geliştirme için bind-mount ve Uvicorn `--reload`

---

## 🛠️ Teknolojiler

- **Backend**: Python 3.11, FastAPI  
- **XML**: lxml, pydantic-xml, XSD  
- **Auth**: python-jose (JWT), bcrypt  
- **Frontend**: Jinja2 + Bootstrap 5 (vendor), Vanilla JS  
- **Test**: pytest, httpx  
- **Container**: Docker, docker-compose  
- **Ortam**: `.env` (JWT_SECRET, ADMIN_USER, ADMIN_PASSWORD)


---

## ⚙️ Kurulum
1. Repo’yu klonlayın ve proje dizinine girin:
   ```bash
   git clone https://github.com/kullanici/votesys.git
   cd votesys


Ortam değişkenleri:

cp .env.example .env
# .env içinde JWT_SECRET, ADMIN_USER, ADMIN_PASSWORD değerlerini düzenleyin


Python sanal ortam:

python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

▶️ Çalıştırma (Geliştirme)

uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000

   Uygulamaya: http://127.0.0.1:8001


🐳 Docker ile Çalıştırma
docker-compose up --build

   Uygulamaya: http://127.0.0.1:8000



🔑 Ortam Değişkenleri (.env)
JWT_SECRET=change-this-secret
ADMIN_USER=admin
ADMIN_PASSWORD=secret


📄 API Uç Noktaları
Genel (herkes)

    GET /api/polls → Anket ID listesi

    GET /api/polls/{id} → Tek anket (JSON)

Auth Gerektiren

    POST /login → Login (JWT elde etme)

    POST /register → Kayıt (user rolü)

    POST /api/polls/{id}/vote → Oy verme (her kullanıcı bir kez)

    POST /api/polls → Anket oluşturma (girişli user veya admin)

    GET /poll/create → Anket oluşturma formu (girişli)

Sadece Admin

    GET /api/users → Kullanıcı listesi

    DELETE /api/users/{username} → Kullanıcı silme

    GET /admin → Yönetici paneli

    DELETE /api/polls/{id} → Anket silme


📝 Lisans

MIT License © 2025



