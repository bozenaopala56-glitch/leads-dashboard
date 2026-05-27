# CODEX CLI BRIEF — MeNET Ops Dashboard

> **Zadanie:** Zaprojektuj, zdecyduj i zbuduj **MeNET Ops Dashboard** — unified frontend + backend dla lead management + leadpipe pipeline + self-evolving-core.
> **Kontekst:** Masz pełną swobodę decyzji architektonicznej. Nie szukam zgody — szukam gotowego kodu.
> **Odbiorca:** B B / MeNET — właściciel agencji, zna infrastrukturę, nie cierpi ogólników.
> **Język:** Kod + komentarze po angielsku. Docs po polsku.

---

## Infrastruktura (niezmienna)

### VM 1: hermes-agent (10.186.0.2)
- Hermes AI orchestrator (Telegram boty, profiile, gatewaye)
- Tutaj stoi Hermes Agent CLI + Codex CLI

### VM 2: mennet-deploy (10.186.0.4)
- Caddy reverse proxy + Authelia SSO
- 15+ domen DuckDNS (luxewor.duckdns.org i subdomeny)
- PM2, statyczne strony, kontenery Docker
- Porty zajęte: 80, 443, 3000-3002, 8080-8089, 9091 (Authelia)
- Obecnie: pusty placeholder `/home/hermes/dashboard/` na `leads.luxewor.duckdns.org`
- Webhook: POST `/api/leads` zapisuje do `leads.json`
- Auth: Authelia (admin, bartas + do dodania grupy: ceo, copywriter, ops)

### VM 3: sandbox-bot-v3 (10.186.0.3)
- **Self-Evolving Core (SEC):** Py UI dashboard na porcie 8765 (DZIAŁA, nie ruszać)
  - Supervisor, Event Bus, Meta-learning, Watchdogi
  - Archiwum: `/home/hermes/data/leads/vision_reports/` — 16K markdown YAML (STARY SYSTEM, nie ruszać)
- **Leadpipe (NOWY):** Repo `bozenaopala56-glitch/leadpipe`, Python
  - Postgres DB via SQLAlchemy (`db_schema.py`)
  - T0→T2 pipeline, Campaign Engine, Copywriter, CEO Queue/Auto-Decider
  - Rules: YAML w `leadpipe/rules/` (campaigns, gates, evidence, suppression, t2_eligibility)
  - Models: Pydantic (`models.py`), Engine: `engine.py`
- **Scraper (AKTYWNY):** `scrape_verify_save_v2.py --city Łódź` PID 853798
- **200+ skryptów pomocniczych:** `scripts/*.py` — cron, watchdogi, fixery (nie ruszać)

### Połączenie VPC
- mennet-deploy ←→ v3: internal VPC 10.186.0.x, bez proxy, porty dowolne
- Caddy na mennet-deploy może reverse proxy do `10.186.0.3:<port>`

---

## Systemy do zintegrowania

### System A: Leadpipe (NOWY, aktywny)
**Pipeline:** Scraper → GUS REGON check → T0 Scanner (~40-85 sygnały) → T0.5 Enrichment (NIP/VAT) → T1 Parser → Decision Gates → Campaign Engine → T2 Vision (Playwright + Kimi k2.5) → Copywriter Generator → Copywriter Reviewer → CEO Queue → CEO Auto-Decider → Outreach → Feedback Loop

**Campaigns (7):**
- REDESIGN_OUTDATED
- REDESIGN_ADS_WASTE
- REDESIGN_CONVERSION
- REDESIGN_TRUST
- WORDPRESS_REWORK
- MOBILE_REBUILD
- TECH_REBUILD

**Baza:** Postgres (SQLAlchemy async) — tabele: `leads`, `batches`, `scan_results`, `signals`, `evidence`, `campaign_decisions`, `decision_traces`, `outreach_events`, `suppression`

### System B: Lead Management (web forms)
- Webhook POST `/api/leads` na mennet-deploy → zapis do `leads.json`
- Źródła: main-hub, security, seo, ads, cloud, translations, labs, maintenance, prawnik-v1/v2
- Auth: Authelia SSO (Remote-User, Remote-Email, Remote-Groups headers)

### System C: Self-Evolving Core (ZOSTAJE, read-only integration)
- Port 8765 na v3, Py UI
- Event Bus: JSONL log
- Health Report: JSON co N minut
- **Read-only:** dashboard czyta health, statusy, eventy. Nie zapisuje do SEC.

---

## TWÓJ ZAKRES DECYZJI

Nie musisz pytać o zgodę. Zdecyduj samodzielnie:

### 1. Stack frontend
- **React + Vite + Tailwind + shadcn/ui** czy **HTMX + Alpine.js + Tailwind**?
- Uzasadnij: dla wewnętrznego panelu ops, 7 modułów, CRUD + pipeline state machine + wykresy.
- Uwaga: masz już `leads-dashboard` repo z React spec. Możesz użyć, zmienić lub zignorować.

### 2. Stack backend
- Cały backend na v3 jako **FastAPI** (Python) + Postgres leadpipe?
- Czy potrzebny jest jakiś backend na mennet-deploy (Express/SQLite dla web form)?
- Uzasadnij: czy lepiej jeden backend czy dwa (web forms na mennet-deploy, pipeline na v3)?

### 3. Web form leady
- Obecnie zapisują się do `leads.json`.
- Czy wrzucić je do leadpipe Postgres (tabela `leads` z `source: web_form`)?
- Czy zostawić osobno (SQLite na mennet-deploy) i tylko proxy do dashboard?
- Uzasadnij: unifikacja vs separation of concerns.

### 4. Moduły — kolejność implementacji
Zaproponuj kolejność (nie musisz zbudować wszystkich na raz):
- A: Leads CRM (web form leads list/detail)
- B: Pipeline T0→T2 (status, sygnały, campaigns)
- C: Scraper Ops (active scrapers, logs, start/stop)
- D: Copywriter Queue (drafts, review, approve)
- E: CEO Command Center (ATTACK/SKIP/MANUAL + auto-decider config)
- F: Outreach & Feedback (outbox, replies, suppression)
- G: Analytics (funnel, conversion by campaign)

### 5. Dane — co jak czytać
- Leadpipe Postgres: natywne SQLAlchemy models, async
- SEC Health: JSON file read
- Web form leads: czyli co? leadpipe Postgres czy osobna baza?
- Scraper status: process check (PID), log tail, discovered/verified counts

### 6. Auth
- Authelia SSO (Caddy forward auth) — dostajesz headers: Remote-User, Remote-Email, Remote-Groups
- Grupy: admin (wszystko), ceo (CEO + analytics), copywriter (D), ops (C + B), bartas (A only)
- Czy potrzebne API keys service-to-service (mennet-deploy ↔ v3)?

### 7. Deploy
- Gdzie stoi frontend? (mennet-deploy `/var/www/ops/` czy `/home/hermes/dashboard/`?)
- Gdzie stoi backend? (v3 port X, mennet-deploy port Y?)
- Caddy config: jakie hosty? `ops.luxewor.duckdns.org`? `leads.luxewor.duckdns.org`?

---

## WYMAGANIA FUNKCJONALNE (MVP Phase 1)

### Must-Have (Phase 1 — pierwszy deploy)
1. **Unified Lead Table** — wszystkie leady (web form + pipeline) w jednej tabeli
   - Columns: ID, Domain, Company, NIP, Source, Pipeline Status, Campaign, CEO Decision, Created
   - Sort, filter, paginate
   - Click → detail view

2. **Pipeline Status Board** — kanban-style lub timeline
   - T0 Queue → T1 Queue → Decision Gates → Campaign Assigned → T2 Queue → Copywriter → CEO Review
   - Count per stage
   - Click stage → filtered lead table

3. **CEO Decision Inbox** — lista leadów czekających na decyzję
   - Show: domain, company, T0 score, T1 signals, assigned campaign, confidence
   - Buttons: ATTACK / SKIP / MANUAL
   - Bulk select + bulk decide

4. **Scraper Status** — live status aktywnego scrapera
   - Process running? (PID check)
   - Last log lines (tail)
   - City, niche, discovered count, verified count
   - Start/Stop/Restart buttons (shell exec via API)

### Should-Have (Phase 2)
5. Lead detail: full timeline, signals, evidence, decision trace
6. Copywriter Queue: drafts inbox, preview, approve/reject
7. Outreach Outbox: sent/pending/replied counts
8. Analytics: funnel chart, campaign conversion rates

### Nice-to-Have (Phase 3)
9. Hermes Agent integration — auto-decisions from AI
10. Real-time WebSocket updates
11. Mobile responsive (table → cards)

---

## CONSTRAINTS (ABSOLUTNE — nie łamać)

1. **NIE RUSZAĆ** `self-evolving-core/scripts/` — 200+ skryptów, read-only
2. **NIE RUSZAĆ** aktywnego scrapera PID 853798
3. **NIE MIGROWAĆ** 16K markdown YAML z archiwum — to historia SEC, nie leadpipe
4. **NIE ZMIENIAĆ** leadpipe rules YAML bez testów (`pytest -q` musi przejść)
5. **NIE USUWAĆ** Authelia config na mennet-deploy bez backup
6. **NIE ZAJMOWAĆ** portów 3000-3002, 8080-8089, 9091 na mennet-deploy
7. Repo kodu: `bozenaopala56-glitch/leads-dashboard` (istnieje, masz push access)

---

## DOSTĘPNE ZASOBY

- **Postgres na v3:** leadpipe DB (schema w `leadpipe/db_schema.py`)
- **SQLite na mennet-deploy:** dowolny plik w `/home/hermes/`
- **Caddy:** możesz dodać hosta w `/etc/caddy/Caddyfile` (root only, wymaga `sudo caddy reload`)
- **Authelia:** grupy w `/opt/auth/config/users.yml` (root, restart docker `authelia`)
- **Python 3.11** na v3 i mennet-deploy
- **Node 20** na mennet-deploy (jeśli potrzebujesz)
- **Repo:** https://github.com/bozenaopala56-glitch/leads-dashboard

---

## FORMAT WYJŚCIA

1. **ARCH.md** — Twoja decyzja architektoniczna (stack, deploy, moduły, kolejność)
2. **Backend** — kompletny kod backendu (FastAPI/Express/whatever you chose)
3. **Frontend** — kompletny kod frontendu (React/HTMX/whatever you chose)
4. **Deploy guide** — jak postawić na mennet-deploy + v3 (krok po kroku)
5. **Caddy config snippet** — co dodać do Caddyfile
6. **Commit:** `feat: ops dashboard MVP` z konwencjonalnym commit message

---

## DECYZJA STARTOWA

Zaczynamy od **Phase 1** (Lead Table + Pipeline Board + CEO Inbox + Scraper Status).

Zdecyduj stack, zbuduj, commituj. Nie czekaj na zgodę.
