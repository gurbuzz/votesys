# 1. Hafif ve Python 3.11 içeren resmi image
FROM python:3.11-slim

# 2. Çalışma dizinini ayarla
WORKDIR /app

# 3. Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Uygulama kodunu kopyala
COPY . .

# 5. Data klasörünü oluştur (XML dosyaları için)
RUN mkdir -p app/data

# 6. Uvicorn'un kullandığı portu aç
EXPOSE 8000

# 7. Container ayağa kalkınca çalışacak komut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
