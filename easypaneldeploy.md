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

- ✅ EasyPanel hesabı ve erişimi
- ✅ Supabase projesi (ücretsiz tier yeterli)
- ✅ Domain adı (opsiyonel, IP ile de çalışır)
- ✅ Provider API keys:
  - Anthropic API Key
  - DeepSeek API Key
  - OpenAI API Key (opsiyonel)

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

### Yöntem 1: Otomatik Setup (Önerilen) 🚀

Supabase schema'sını tek komutla otomatik deploy edebilirsiniz:

#### Adım 1: Supabase Projesi Oluşturma

1. [Supabase Dashboard](https://app.supabase.com) → **New Project**
2. Proje bilgilerini doldurun:
   - **Name:** `cfx-database` (veya farklı bir isim - EasyPanel projesinden bağımsız)
   - **Database Password:** Güçlü bir şifre oluşturun (kaydedin!)
   - **Region:** Size en yakın region seçin
3. **Create new project** butonuna tıklayın (2-3 dakika sürebilir)

#### Adım 2: Schema'yı Otomatik Deploy Etme

**Seçenek A: Supabase CLI ile (En Kolay)**

```bash
# 1. Supabase CLI'yi yükleyin
npm install -g supabase

# 2. Supabase'e login olun
supabase login

# 3. Schema'yı deploy edin
cd infra/supabase
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"
```

**Seçenek B: SQL Editor ile (Manuel - Daha Basit)**

1. Supabase Dashboard → **SQL Editor**
2. **New Query** butonuna tıklayın
3. `infra/supabase/schema.sql` dosyasının içeriğini kopyalayın
4. SQL Editor'e yapıştırın
5. **Run** butonuna tıklayın
6. ✅ **Done!** Tüm tablolar, indexler ve RPC function oluşturuldu

**Seçenek C: Setup Script ile**

```bash
# Setup script'i çalıştırın
chmod +x scripts/setup-supabase.sh
./scripts/setup-supabase.sh
```

### Yöntem 2: Manuel Setup (Eski Yöntem - Daha Uzun)

Eğer otomatik setup çalışmazsa, aşağıdaki adımları manuel takip edin:

### Adım 3: Supabase API Keys

1. Supabase Dashboard → **Settings** → **API**
2. Şu bilgileri kopyalayın (sonraki adımlarda kullanacağız):
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ Gizli tutun!)
   - **anon public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`

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

1. EasyPanel Project → **"Services"** → **"New Service"**
2. **Service Type:** `Docker Image`
3. **Service Name:** `litellm`
4. **Image:** `ghcr.io/berriai/litellm:main-latest`
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

#### Adım 3: Network Ayarları

- **Network:** Default network (diğer servislerle aynı)
- **Public Port:** ❌ **KAPALI** (internal only!)

#### Adım 4: Health Check

**Health Check** sekmesinde:
- **Path:** `/health`
- **Port:** `4000`
- **Interval:** `30s`

#### Adım 5: Deploy

- **"Deploy"** butonuna tıklayın
- Container'ın başladığını kontrol edin (Logs sekmesinden)

---

### 2. CF-X Router Servisi

#### Adım 1: Yeni Servis Oluştur

1. **Service Type:** `Dockerfile` (veya `Git Repository` eğer repo'ya push ettiyseniz)
2. **Service Name:** `cfx-router`
3. **Build Context:** 
   - Git kullanıyorsanız: Repository URL + branch
   - Manual upload: `services/cfx-router` klasörünü zip olarak yükleyin
4. **Dockerfile Path:** `services/cfx-router/Dockerfile` (veya sadece `Dockerfile`)

#### Adım 2: Build Ayarları

**Build Settings:**
- **Build Command:** (otomatik, Dockerfile'dan alınır)
- **Build Context:** `services/cfx-router`

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

