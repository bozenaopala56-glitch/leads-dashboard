# 🔬 Pełna Analiza Architektoniczna — MeNET Leads + Leadpipe Integration

**Data:** 2026-05-27  
**Analizator:** CodexLuxeworbot  
**Zakres:** Lead Management (web forms) + Leadpipe (T0/T1/T2 + scraper + copywriter) + CEO workflow

---

## 1. Obecny Stan Systemów

### 1.1 VM Cluster

| VM | Rola | IP | Aktywne usługi |
|---|---|---|---|
| **hermes-agent** | Main hub, boty, gatewaye | 10.186.0.2 | Hermes profiles, Codex CLI, gatewaye Telegram |
| **mennet-deploy** | Prod/preview, reverse proxy | 10.186.0.4 | Caddy + Authelia, statyczne strony, PM2 apps |
| **sandbox-bot-v3** | Scraper + pipeline + AI | 10.186.0.3 | Self-evolving-core (port 8765), leadpipe, copywriter, scrapery |

### 1.2 Leadpipe (sandbox-bot-v3)

**Repo:** `bozenaopala56-glitch/leadpipe` (Python, 140KB)  
**Dokumentacja:** 14 plików .md (SPEC, ARCH, RAPORTY, REGUŁY, ZADANIA)

#### Komponenty pipeline:

```
Scraper (pkt.pl / panoramafirm / overpass / ceneo / olx / CEIDG)
  ↓
Company Check (GUS REGON / NIP weryfikacja)
  ↓
Lead Store (self-evolving-core/data/leads/vision_reports/)
  ↓
T0 Scanner (~40-85 sygnałów binarnych: HTTP, SSL, DNS, HTML, tech detection)
  ↓
T0.5 Enrichment (NIP, VAT, Biała Lista, business identity)
  ↓
T1 Parser (JSON-LD, OG, meta, headings, contact, CTA, industry fit)
  ↓
Decision Gates (7 bramek: compliance, quality, fit, contactability, evidence)
  ↓
Campaign Engine (7 kampanii: REDESIGN_*, WORDPRESS_REWORK, MOBILE_REBUILD, TECH_REBUILD)
  ↓
T2 Vision (Playwright screenshot + Kimi k2.5 vision analysis)
  ↓
Copywriter Generator (email + phone script drafts)
  ↓
Copywriter Reviewer (QA copywritingu)
  ↓
CEO Queue (ATTACK / SKIP / MANUAL_REVIEW decision)
  ↓
CEO Auto-Decider (reguły automatyczne dla pewnych przypadków)
  ↓
Outbox / Outreach (email + phone execution)
  ↓
Feedback Loop (reply, bounce, opt-out → suppression + retraining)
```

#### Dane:

| Lokalizacja | Co tam jest | Format |
|---|---|---|
| `/home/hermes/data/leads/` | Symlink do `self-evolving-core/data/leads/` | mix |
| `vision_reports/` | Raporty markdown per lead | `.md` z frontmatter YAML |
| `index.jsonl` | Indeks wszystkich leadów | JSON Lines |
| `archive/` | Archiwum przetworzonych | foldery z datą |
| `analytics/` | Metryki, snapshoty | `.json`, `.csv` |
| `scraper_lodz_v2.log` | Log scrapera (aktualnie działa!) | text |

#### Aktywne procesy na v3 (sprawdzone):

```
PID 570415: self-evolving-core dashboard (port 8765)     ← DZIAŁA
PID 853798: scrape_verify_save_v2.py --city Łódź           ← DZIAŁA TERAZ
```

#### Dashboardy na v3:

| Dashboard | URL / Lokalizacja | Stan |
|---|---|---|
| **Self-Evolving Core Dashboard** | `http://10.186.0.3:8765` | ✅ Działa, Py UI |
| **Leadpipe QA Dashboard** | `/home/hermes/leadpipe/dashboard/` | 📁 Statyczny HTML/JS, niepostawiony |
| **CEO Dashboard** | `/home/hermes/scripts/ceo-dashboard.html` | 📁 Plik HTML, niepostawiony |

### 1.3 Lead Management (web forms)

| Komponent | Stan |
|---|---|
| **Webhook** | `POST /api/leads` na mennet-deploy (zapisuje do `leads.json`) |
| **Dashboard** | Pusty placeholder na `/home/hermes/dashboard/` (domena `leads.luxewor.duckdns.org`) |
| **Repo** | `bozenaopala56-glitch/leads-dashboard` (utworzone, SPEC.md wgrany) |
| **Auth** | Authelia SSO (admin + bartas konta) |

---

## 2. Architektura Docelowa — Unified Ops Center

### 2.1 Wizja

Jeden **MeNET Ops Dashboard** jako single pane of glass. Nie osobne dashboardy, tylko jeden z modułami:

```
┌─────────────────────────────────────────────────────────────┐
│                   MeNET Ops Dashboard                        │
│              https://ops.luxewor.duckdns.org                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Leads   │  │ Pipeline │  │Scraper   │  │ Outreach │     │
│  │   CRM    │  │  T0→T2  │  │ Status   │  │  Stats   │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           CEO Command Center (ATTACK/SKIP)              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         Copywriter Queue + Draft Preview                │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment

| Domena | Co tam | VM | Auth |
|---|---|---|---|
| `leads.luxewor.duckdns.org` | Lead CRM (web forms) | mennet-deploy | Authelia |
| `ops.luxewor.duckdns.org` | **MeNET Ops Dashboard** (unified) | mennet-deploy | Authelia |
| `pipeline.luxewor.duckdns.org` | API proxy do v3 | mennet-deploy | Authelia |

### 2.3 Backend — wspólny API Gateway

Na **mennet-deploy** stoi jeden backend Node.js/Express:

```javascript
// Unified API Gateway (mennet-deploy)
app.use('/api/leads',        leadsRouter);      // web form leads (SQLite)
app.use('/api/pipeline',       pipelineRouter);   // proxy do v3 API
app.use('/api/scraper',        scraperRouter);    // status, start, stop, config
app.use('/api/copywriter',     copywriterRouter); // drafts, queue, approve
app.use('/api/ceo',           ceoRouter);        // decisions, stats
app.use('/api/outreach',       outreachRouter);   // outbox, feedback
app.use('/api/analytics',      analyticsRouter);  // unified stats
```

Proxy do v3 przez internal VPC (10.186.0.3):
```javascript
// pipeline proxy
app.use('/api/pipeline', createProxyMiddleware({
  target: 'http://10.186.0.3:8765',
  changeOrigin: true,
}));
```

### 2.4 Moduły Dashboardu (React/Vite)

#### Moduł A: Leads CRM (z web formularzy)
- TanStack Table: leady z `/api/leads`
- Statusy: new, contacted, qualified, converted, lost
- Bulk actions, filtry, eksport
- **Integracja:** leady z web formularzy mogą być pushowane do pipeline (button "Dodaj do pipeline")

#### Moduł B: Pipeline T0→T2
- **T0 Queue:** lista leadów w skanowaniu, progress bar, sygnały techniczne
- **T1 Queue:** wyniki parsowania, contactability, industry fit
- **Decision Gates:** które bramki przeszły/blokowały
- **Campaign Assignment:** która kampania została przypisana
- **T2 Vision:** screenshot + wyniki analizy wizualnej
- **Timeline per lead:** `new → T0 → T0.5 → T1 → gates → campaign → T2 → copywriter → CEO`

#### Moduł C: Scraper Ops
- **Active Scrapers:** które scrapery działają (miasto, nisza, progres)
- **Start/Stop/Pause** z UI
- **Discovered vs Verified:** ile znaleziono vs ile przeszło company check
- **Log tail:** ostatnie 50 linii logu scrapera

#### Moduł D: Copywriter Queue
- **Drafts inbox:** wygenerowane emaile + phone scripty
- **Reviewer queue:** czekające na review
- **Approved drafts:** gotowe do wysyłki
- **Preview:** renderowanie emaila w iframe

#### Moduł E: CEO Command Center
- **Inbox decisions:** leady czekające na ATTACK/SKIP (z T0+T1+T2 danymi)
- **Quick stats:** ile w kolejce, ile zaakceptowanych, conversion rate
- **Decision history:** kto, kiedy, dlaczego
- **Auto-decider config:** próg confidence dla auto-ATTACK

#### Moduł F: Outreach & Feedback
- **Outbox:** zaplanowane emaile/telefony
- **Sent:** wysłane + open rate (jeśli trackowane)
- **Replies:** lista odpowiedzi
- **Feedback import:** CSV upload (reply/bounce/opt-out)
- **Suppression list:** domeny/emails do pominięcia

#### Moduł G: Analytics (unified)
- **Funnel:** Discovered → Verified → T0 → T1 → Campaign → Copywriter → CEO → Outreach → Reply
- **Conversion by campaign:** która kampania ma najlepszy reply rate
- **Scraper efficiency:** leady/minutę per miasto/nisza
- **Copywriter quality:** które drafty CEO akceptuje/rejectuje
- **Revenue pipeline:** wartość leadów w poszczególnych stage'ach

---

## 3. Integracja Leadpipe ↔ Leads CRM

### 3.1 Dwukierunkowy flow

```
Web Form Lead ──→ leads.luxewor.duckdns.org ──→ API ──→ SQLite
                                    │
                                    │ (button "Uruchom pipeline")
                                    ▼
                              POST /api/pipeline/leads
                                    │
                                    ▼
                            sandbox-bot-v3 (v3 API)
                                    │
                                    ▼
                              T0 → T1 → Decision → Campaign
                                    │
                                    ▼
                            Copywriter → CEO → Outreach
                                    │
                                    ▼
                              Feedback loop ──→ update lead status w CRM
```

### 3.2 Scraper Lead → CRM

```
Scraper v3 ──→ Discovered lead ──→ Company check (GUS) ──→ Verified
                                              │
                                              ▼
                                       Auto-dodanie do CRM
                                       status: "auto_scraped"
                                       source: "scraper_pkt_pl"
```

### 3.3 Unified Lead Record

```typescript
interface UnifiedLead {
  // Core
  id: string;
  domain: string;
  company_name: string;
  nip: string;
  email: string;
  phone: string;
  
  // Source
  source: "web_form" | "scraper_pkt" | "scraper_panoramafirm" | "scraper_ceidg" | "manual";
  source_detail: string; // np. "formularz main-hub", "pkt.pl Łódź usługi"
  
  // Pipeline status
  pipeline_status: 
    | "not_in_pipeline" 
    | "t0_queued" | "t0_running" | "t0_done"
    | "t1_queued" | "t1_running" | "t1_done"
    | "decision_gates" 
    | "campaign_assigned"
    | "t2_queued" | "t2_running" | "t2_done"
    | "copywriter_queued" | "copywriter_done"
    | "ceo_review" | "ceo_approved" | "ceo_rejected"
    | "outreach_queued" | "outreach_sent" | "replied" | "converted";
  
  // Campaign (jeśli przeszedł pipeline)
  campaign: CampaignKey | null;
  campaign_confidence: number;
  
  // Scraper data
  scraper_city: string | null;
  scraper_niche: string | null;
  scraper_verified: boolean;
  
  // CRM data
  crm_status: "new" | "contacted" | "qualified" | "proposal" | "negotiation" | "won" | "lost";
  crm_notes: string;
  assigned_to: string; // bartas, ceo, etc.
  
  // Timestamps
  created_at: string;
  updated_at: string;
  pipeline_started_at: string | null;
  pipeline_finished_at: string | null;
}
```

---

## 4. Tech Stack Recommendation

### 4.1 Frontend (Dashboard)

| Layer | Tech | Uzasadnienie |
|---|---|---|
| Framework | React 19 + TypeScript | Masz już spec |
| Build | Vite | Szybki, prosty |
| Styling | Tailwind CSS v4 + shadcn/ui | Masz już spec |
| Tables | TanStack Table | Leads + pipeline lists |
| Charts | Recharts | Funnel, stats |
| Routing | React Router v7 | Moduły jako routes |
| State | Zustand | Prostszy niż Redux |
| API | React Query (TanStack Query) | Cache, polling, sync |
| Auth | Headers Authelia | Remote-User, Remote-Groups |

### 4.2 Backend (mennet-deploy)

| Layer | Tech | Uzasadnienie |
|---|---|---|
| Runtime | Node.js 20 | Ekosystem, prosty |
| Framework | Express.js | Lekki, stabilny |
| DB local | SQLite (leads web forms) | Prosty, backupowalny |
| DB pipeline | Postgres (na v3) | Leadpipe już używa |
| Proxy | http-proxy-middleware | Tunel do v3 |
| Auth | Passport.js + Authelia headers | SSO ready |

### 4.3 API v3 (sandbox-bot-v3)

Leadpipe potrzebuje REST API wrappera:

```python
# /home/hermes/leadpipe/api/main.py
from fastapi import FastAPI
from leadpipe.engine import DecisionEngine

app = FastAPI()
engine = DecisionEngine()

@app.get("/api/pipeline/status")
def pipeline_status():
    return {
        "t0_queue": get_t0_queue_count(),
        "t1_queue": get_t1_queue_count(),
        "t2_queue": get_t2_queue_count(),
        "copywriter_queue": get_copywriter_queue(),
        "ceo_queue": get_ceo_queue(),
        "outbox": get_outbox_count(),
    }

@app.get("/api/pipeline/leads")
def list_leads(status: str = None, limit: int = 50):
    ...

@app.post("/api/pipeline/leads")
def add_lead(lead: LeadInput):
    # Dodanie leada do pipeline (z web form lub scraper)
    ...

@app.get("/api/scraper/status")
def scraper_status():
    # Process check PID 853798
    ...

@app.post("/api/scraper/start")
def start_scraper(city: str, niche: str):
    ...

@app.get("/api/copywriter/drafts")
def list_drafts():
    ...

@app.post("/api/copywriter/approve/{lead_id}")
def approve_draft(lead_id: str):
    ...

@app.get("/api/ceo/queue")
def ceo_queue():
    ...

@app.post("/api/ceo/decide/{lead_id}")
def ceo_decide(lead_id: str, decision: Literal["attack", "skip", "manual"]):
    ...
```

---

## 5. Deployment Plan

### Faza 1: Infrastructure (zero-risk)

1. **Authelia groups** — dodać `ops`, `ceo`, `copywriter`, `scraper` role
2. **Caddy vhosts** — `ops.luxewor.duckdns.org`, `pipeline.luxewor.duckdns.org`
3. **Internal VPC** — upewnić się że mennet-deploy widzi v3 (10.186.0.3:8765)

### Faza 2: API v3 (backend)

1. Zbudować FastAPI wrapper wokół leadpipe
2. Dockerize lub systemd service
3. Expose na porcie np. 8092 (tylko internal VPC)

### Faza 3: Unified Backend (mennet-deploy)

1. Node.js Express app na porcie 8093
2. SQLite schema dla unified leads
3. Proxy do v3 API
4. Webhook integration (leads web form → unified API)

### Faza 4: Frontend Dashboard (mennet-deploy)

1. React app z modułami A-G
2. Build → `/var/www/ops/`
3. Caddy serwuje static + proxy `/api/*` do Node backendu

### Faza 5: Data Migration

1. Import leadów z `data/leads/vision_reports/` do SQLite
2. Mapowanie statusów frontmatter YAML → pipeline_status
3. CEO queue initial load

---

## 6. Ryzyka i Ograniczenia

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|---|---|---|---|
| v3 nie ma public API | WYSOKIE | BLOKUJĄCE | Zbudować FastAPI wrapper |
| Self-evolving-core dashboard konflikt portu | ŚREDNIE | ŚREDNIE | Przesunąć na inny port lub zintegrować |
| 200+ skryptów na v3 bez orchestracji | WYSOKIE | WYSOKIE | Nie ruszać działającego, tylko read-only API |
| Lead data format mismatch | ŚREDNIE | ŚREDNIE | Unified schema + migrator |
| Authelia role mapping | NISKIE | ŚREDNIE | Dodać grupy w users.yml |
| v3 → mennet-deploy bandwidth | NISKIE | NISKIE | Internal VPC 10Gbps |

---

## 7. Quick Wins (przed pełną implementacją)

1. **CEO Dashboard postawić na v3** — `python3 -m http.server 8080` w `/home/hermes/scripts/` + Caddy reverse proxy
2. **Leadpipe dashboard postawić** — `python3 backend.py` w `/home/hermes/leadpipe/dashboard/` + Caddy
3. **Proxy do v3 z mennet-deploy** — w Caddy `handle_path /api/pipeline/*` → `10.186.0.3:8765`
4. **Unified SQLite na mennet-deploy** — schema + import z leads.json
5. **Cron dla scraper status** — `scripts/scraper_pulse_checker_v2.py` zapisuje JSON → dashboard read

---

## 8. Podsumowanie Decyzji

| Pytanie | Odpowiedź |
|---|---|
| Jeden czy dwa dashboardy? | **Jeden Unified Ops Dashboard** (`ops.luxewor.duckdns.org`) z modułami |
| Gdzie stoi frontend? | mennet-deploy (Caddy + static) |
| Gdzie stoi backend? | mennet-deploy (Node.js + SQLite) + v3 (FastAPI proxy) |
| Auth? | Authelia SSO z rolami: admin, ceo, copywriter, ops |
| Pierwszy krok? | Postawić API wrapper na v3 + proxy w Caddy |
| Leadpipe repo — czy zmieniać? | **NIE** — read-only integracja, nie modyfikować |

---

**Rekomendacja:** Zacząć od **Quick Win #3** — proxy API z mennet-deploy do v3. Wtedy możesz zobaczyć wszystkie dane pipeline w przeglądarce bez ruszania działającego systemu.

**Następny krok:** Daj 'go'/'rob' który phase chcesz żebym zaczął implementować.
