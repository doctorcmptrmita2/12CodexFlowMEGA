# CF-X EasyPanel Deployment Rehberi

Bu rehber, CF-X (CodexFlow) v3 platformunu EasyPanel'de deploy etmek için adım adım talimatlar içerir.

## 📋 İçindekiler

1. [Ön Hazırlık](#ön-hazırlık)
2. [EasyPanel Proje Oluşturma](#easypanel-proje-oluşturma)
3. [Supabase Kurulumu](#supabase-kurulumu)
4. [Servislerin Oluşturulması](#servislerin-oluşturulması)
   - [1. LiteLLM Servisi](#1-litellm-servisi)
   - [2. CF-X Router Servisi](#2-cf-x-router-servisi)
   - [3. Dashboard Servisi](#3-dashboard-servisi)
5. [Domain ve Routing Yapılandırması](#domain-ve-routing-yapılandırması)
6. [Environment Variables](#environment-variables)
7. [Health Check ve Monitoring](#health-check-ve-monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Ön Hazırlık

### Gereksinimler

- ✅ **EasyPanel hesabı** (Container hosting için)
- ✅ **Supabase hesabı** (Database için - ücretsiz tier yeterli)
  - ⚠️ **ÖNEMLİ:** Supabase, EasyPanel'den **BAĞIMSIZ** bir servistir
  - Supabase projesini [supabase.com](https://app.supabase.com) web sitesinde oluşturursunuz
  - EasyPanel'de Supabase projesi oluşturulmaz!
- ✅ Domain adı (opsiyonel, IP ile de çalışır)
- ✅ **Provider API Keys:**
  - **Seçenek 1 (Önerilen):** OpenRouter API Key (tek key ile tüm modellere erişim)
  - **Seçenek 2:** Direkt provider keys (Anthropic, DeepSeek, OpenAI ayrı ayrı)

### Servis Mimarisi

CF-X platformu **2 farklı platform** kullanır:

1. **EasyPanel** → Container hosting (Router, Dashboard, LiteLLM servisleri burada çalışır)
2. **Supabase** → Database & Auth servisi (ayrı bir platform, web dashboard üzerinden yönetilir)

### Hazırlanacak Dosyalar

Projenizi EasyPanel'e yüklemek için iki yöntem var:

**Yöntem 1: Git Repository (Önerilen)**
- Projeyi GitHub/GitLab'a push edin
- EasyPanel'de Git repository'den deploy edin

**Yöntem 2: Manual Upload**
- Proje dosyalarını zip olarak hazırlayın
- EasyPanel'de manual upload yapın

---

## EasyPanel Proje Oluşturma

### Adım 1: EasyPanel'e Giriş

1. EasyPanel dashboard'una giriş yapın
2. Sol menüden **"Projects"** sekmesine tıklayın
3. **"New Project"** butonuna tıklayın

### Adım 2: Proje Bilgileri

- **Project Name:** `cfx-platform` (veya istediğiniz isim)
  - ⚠️ **NOT:** Bu isim sadece EasyPanel içindir, Supabase ile karıştırmayın!
- **Description:** `CF-X AI Orchestration Platform`
- **Save** butonuna tıklayın

---

## Supabase Kurulumu (Otomatik)

⚠️ **ÖNEMLİ:** Supabase, EasyPanel'den **BAĞIMSIZ** bir servistir. Supabase projesini EasyPanel'de değil, **Supabase'in kendi web dashboard'unda** oluşturmanız gerekir.

### Yöntem 1: Otomatik Setup (Önerilen) 🚀

Supabase schema'sını tek komutla otomatik deploy edebilirsiniz:

#### Adım 1: Supabase Projesi Oluşturma (Supabase Dashboard'unda)

**📍 Bu adım EasyPanel'de DEĞİL, Supabase web sitesinde yapılır:**

1. Tarayıcınızda [Supabase Dashboard](https://app.supabase.com) açın
2. **New Project** butonuna tıklayın
3. Proje bilgilerini doldurun:
   - **Name:** `cfx-database` (veya istediğiniz isim - EasyPanel projesinden bağımsız)
   - **Database Password:** Güçlü bir şifre oluşturun (kaydedin!)
   - **Region:** Size en yakın region seçin
4. **Create new project** butonuna tıklayın (2-3 dakika sürebilir)

**💡 Not:** Bu Supabase'in kendi servisi, EasyPanel ile ilgili değil. Supabase ücretsiz tier'da kullanılabilir.

#### Adım 2: Schema'yı Otomatik Deploy Etme

**Seçenek A: Supabase CLI ile (Opsiyonel - Gelişmiş Kullanıcılar İçin)**

**Supabase CLI Nedir?**
- Supabase CLI, Supabase projelerini komut satırından yönetmenizi sağlayan bir araçtır
- Schema'ları, migration'ları ve diğer ayarları terminal'den deploy edebilirsiniz
- **Opsiyonel:** Eğer CLI kullanmak istemiyorsanız, **Seçenek B (SQL Editor)** çok daha basittir ve önerilir!

**⚠️ ÖNEMLİ:** Supabase CLI artık `npm install -g` ile kurulamıyor! Windows için farklı yöntemler gerekiyor.

**Windows'ta Supabase CLI Kurulumu:**

**Yöntem 1: Scoop (Önerilen - Windows için)**

```powershell
# 1. Scoop yüklü değilse önce Scoop'u kurun:
# PowerShell'i Administrator olarak açın ve çalıştırın:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# 2. Supabase CLI'yi kurun:
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# 3. Kontrol:
supabase --version
```

**Yöntem 2: Chocolatey (Alternatif)**

```powershell
# 1. Chocolatey yüklü değilse önce kurun (Administrator PowerShell):
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Supabase CLI'yi kurun:
choco install supabase

# 3. Kontrol:
supabase --version
```

**Yöntem 3: npx ile (npm yüklüyse, geçici kullanım)**

```powershell
# Her seferinde npx ile çalıştırın (global kurulum yok):
npx supabase@latest login
npx supabase@latest db push --db-url "postgresql://..."
```

**CLI Kullanımı (Kurulum sonrası):**

```powershell
# 1. Supabase'e login olun (tarayıcı açılacak)
supabase login

# 2. Schema'yı deploy edin
cd C:\wamp64\www\12CodexFlowMEGA\infra\supabase
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"
```

**💡 ÖNERİ:** CLI kurulumu karmaşık olabilir. **Seçenek B (SQL Editor)** çok daha basit ve hiçbir şey kurmanıza gerek yok - sadece tarayıcıdan yapılır!

**Seçenek B: SQL Editor ile (Manuel - Daha Basit) ⭐ ÖNERİLEN**

**Bu yöntem en kolaydır - hiçbir şey kurmanıza gerek yok!**

1. Tarayıcınızda Supabase Dashboard açın (https://app.supabase.com)
2. Projenizi seçin
3. Sol menüden **SQL Editor** sekmesine tıklayın
4. **New Query** butonuna tıklayın
5. `infra/supabase/schema.sql` dosyasını açın (proje klasörünüzde)
6. Dosyanın **tüm içeriğini** kopyalayın (Ctrl+A, Ctrl+C)
7. SQL Editor'e yapıştırın (Ctrl+V)
8. **Run** butonuna tıklayın (veya F5)
9. ✅ **Done!** Tüm tablolar, indexler ve RPC function oluşturuldu

**💡 İpucu:** Eğer hata alırsanız, SQL'i parça parça çalıştırabilirsiniz (her CREATE TABLE ayrı ayrı).

**Seçenek C: Setup Script ile**

```bash
# Setup script'i çalıştırın
chmod +x scripts/setup-supabase.sh
./scripts/setup-supabase.sh
```

### Yöntem 2: Manuel Setup (Eski Yöntem - Daha Uzun)

Eğer otomatik setup çalışmazsa, aşağıdaki adımları manuel takip edin:

### Adım 3: Supabase API Keys (Supabase Web Sitesinde)

**📍 Bu adım da Supabase web dashboard'unda yapılır (EasyPanel'de değil!):**

1. Supabase Dashboard (web sitesi) → **Settings** → **API**
2. Şu bilgileri kopyalayın (bunları **daha sonra EasyPanel'deki servislere environment variable olarak ekleyeceksiniz**):
   - **Project URL** → `SUPABASE_URL` (örnek: `https://xxxxx.supabase.co`)
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ Gizli tutun! Router servisinde kullanılacak)
   - **anon public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Dashboard servisinde kullanılacak)

**💡 Not:** Bu bilgileri kopyalayın, çünkü EasyPanel'de servis oluştururken environment variables olarak ekleyeceksiniz.

### Adım 4: Database Schema Oluşturma (Manuel Yöntem)

⚠️ **Not:** Eğer otomatik setup kullandıysanız bu adımı atlayın!

Supabase SQL Editor'de `infra/supabase/schema.sql` dosyasını çalıştırın:

Tüm SQL komutları `infra/supabase/schema.sql` dosyasında hazır. Sadece bu dosyayı Supabase SQL Editor'de çalıştırın.

### Adım 5: Test User ve API Key Oluşturma

#### Test User Oluşturma

1. Supabase Dashboard → **Authentication** → **Users**
2. **Add User** → **Create new user**
3. Email ve password girin
4. User ID'yi kopyalayın (sonraki adımda kullanacağız)

#### API Key Oluşturma (Otomatik)

**Yöntem 1: Python Script ile (Önerilen)**

```bash
# Router environment variables'ları hazırlayın
export HASH_SALT="your-hash-salt"
export KEY_HASH_PEPPER="your-pepper"

# API key oluştur
python scripts/create-api-key.py \
  --user-id "YOUR_USER_ID" \
  --supabase-url "https://xxx.supabase.co" \
  --supabase-key "your-service-role-key" \
  --hash-salt "$HASH_SALT" \
  --hash-pepper "$KEY_HASH_PEPPER"
```

Script otomatik olarak:
- ✅ Yeni API key oluşturur
- ✅ Hash'ler
- ✅ Supabase'e kaydeder
- ✅ Key'i size gösterir (bir daha gösterilmez!)

**Yöntem 2: Manuel (Gelişmiş)**

Eğer script kullanamıyorsanız, Python REPL'de:

```python
from cfx.security import SecurityManager
import os

os.environ["HASH_SALT"] = "your-hash-salt"
os.environ["KEY_HASH_PEPPER"] = "your-pepper"

security = SecurityManager()
api_key = "cfx_test_key_123"  # Kendi key'inizi oluşturun
key_hash = security.hash_api_key(api_key)

print(f"API Key: {api_key}")
print(f"Hash: {key_hash}")

# Sonra Supabase'de:
# INSERT INTO api_keys (user_id, key_hash, status) VALUES ('USER_ID', 'HASH', 'active');
```

---

## Servislerin Oluşturulması

EasyPanel'de 3 servis oluşturacağız. **ÖNEMLİ:** LiteLLM'i önce oluşturun, çünkü Router ona bağımlı.

### 1. LiteLLM Servisi

#### Adım 1: Yeni Servis Oluştur

1. EasyPanel Project → **"Services"** sekmesinde **"+ Service"** butonuna tıklayın
2. Açılan servis seçeneklerinden **"App"** seçeneğine tıklayın
   - ⚠️ **NOT:** "Compose" değil, "App" seçin!
   - "App" = Docker Image deploy etmek için
   - "Compose" = docker-compose.yml dosyası için (LiteLLM için gerekli değil)
3. **Service Name:** `litellm` yazın
4. **Source** sekmesinde:
   - **Image:** `ghcr.io/berriai/litellm:main-latest` yazın
   - Veya **Repository URL** alanına aynı image'ı yazın
5. **Port:** `4000` (internal only, public'e expose etmeyin!)

#### Adım 2: Environment Variables

**Environment Variables** sekmesine gidin ve şunları ekleyin:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
DEEPSEEK_API_KEY=your-deepseek-key-here
OPENAI_API_KEY=sk-your-openai-key-here
PORT=4000
MODEL_LIST=claude-3-5-sonnet-20241022,deepseek-chat,gpt-4o-mini
```

#### Adım 3: Port Ayarları (ÖNEMLİ!)

**📍 Nerede:** Ana sayfada **"Ports"** bölümü var (ekranda görünüyor)

**⚠️ ÖNEMLİ:** LiteLLM için **PORT EKLEMEYİN!**

- **"Add Port"** butonuna **TIKLAMAYIN**
- LiteLLM sadece internal network'te çalışmalı (Router servisi `http://litellm:4000` ile erişecek)
- Public port eklemek güvenlik riski oluşturur

**Sadece şunu yapın:** Hiçbir şey yapmayın, port eklemeyin! ✅

#### Adım 4: Health Check (Opsiyonel)

**📍 Nerede:** Sol menüden **"Advanced"** sekmesi → **"Health Check"** bölümü

**Opsiyonel ayarlar (gerekli değil):**
- **Path:** `/health`
- **Port:** `4000`
- **Interval:** `30s`

**💡 Not:** Health Check opsiyoneldir, şimdilik atlayabilirsiniz.

#### Adım 5: Deploy

- **"Deploy"** butonuna tıklayın
- Container'ın başladığını kontrol edin (Logs sekmesinden)

---

### 2. CF-X Router Servisi

#### Adım 1: Yeni Servis Oluştur

1. EasyPanel → **"+ Service"** → **"App"** seçin
2. **Service Name:** `cfx-router` yazın
3. **Source** sekmesinde **"Git"** tab'ını seçin (ekranda görünüyor)

#### Adım 2: Git Repository Ayarları

**Ekranda görünen alanları doldurun:**

1. **Repository URL:** 
   - Zaten doldurulmuş: `https://github.com/doctorcmptrmita2/12CodexFlowMEGA`
   - ✅ Doğru, değiştirmeyin

2. **Branch:**
   - `main` (veya hangi branch'te kod varsa)
   - ✅ Doğru görünüyor

3. **Build Path:** ⚠️ **ÖNEMLİ - DEĞİŞTİRİN!**
   - Şu an: `/` (yanlış - requirements.txt bulunamıyor!)
   - **Değiştirin:** `services/cfx-router`
   - 💡 Neden? Dockerfile `COPY requirements.txt .` yapıyor, dosya `services/cfx-router/` içinde

4. **Dockerfile Path:**
   - **"Dockerfile"** tab'ına geçin (Git tab'ının yanında)
   - **Dockerfile Path:** `Dockerfile` yazın (sadece dosya adı, Build Path'e göre otomatik bulunur)
   - ⚠️ **NOT:** `services/cfx-router/Dockerfile` YAZMAYIN, sadece `Dockerfile` yazın!

5. **"Save"** butonuna tıklayın

**✅ Doğru Ayarlar:**
- **Build Path:** `services/cfx-router` (router klasörü)
- **Dockerfile Path:** `Dockerfile` (Build Path içinde otomatik bulunur)
- Bu şekilde Dockerfile `requirements.txt` ve diğer dosyaları bulabilir!

#### Adım 3: Environment Variables

**Environment Variables** sekmesine gidin:

```
PORT=8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
HASH_SALT=your-hash-salt-generate-with-openssl-rand-hex-32
KEY_HASH_PEPPER=your-pepper-generate-with-openssl-rand-hex-32
LITELLM_BASE_URL=http://litellm:4000
DAILY_REQUEST_LIMIT=1000
STREAMING_CONCURRENCY_CAP=2
CORS_ALLOWED_ORIGINS=*
```

**⚠️ ÖNEMLİ:**
- `HASH_SALT` ve `KEY_HASH_PEPPER` için güçlü random string oluşturun:
  ```bash
  openssl rand -hex 32
  ```
- `LITELLM_BASE_URL` EasyPanel'de servis adı ile çözülür: `http://litellm:4000`
- `CORS_ALLOWED_ORIGINS` production'da domain'inizi ekleyin: `https://app.yourdomain.com`

#### Adım 4: Port Ayarları

- **Container Port:** `8000`
- **Public Port:** ❌ **KAPALI** (Traefik veya reverse proxy kullanacaksanız)
- Veya **Public Port:** `8000` (direkt erişim için)

#### Adım 5: Health Check

**Health Check:**
- **Path:** `/health`
- **Port:** `8000`
- **Interval:** `30s`

#### Adım 6: Deploy

- **"Deploy"** butonuna tıklayın
- Build loglarını kontrol edin
- Container başladıktan sonra Logs sekmesinden `/health` endpoint'ini test edin

---

### 3. Dashboard Servisi

#### Adım 1: Yeni Servis Oluştur

1. **Service Type:** `Dockerfile` (veya `Git Repository`)
2. **Service Name:** `dashboard`
3. **Build Context:**
   - Git: Repository URL + branch
   - Manual: `apps/dashboard` klasörünü zip olarak yükleyin
4. **Dockerfile Path:** `apps/dashboard/Dockerfile`

#### Adım 2: Build Ayarları

**Build Settings:**
- **Build Command:** (otomatik)
- **Build Context:** `apps/dashboard`

**⚠️ NOT:** Next.js standalone build için `next.config.js`'de `output: 'standalone'` olmalı (zaten var).

#### Adım 3: Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

#### Adım 4: Port Ayarları

- **Container Port:** `3000`
- **Public Port:** `3000` (veya reverse proxy kullanacaksanız kapalı)

#### Adım 5: Health Check

**Health Check:**
- **Path:** `/` (veya `/api/health` eğer oluşturduysanız)
- **Port:** `3000`
- **Interval:** `30s`

#### Adım 6: Deploy

- **"Deploy"** butonuna tıklayın
- Build süreci uzun sürebilir (Next.js build)
- Logs sekmesinden kontrol edin

---

## Domain ve Routing Yapılandırması

### Yöntem 1: EasyPanel Reverse Proxy (Önerilen)

EasyPanel'de built-in reverse proxy varsa:

1. **Dashboard için:**
   - Domain: `app.yourdomain.com` → `dashboard:3000`

2. **Router için:**
   - Domain: `api.yourdomain.com` → `cfx-router:8000`
   - Path: `/v1/*` → `cfx-router:8000`

### Yöntem 2: Traefik Container (Gelişmiş)

Eğer EasyPanel'de Traefik container'ı çalıştırabiliyorsanız:

1. **Traefik servisi oluşturun:**
   - Image: `traefik:v2.11`
   - Ports: `80`, `443`, `8080`
   - Volumes: Traefik config dosyalarını mount edin

2. **Traefik labels ekleyin:**
   - Dashboard: `traefik.http.routers.dashboard.rule=PathPrefix(\`/\`)`
   - Router: `traefik.http.routers.router.rule=PathPrefix(\`/v1\`)`

### Yöntem 3: Nginx Reverse Proxy (Manuel)

EasyPanel'de Nginx container'ı oluşturup routing yapılandırın.

---

## Environment Variables Özeti

### LiteLLM Servisi

**OpenRouter Kullanımı (Önerilen):**

```
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
PORT=4000
MODEL_LIST=openrouter/anthropic/claude-3.5-sonnet,openrouter/deepseek/deepseek-chat,openrouter/openai/gpt-4o-mini
```

**Veya Direkt Provider Keys:**

```
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=sk-...
PORT=4000
MODEL_LIST=claude-3-5-sonnet-20241022,deepseek-chat,gpt-4o-mini
```

### CF-X Router Servisi

```
PORT=8000
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
HASH_SALT=abc123... (32+ karakter)
KEY_HASH_PEPPER=def456... (32+ karakter, farklı olmalı!)
LITELLM_BASE_URL=http://litellm:4000
DAILY_REQUEST_LIMIT=1000
STREAMING_CONCURRENCY_CAP=2
CORS_ALLOWED_ORIGINS=https://app.yourdomain.com
```

### Dashboard Servisi

```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

---

## Health Check ve Monitoring

### Router Health Check

```bash
curl http://your-router-url/health
```

Beklenen response:
```json
{"status": "healthy", "version": "0.1.0"}
```

### LiteLLM Health Check

```bash
curl http://litellm:4000/health
```

### Dashboard Health Check

```bash
curl http://your-dashboard-url/
```

### Log Monitoring

EasyPanel'de her servisin **Logs** sekmesinden:
- Real-time log görüntüleme
- Error filtering
- Log export

---

## Troubleshooting

### Problem 1: Router LiteLLM'e Bağlanamıyor

**Hata:** `Connection refused` veya `Name resolution failed`

**Çözüm:**
1. LiteLLM servisinin çalıştığını kontrol edin
2. `LITELLM_BASE_URL=http://litellm:4000` doğru mu?
3. EasyPanel'de servisler aynı network'te mi? (genellikle default network)
4. LiteLLM container'ın internal port'u `4000` mi?

### Problem 2: Supabase Connection Error

**Hata:** `Supabase credentials not configured`

**Çözüm:**
1. Environment variables'ı kontrol edin:
   - `SUPABASE_URL` doğru mu?
   - `SUPABASE_SERVICE_ROLE_KEY` doğru mu?
2. Supabase projesinin aktif olduğunu kontrol edin
3. Service role key'in expire olmadığını kontrol edin

### Problem 3: Authentication Always Fails

**Hata:** `Invalid API key`

**Çözüm:**
1. API key'in Supabase'de hash'lenmiş olarak kayıtlı olduğunu kontrol edin
2. `HASH_SALT` ve `KEY_HASH_PEPPER` değerlerinin doğru olduğunu kontrol edin
3. API key hash'leme fonksiyonunu test edin:
   ```python
   from cfx.security import SecurityManager
   sm = SecurityManager()
   hash = sm.hash_api_key("your-api-key")
   print(hash)
   ```

### Problem 4: Rate Limit Not Working

**Hata:** Rate limit her zaman allow ediyor

**Çözüm:**
1. Supabase'de `usage_counters` tablosunun oluşturulduğunu kontrol edin
2. RPC function `increment_usage_counter` oluşturuldu mu?
3. Router logs'unda database error var mı?

### Problem 5: Dashboard Build Fails

**Hata:** `npm install` veya `npm run build` fails

**Çözüm:**
1. `package.json` dosyasının doğru olduğunu kontrol edin
2. Node.js version'ı `20-alpine` mi? (Dockerfile'da)
3. Build logs'unda spesifik error mesajını kontrol edin

### Problem 6: CORS Error

**Hata:** `CORS policy: No 'Access-Control-Allow-Origin' header`

**Çözüm:**
1. Router'da `CORS_ALLOWED_ORIGINS` environment variable'ını kontrol edin
2. Dashboard domain'ini ekleyin: `CORS_ALLOWED_ORIGINS=https://app.yourdomain.com`
3. Wildcard kullanmayın production'da: `CORS_ALLOWED_ORIGINS=*` ❌

---

## Production Checklist

Deploy sonrası kontrol listesi:

- [ ] Tüm servisler çalışıyor (health check OK)
- [ ] Supabase schema oluşturuldu (tables + RLS policies)
- [ ] RPC function `increment_usage_counter` çalışıyor
- [ ] Test API key oluşturuldu ve test edildi
- [ ] Router `/health` endpoint çalışıyor
- [ ] Dashboard erişilebilir
- [ ] CORS ayarları production için restrict edildi
- [ ] `HASH_SALT` ve `KEY_HASH_PEPPER` güçlü random string'ler
- [ ] Domain SSL/TLS yapılandırıldı (Let's Encrypt)
- [ ] Monitoring/logging kuruldu
- [ ] Backup stratejisi hazır

---

## Test Senaryoları

### 1. API Key Authentication Test

```bash
curl -X POST http://your-router-url/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-CFX-Stage: plan" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 2. Streaming Test

```bash
curl -X POST http://your-router-url/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-CFX-Stage: code" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Write hello world"}],
    "stream": true
  }'
```

### 3. Rate Limit Test

1000+ request göndererek rate limit'in çalıştığını test edin.

---

## Destek ve Kaynaklar

- **CF-X Documentation:** `README.md`, `proje.md`
- **EasyPanel Docs:** [EasyPanel Documentation](https://easypanel.io/docs)
- **Supabase Docs:** [Supabase Documentation](https://supabase.com/docs)

---

## Sonuç

CF-X platformu EasyPanel'de başarıyla deploy edildi! 🎉

Sorularınız için:
- GitHub Issues
- EasyPanel Support
- Supabase Community

**İyi deploy'lar!** 🚀

