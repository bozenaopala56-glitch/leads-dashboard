# MeNET Ops Dashboard - decyzja architektoniczna

Data decyzji: 2026-05-27  
Repo: `bozenaopala56-glitch/leads-dashboard`  
Zakres: Phase 1 MVP dla unified lead table, pipeline board, CEO inbox i scraper status.

## 1. Decyzja w skrócie

MeNET Ops Dashboard będzie aplikacją frontendową React/Vite hostowaną statycznie na `mennet-deploy` i jednym backendem FastAPI uruchomionym na `sandbox-bot-v3` obok Leadpipe.

Publiczny ruch idzie przez Caddy + Authelia na `mennet-deploy`. Caddy serwuje frontend z `/var/www/ops/` i reverse proxy kieruje `/api/*` do backendu FastAPI na `10.186.0.3:8092`.

CX webhook zostaje żywym systemem na `mennet-deploy:8091` i nadal zapisuje do `/home/hermes/cx-webhook/leads.json`. Nie zmieniamy jego publicznych endpointów. Dla unifikacji danych dodajemy osobny importer/sync job, który czyta `GET http://10.186.0.10:8091/api/leads` i zapisuje kopię CX leadów do Postgresa Leadpipe na v3 jako `source = 'cx_bot'`. Dashboard czyta tylko z backendu FastAPI i Postgresa, dzięki czemu UI ma jedną tabelę i jeden model danych.

## 2. Infrastruktura docelowa

| Host | Rola w dashboardzie | Decyzja |
|---|---|---|
| `hermes-agent` `10.186.0.2` | Delegacja Codex CLI | Bez usług dashboardu. Nic nie stoi tu na stałe. |
| `mennet-deploy` `10.186.0.10` | Publiczny ingress, auth, statyczny frontend | Caddy + Authelia + pliki `/var/www/ops/`. Bez nowego backendu aplikacyjnego. |
| `sandbox-bot-v3` `10.186.0.3` | Dane i operacje Leadpipe | FastAPI backend na porcie `8092`, Postgres Leadpipe, read-only SEC, scraper control. |

Port `8092` jest świadomie wybrany dla v3. Ograniczenie portów zajętych dotyczy `mennet-deploy`, a nie v3. Na `mennet-deploy` nie zajmujemy `3000-3002`, `8080-8089`, `8091` ani `9091`.

Publiczny host: `ops.luxewor.duckdns.org`.

`leads.luxewor.duckdns.org` może pozostać dla starszego lead CRM albo przekierować do `ops.luxewor.duckdns.org/leads` po wdrożeniu, ale nie jest głównym hostem nowego dashboardu.

## 3. Stack frontend

Wybrany stack:

- React 19
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query
- TanStack Table
- React Router
- React Hook Form + Zod
- Recharts
- lucide-react

Uzasadnienie:

React + Vite jest najlepszym wyborem dla tego dashboardu, bo Phase 1 wymaga gęstych tabel, filtrowania, paginacji, widoków szczegółowych, bulk actions i stanu klienta dla CEO inbox. TanStack Table i Query rozwiązują większość trudnych elementów bez pisania własnej infrastruktury UI.

HTMX/Alpine byłby prostszy dla formularzy i statycznych list, ale tutaj szybko pojawią się zależne widoki, odświeżanie statusów, zaznaczanie wielu rekordów, filtrowanie stage board -> table i edycje decyzji CEO. To jest aplikacja operacyjna, nie klasyczny server-rendered CRUD.

shadcn/ui daje kontrolę nad komponentami i nie narzuca ciężkiego runtime. Tailwind pozwala utrzymać spójny, data-dense interfejs bez budowania własnego design systemu od zera.

## 4. Stack backend

Wybrany stack:

- Python 3.11
- FastAPI
- Uvicorn
- SQLAlchemy async
- asyncpg
- Pydantic v2
- Alembic tylko dla nowych tabel dashboardu, bez migracji historycznego markdown archiwum
- httpx
- structlog albo standardowy `logging`
- pytest + pytest-asyncio

Backend stoi na `sandbox-bot-v3`, obok Leadpipe.

Uzasadnienie:

Leadpipe jest Pythonowy, używa Pydantic, SQLAlchemy async i Postgresa. Backend dashboardu musi czytać natywne modele/tabele Leadpipe oraz wykonywać operacje na CEO decisions, campaign decisions, traces i scraper status. Trzymanie API na v3 usuwa potrzebę zdalnego dostępu do Postgresa z `mennet-deploy` i ogranicza liczbę połączeń między VM.

Nie stawiamy Expressa na `mennet-deploy`, bo rozbiłoby to logikę na dwa backendy i wymusiło proxy/gateway dla operacji, które i tak muszą skończyć w Leadpipe. `mennet-deploy` zostaje prostym, twardym ingress layer: Caddy, Authelia, statyczne pliki.

## 5. Decyzja dla CX webhook leadów

Wybrane rozwiązanie: D) kompatybilny importer CX -> Postgres.

Nie wybieramy A jako pierwszy krok, czyli nie zmieniamy `cx-webhook/server.js`, żeby od razu pisał do Postgresa. CX webhook jest żywy, Dialogflow CX zależy od jego endpointów i formatu. Zmiana ścieżki zapisu w Phase 1 zwiększa ryzyko awarii lead capture.

Nie wybieramy B, czyli czytania `leads.json` przez NFS/SSH z v3. To tworzy słabe sprzężenie między maszynami, zależność od ścieżek plików i uprawnień oraz trudny model awarii.

Nie wybieramy C w UI, czyli dwóch requestów z dashboardu. To przerzuca unifikację danych do frontendu, komplikuje filtrowanie, sortowanie, paginację i uprawnienia. Unified Lead Table ma być naprawdę unified, więc API musi zwracać jeden model.

Docelowy flow:

1. Dialogflow CX wysyła lead do `POST http://10.186.0.10:8091/webhook`.
2. CX webhook zapisuje jak dziś do `/home/hermes/cx-webhook/leads.json`.
3. Backend FastAPI na v3 cyklicznie pobiera `GET http://10.186.0.10:8091/api/leads` przez VPC.
4. Importer upsertuje rekordy do Postgresa Leadpipe z `source = 'cx_bot'` i stabilnym `external_id`.
5. Dashboard czyta `/api/leads`, które zwraca dane z Postgresa.

W Phase 2 można dodać dual-write w CX webhooku do nowego endpointu FastAPI, ale tylko jako kompatybilne rozszerzenie. `leads.json` i obecne endpointy zostają.

## 6. Model danych

Dashboard nie migruje 16K markdown YAML z archiwum Self-Evolving Core. Źródłem prawdy dla nowej aplikacji jest Postgres Leadpipe oraz read-only endpointy/pliki istniejących systemów.

### Unified lead view

Backend wystawia `GET /api/leads` jako widok logiczny, zasilany z tabel Leadpipe:

- `leads` - identity, domain/company/NIP/contact/source/created
- `scan_results` - T0 score i status skanowania
- `signals` - T1 signals i agregaty
- `evidence` - linki i dowody dla detail view
- `campaign_decisions` - przypisana kampania, confidence
- `decision_traces` - uzasadnienia bramek i CEO/autodecider
- `outreach_events` - stan outreach
- `suppression` - skip/suppression reasons

Minimalny kontrakt odpowiedzi dla tabeli:

```ts
type UnifiedLeadRow = {
  id: string;
  domain: string | null;
  company: string | null;
  nip: string | null;
  source: "cx_bot" | "pipeline";
  pipelineStatus:
    | "t0_queue"
    | "t1_queue"
    | "decision_gates"
    | "campaign_assigned"
    | "t2_queue"
    | "copywriter"
    | "ceo_review"
    | "done"
    | "not_in_pipeline";
  campaign: string | null;
  ceoDecision: "attack" | "skip" | "manual" | "pending" | null;
  createdAt: string;
};
```

### CX import fields

CX lead format:

```json
{
  "timestamp": "...",
  "name": "...",
  "email": "...",
  "phone": "...",
  "service": "...",
  "bantScore": 0,
  "persona": "...",
  "need": "...",
  "budget": "...",
  "timeline": "...",
  "authority": "..."
}
```

Mapowanie:

| CX field | Postgres/dashboard field |
|---|---|
| `timestamp` | `created_at`, part of `external_id` fallback |
| `name` | `company` or contact display name when company unknown |
| `email` | contact email |
| `phone` | contact phone |
| `service` | source detail / requested service |
| `bantScore` | CX qualification metadata |
| `persona`, `need`, `budget`, `timeline`, `authority` | JSON metadata attached to lead |

Jeśli Leadpipe `leads` nie ma miejsca na CX metadata, dodajemy małą tabelę dashboardową `lead_source_payloads`:

```sql
lead_source_payloads(
  id uuid primary key,
  lead_id uuid not null,
  source text not null,
  external_id text not null,
  payload jsonb not null,
  imported_at timestamptz not null,
  unique(source, external_id)
)
```

Ta tabela nie zmienia reguł Leadpipe i nie dotyka YAML rules.

## 7. API backendu

Phase 1 endpointy:

- `GET /api/me` - użytkownik z nagłówków Authelia
- `GET /api/leads` - sort/filter/paginate
- `GET /api/leads/{id}` - detail view
- `GET /api/pipeline/stages` - counts per stage
- `GET /api/ceo/inbox` - leady czekające na decyzję
- `POST /api/ceo/decisions` - single decision `ATTACK | SKIP | MANUAL`
- `POST /api/ceo/decisions/bulk` - bulk decision
- `GET /api/scraper/status` - PID, running, city, niche, counts, log tail
- `POST /api/scraper/start`
- `POST /api/scraper/stop`
- `POST /api/scraper/restart`
- `POST /api/import/cx/run` - ręczne uruchomienie importu, admin/ops only

Scraper control musi być jawnie ograniczony. Phase 1 status może pokazywać aktywny PID `853798`, ale przyciski Stop/Restart nie mogą przypadkowo ubić tego procesu bez świadomej autoryzacji i allowlisty komend. Backend ma wykonywać tylko przygotowane komendy, bez przyjmowania shell stringów z UI.

## 8. Auth i autoryzacja

Authelia zostaje jedynym loginem użytkownika. Caddy chroni host `ops.luxewor.duckdns.org` i przekazuje do backendu:

- `Remote-User`
- `Remote-Email`
- `Remote-Groups`

Backend FastAPI ufa tym nagłówkom tylko dlatego, że port `8092` nie jest publicznie wystawiony i ruch przychodzi przez Caddy z VPC. Dodatkowo backend powinien odrzucać requesty bez `Remote-User`.

Role:

| Grupa | Uprawnienia |
|---|---|
| `admin` | Wszystko, w tym import CX i operacje serwisowe |
| `ceo` | CEO inbox, decyzje, analytics, lead detail |
| `copywriter` | Copywriter queue i lead detail potrzebny do pracy |
| `ops` | Scraper status/control, pipeline board, lead table |
| `bartas` | Lead table i lead detail read-only |

Service-to-service API key jest potrzebny dla operacji bez użytkownika:

- CX importer wywoływany przez scheduler
- ewentualny przyszły dual-write z CX webhooka do v3
- health checks bez sesji Authelia

Nagłówek: `X-Service-Token`. Token trzymany jako env var po obu stronach, bez commitowania do repo.

## 9. Integracja Self-Evolving Core

Self-Evolving Core na `10.186.0.3:8765` jest read-only dla nowego dashboardu.

Dashboard Phase 1 nie wywołuje mutacji SEC i nie dotyka `self-evolving-core/scripts/`. Dozwolone są tylko:

- odczyt health report JSON, jeśli istnieje stabilna ścieżka
- odczyt Event Bus JSONL jako read-only
- link out do starego dashboardu SEC dla admina/ops

Nie migrujemy historycznego markdown/YAML archiwum.

## 10. Caddy config snippet

Do dodania na `mennet-deploy` w Caddyfile:

```caddyfile
ops.luxewor.duckdns.org {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.luxewor.duckdns.org/
        copy_headers Remote-User Remote-Email Remote-Groups
    }

    root * /var/www/ops
    encode gzip zstd

    handle /api/* {
        reverse_proxy 10.186.0.3:8092 {
            header_up Remote-User {http.request.header.Remote-User}
            header_up Remote-Email {http.request.header.Remote-Email}
            header_up Remote-Groups {http.request.header.Remote-Groups}
            header_up X-Forwarded-Host {host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    handle {
        try_files {path} /index.html
        file_server
    }
}
```

Jeśli obecna konfiguracja Authelii używa innej nazwy upstreamu niż `authelia:9091`, należy zachować lokalny wzorzec z istniejącego Caddyfile. Nie usuwać obecnej konfiguracji Authelia bez backupu.

## 11. Deploy plan

1. Przygotować backend FastAPI w repo dashboardu albo jako osobny katalog aplikacyjny na v3.
2. Skonfigurować env na v3:
   - `DATABASE_URL` do Postgresa Leadpipe
   - `CX_WEBHOOK_URL=http://10.186.0.10:8091/api/leads`
   - `SERVICE_TOKEN`
   - ścieżki read-only do logów scrapera i health SEC
3. Uruchomić backend na v3 pod `127.0.0.1:8092` albo `10.186.0.3:8092` przez PM2/systemd.
4. Dodać importer CX jako scheduler albo endpoint uruchamiany przez cron/systemd timer. Importer robi upsert, nie kasuje danych.
5. Zbudować frontend:
   - `npm ci`
   - `npm run build`
6. Skopiować `dist/` na `mennet-deploy:/var/www/ops/`.
7. Dodać Caddy snippet dla `ops.luxewor.duckdns.org`.
8. Przeładować Caddy dozwolonym sudo reloadem.
9. Zweryfikować:
   - Authelia redirect działa
   - `/api/me` zwraca usera i grupy
   - Unified Lead Table pokazuje pipeline + CX leady po imporcie
   - CEO decyzja zapisuje się w Postgresie
   - Scraper status pokazuje PID i log tail bez restartowania aktywnego procesu

## 12. Kolejność implementacji modułów

Phase 1:

1. Backend foundation: auth headers, DB session, role guard, unified lead query.
2. CX importer: `GET /api/leads` z webhooka -> idempotentny upsert do Postgresa.
3. Unified Lead Table: sort, filter, paginate, detail link.
4. Pipeline Status Board: stage counts, click stage -> filtered lead table.
5. CEO Decision Inbox: single i bulk `ATTACK/SKIP/MANUAL`, zapis decision trace.
6. Scraper Status: running check, PID, last log lines, counts; start/stop/restart za allowlistą.

Phase 2:

1. Lead detail timeline: scan results, signals, evidence, decision traces.
2. Copywriter Queue: drafts, preview, approve/reject.
3. Outreach Outbox: pending/sent/replied, suppression visibility.
4. Analytics: funnel i campaign conversion.

Phase 3:

1. Real-time updates przez WebSocket/SSE.
2. Hermes Agent integration dla wspomagania decyzji.
3. Zaawansowany audit log operacji użytkowników.
4. Mobile table-to-cards dla operacji terenowych.

## 13. Granice bezpieczeństwa

Tych rzeczy dashboard nie robi:

- Nie dotyka `self-evolving-core/scripts/`.
- Nie zatrzymuje aktywnego scrapera PID `853798` podczas wdrożenia.
- Nie migruje 16K markdown YAML.
- Nie zmienia Leadpipe rules YAML bez testów `pytest -q`.
- Nie usuwa ani nie nadpisuje konfiguracji Authelia.
- Nie zmienia endpointów CX webhooka bez backward compatibility.
- Nie wystawia Postgresa publicznie.
- Nie przyjmuje dowolnych komend shell z UI.

## 14. Decyzja końcowa

Architektura Phase 1 to:

```text
Browser
  -> ops.luxewor.duckdns.org
  -> Caddy + Authelia on mennet-deploy
  -> static React app from /var/www/ops
  -> /api/* reverse_proxy to 10.186.0.3:8092
  -> FastAPI on sandbox-bot-v3
  -> Leadpipe Postgres + read-only SEC + controlled scraper ops

CX Dialogflow
  -> existing cx-webhook on mennet-deploy:8091
  -> existing leads.json
  -> FastAPI CX importer over VPC
  -> Leadpipe Postgres unified source
```

To utrzymuje żywe systemy bez ryzykownych zmian, daje dashboardowi jeden backend i jeden model danych, a logikę operacyjną trzyma przy Leadpipe, czyli tam, gdzie są dane i procesy.
