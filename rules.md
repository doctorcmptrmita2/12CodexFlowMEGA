# CF-X Engineering Rules

Bu repo CF-X (CodexFlow) için monorepo + multi-container mimarisi kullanır.
Hedef: Plan→Code→Review orkestrasyonu + maliyet kontrolü + audit log + Roo Code uyumluluğu.

## 1) Part Sistemi (Zorunlu)
- Çıktılar Part 1 / Part 2 / ... şeklinde ilerler.
- Her Part'ta maksimum 3 dosya değişir.
- Değişiklikler unified diff formatında yapılır.
- Tam dosya yeniden yazmak yasak (gerekmedikçe).

## 2) Servis Sınırları
- Dashboard: `/apps/dashboard/**`
- Router: `/services/cfx-router/**`
- LiteLLM: `/services/litellm/**` (config)
- Config: `/config/**`
- Infra: `/infra/**` + `docker-compose.yml`

Her Part tek servis alanına odaklanır. Aynı Part'ta dashboard + router karışmaz.

## 3) Güvenlik Sınırları (En Kritik)
- Dashboard tarafında **service role key yok**.
- Provider API key'leri sadece LiteLLM container'da bulunur.
- Router:
  - API key doğrulama
  - rate limit
  - stage routing
  - streaming relay
  - logging
  işlerinin tek otoritesidir.
- Loglarda Authorization header, raw API key, secret parçaları tutulmaz (redaction).

## 4) OpenAI Uyumluluğu
- Router: `POST /v1/chat/completions`
- `stream=true` ise SSE formatı doğru olmalı:
  - `data: {...}\n\n` parçalı
  - kapanış: `data: [DONE]\n\n`

## 5) Stabilite & Dayanıklılık
- Upstream timeout zorunlu.
- Retry sadece 502/503/504 için ve maksimum 1 kez.
- Circuit breaker: upstream sürekli patlıyorsa kısa süre 503 dön.
- Per-user streaming concurrency cap (örn 2).
- Logging best-effort: log hatası request'i düşürmez.

## 6) Deploy Topology
- Public entrypoint: reverse proxy (Traefik/EasyPanel proxy)
- `/` → dashboard
- `/v1/*` → router
- Router → LiteLLM internal network üzerinden konuşur.
- LiteLLM dışarıya açılmaz.

## 7) Review Standartları
Her Part sonunda:
- Yapılanlar özeti
- Manuel kontrol listesi
- Riskler/edge-case'ler
- Sonraki Part'a geçmeden onay iste

