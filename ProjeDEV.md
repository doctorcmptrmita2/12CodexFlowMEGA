# CF-X İş Modeli & Geliştirme Stratejisi

## Öne Çıkan 3 Özellik

### 1. Plan-Code-Review = Denetlenebilir Üretim (Proof-Driven)
- "Chat" değil; çıktı unified diff / patch ve review ile gelir
- Ekiplerde "ne değişti, neden değişti?" sorusunu çözer
- Audit trail ve rollback imkanı

### 2. Maliyet + Yönetişim Katmanı (Router Merkezli)
- Kullanıcı bazlı API key, günlük limit, concurrency cap
- Log/cost/token takibi
- "Agent kullanıyorum ama fatura sürpriz" problemini hedef alır

### 3. Roo Code / OpenAI Uyumluluğu + Self-Host / Proxy Mimarisi
- IDE tarafı (Roo Code) değişmeden bağlanır
- Arkada LiteLLM ile multi-provider çalışır
- Cline gibi "extension bedava, kullanım kadar öde" yaklaşımını destekler

---

## Global Marka Potansiyeli

**Evet—ama "bir IDE eklentisi" gibi değil, "Teams için governed coding gateway" diye konumlanırsa.**

Cursor gibi ürünler dünyada aylık $20+ seviyesinde fiyatlanıyor. Senin farkın: **governance + cost control + audit logs** (özellikle ekipler/ajanslar).

**Risk:** "Bizde Claude+DeepSeek+Review var" demek tek başına yetmez; herkes model kombinasyonu yapabiliyor. Global farkı **"kontrol, kanıt, denetim"** üzerinden satmalısın.

---

## Projeyi Geliştirme Önerileri (En Değerli 5 Ek)

### 1. Budget/Credits Sistemi (Token Bazlı)
- "1000 request/day" yerine "aylık token/credit havuzu + hard cap"
- Token bazlı limitler maliyet kontrolünü sağlar
- Kullanıcıya şeffaf kullanım görünürlüğü

### 2. Repo/PR Entegrasyonu
- GitHub PR review bot + patch uygula/geri al (audit trail)
- Otomatik code review ve onay akışı
- Git history ile entegre değişiklik takibi

### 3. Policy-as-Code
- Hangi klasörlerde değişiklik serbest, hangi dosyalara dokunamaz
- Lisans/secret taraması
- Compliance ve güvenlik kuralları otomasyonu

### 4. Eval & Kalite Skoru
- "Bu ajan kaç kez rollback oldu, kaç denemede çözdü?" gibi metrikler
- Model performans karşılaştırması
- Kullanıcı memnuniyet skorları

### 5. Takım Özellikleri
- SSO, RBAC, pooled usage
- Proje başına limit
- Organizasyon bazlı yönetim

---

## Maliyet/Gelir Hesabı (Gerçekçi Çerçeve)

### Model Maliyetleri (Token Bazlı)

**OpenRouter üzerinden (Aralık 2025):**

| Model | Input (1K token) | Output (1K token) |
|-------|------------------|-------------------|
| Claude Sonnet 4.5 | ~$0.003 | ~$0.015 |
| DeepSeek V3.2 | ~$0.000224 | ~$0.00032 |
| GPT-4o-mini | ~$0.00015 | ~$0.0006 |

**Kur:** USD/TRY ≈ 42.94 (30 Aralık 2025)

### Neden "1000 Request/Day" Tehlikeli?

**"Request" = maliyet değildir.** Bir request 500 token da olabilir 50.000 token da. Bu yüzden request limiti tek başına seni batırabilir.

**Örnek Senaryo:**
- 1000 request/day limiti var
- Her request ortalama 10K token (5K input + 5K output)
- Claude Sonnet kullanılıyor: (5K × $0.003) + (5K × $0.015) = $0.09/request
- Günlük maliyet: 1000 × $0.09 = **$90/gün = $2.700/ay**
- Bu maliyetle 600 TL/ay fiyatlandırma **imkansız**

**Çözüm:** Token bazlı budget + request limit kombinasyonu

---

## Fiyatlandırma Stratejisi

### Türkiye Odaklı (TL) — Basit

| Plan | Fiyat | Aylık Token | Günlük Request | Concurrency | Kullanım |
|------|-------|-------------|----------------|-------------|----------|
| **Starter** | 599 TL/ay | ~1M token | 200 | 1 stream | Tek kişi |
| **Pro** | 1.299 TL/ay | ~4M token | 600 | 2 stream | Power user |
| **Agency** | 3.999 TL/ay | ~15M token | 2000 | 5 stream | 5-10 seat |

### Global (USD) — Marka İçin Şart

| Plan | Fiyat | Aylık Token | Günlük Request | Concurrency | Kullanım |
|------|-------|-------------|----------------|-------------|----------|
| **Starter** | $15/ay | ~1M token | 200 | 1 stream | Tek kişi |
| **Pro** | $35/ay | ~4M token | 600 | 2 stream | Power user |
| **Agency** | $99/ay | ~15M token | 2000 | 5 stream | 5-10 seat |

**Not:** Cursor fiyat bandına oturur ($20-50/ay), rekabetçi kalır.

---

## Limit Stratejisi (2 Katmanlı)

### Katman 1: Aylık Credit/Token Bütçesi (Asıl Fren)
- Token bazlı hard cap
- Kullanıcıya şeffaf görünürlük
- Aylık reset

### Katman 2: Günlük Request Limit (Abuse Fren)
- Spam/abuse önleme
- Rate limiting
- Concurrency cap

**Kritik:** "Run" metriği satması kolay; ama altyapıda token budget ile enforce et. "Request/day 1000" tek başına stabil iş modeli değil.

---

## Maliyet Analizi & Kârlılık

### Senaryo 1: Starter Plan (599 TL ≈ $14)

**Varsayımlar:**
- Aylık 1M token limiti
- Kullanım: %70 (700K token/ay)
- Ortalama model mix: %40 Claude, %40 DeepSeek, %20 GPT-4o-mini
- Input/Output ratio: 60/40

**Token Dağılımı:**
- Claude: 280K token (168K input, 112K output)
- DeepSeek: 280K token (168K input, 112K output)
- GPT-4o-mini: 140K token (84K input, 56K output)

**Maliyet Hesaplama:**
- Claude: (168 × $0.003) + (112 × $0.015) = $0.504 + $1.68 = **$2.184**
- DeepSeek: (168 × $0.000224) + (112 × $0.00032) = $0.038 + $0.036 = **$0.074**
- GPT-4o-mini: (84 × $0.00015) + (56 × $0.0006) = $0.013 + $0.034 = **$0.047**

**Toplam Maliyet:** $2.305 ≈ **99 TL**

**Brüt Kâr:** 599 - 99 = **500 TL/ay/kullanıcı** (%83.5 margin)

### Senaryo 2: Pro Plan (1.299 TL ≈ $30)

**Varsayımlar:**
- Aylık 4M token limiti
- Kullanım: %75 (3M token/ay)
- Aynı model mix

**Maliyet:** ~$9.9 ≈ **425 TL**

**Brüt Kâr:** 1.299 - 425 = **874 TL/ay/kullanıcı** (%67.3 margin)

### Senaryo 3: Agency Plan (3.999 TL ≈ $93)

**Varsayımlar:**
- Aylık 15M token limiti (pooled, 5-10 kullanıcı)
- Kullanım: %80 (12M token/ay)
- Aynı model mix

**Maliyet:** ~$39.6 ≈ **1.700 TL**

**Brüt Kâr:** 3.999 - 1.700 = **2.299 TL/ay/organizasyon** (%57.5 margin)

---

## Risk Analizi & Öneriler

### Risk 1: Token Kullanımı Tahmin Edilenden Yüksek
**Çözüm:**
- Soft limit + hard limit sistemi
- %80 kullanımda uyarı
- %100'de otomatik durdurma
- Opsiyonel "top-up" paketleri

### Risk 2: Model Fiyatları Değişebilir
**Çözüm:**
- Dinamik fiyatlandırma (provider maliyetine göre)
- Multi-provider fallback
- Kullanıcıya model seçim özgürlüğü (limit içinde)

### Risk 3: Abuse & Fraud
**Çözüm:**
- API key doğrulama (email verification)
- Rate limiting (request + token bazlı)
- Anomali tespiti (sıra dışı kullanım pattern'leri)
- Concurrency cap enforcement

### Risk 4: Rekabet (Cursor, Cline, vb.)
**Çözüm:**
- Farklılaştırma: Governance + Audit + Cost Control
- Self-host seçeneği (enterprise)
- Açık API (entegrasyon kolaylığı)
- Türkiye pazarında erken giriş avantajı

---

## Geliştirme Öncelikleri

### MVP Sonrası (İlk 3 Ay)
1. **Token Budget Sistemi** (kritik - maliyet kontrolü için)
2. **Usage Dashboard** (kullanıcı görünürlüğü)
3. **Email Notifications** (limit uyarıları)

### 6 Ay İçinde
1. **GitHub Integration** (PR review bot)
2. **Policy-as-Code** (güvenlik kuralları)
3. **Team Features** (SSO, RBAC)

### 12 Ay İçinde
1. **Eval & Metrics** (kalite skorları)
2. **Multi-tenant** (white-label)
3. **Enterprise Self-host** (on-premise)

---

## Pazarlama & Konumlandırma

### Türkiye Pazarı
- **Hedef:** Küçük/orta ölçekli yazılım ekipleri, ajanslar
- **Mesaj:** "AI coding maliyetlerini kontrol altına alın"
- **Fiyat:** TL bazlı, rekabetçi (Cursor'dan daha uygun)

### Global Pazar
- **Hedef:** Enterprise teams, agencies
- **Mesaj:** "Governed AI coding with full audit trail"
- **Fiyat:** USD bazlı, Cursor seviyesi
- **Fark:** Cost control + governance (Cursor'da yok)

---

## Sonuç & Öneriler

### Kritik Başarı Faktörleri
1. **Token bazlı limit sistemi** (request limiti yeterli değil)
2. **Şeffaf kullanım görünürlüğü** (kullanıcı ne kadar kullandığını görmeli)
3. **Abuse prevention** (rate limiting + concurrency cap)
4. **Farklılaştırma** (governance + audit + cost control)

### İlk Adımlar
1. MVP'yi token budget sistemi ile tamamla
2. Beta test kullanıcıları ile gerçek kullanım verilerini topla
3. Model mix ve token kullanım pattern'lerini analiz et
4. Fiyatlandırmayı gerçek verilere göre optimize et

### Uzun Vadeli Vizyon
- **Türkiye:** #1 AI coding governance platform
- **Global:** Enterprise teams için "governed coding gateway"
- **Fark:** Cursor'dan governance, Cline'dan cost control, GitHub'dan audit trail

---

**Not:** Bu analiz Aralık 2025 verilerine göre hazırlanmıştır. Model fiyatları ve kur değişebilir; düzenli güncelleme önerilir.

