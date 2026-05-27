# PLAN.md — Implementacja MeNET Ops Dashboard

## Overview

Plan rozbija Phase 1 MVP z `docs/ARCH.md` na małe zadania wykonywalne przez jednego developera w maksymalnie 8 godzin. Zakres Phase 1 obejmuje: backend FastAPI na `sandbox-bot-v3:8092`, statyczny frontend React/Vite na `mennet-deploy:/var/www/ops`, importer CX leadów do Postgresa Leadpipe, unified lead table, pipeline board, CEO inbox oraz bezpieczny scraper status/control.

Założenia:

- Testy powstają przed kodem dla każdego zadania.
- Dashboard czyta dane przez jeden backend FastAPI i jeden model API.
- CX webhook pozostaje kompatybilny i dalej zapisuje `leads.json`.
- Self-Evolving Core jest read-only.
- Scraper control nie przyjmuje dowolnych komend shell z UI.
- Każde zadanie wymaga testów: TAK.

## Batch 1: Foundation

### Zadania

#### T1: Szkielet backendu FastAPI

- Opis: Utworzenie struktury backendu, konfiguracji aplikacji FastAPI, endpointu health oraz podstawowej konfiguracji pytest. Zadanie nie implementuje jeszcze domeny leadów, tylko stabilny punkt startowy aplikacji.
- Input: `docs/ARCH.md`, decyzja o Python 3.11, FastAPI, pytest, pytest-asyncio.
- Output: Katalog backendu, aplikacja FastAPI, `GET /health`, konfiguracja testów backendowych.
- Czas: 4h.
- Testy: TAK.
- Co testować: testy jednostkowe i integracyjne API.
- Przypadki testowe:
  - Given uruchomiona aplikacja, when `GET /health`, then status HTTP 200 i `{"status":"ok"}`.
  - Given brak konfiguracji DB, when start testowej aplikacji, then health nadal działa bez inicjalizacji połączenia produkcyjnego.
- Komenda: `cd backend && pytest -q`.

#### T2: Konfiguracja backendu i env validation

- Opis: Dodanie Pydantic settings dla `DATABASE_URL`, `SERVICE_TOKEN`, `CX_WEBHOOK_URL`, ścieżek logów i parametrów scrapera. Konfiguracja ma jasno rozdzielać tryb testowy od produkcyjnego.
- Input: T1, lista zmiennych środowiskowych z `docs/ARCH.md`.
- Output: Moduł settings, walidacja wymaganych env, testowe ustawienia bez sekretów.
- Czas: 3h.
- Testy: TAK.
- Co testować: testy jednostkowe settings.
- Przypadki testowe:
  - Given brak `DATABASE_URL` w trybie produkcyjnym, when ładowanie settings, then walidacja zgłasza czytelny błąd.
  - Given `APP_ENV=test`, when ładowanie settings, then używane są bezpieczne wartości testowe.
  - Given `SERVICE_TOKEN` jest pusty w produkcji, when ładowanie settings, then aplikacja nie startuje.
- Komenda: `cd backend && pytest -q tests/test_settings.py`.

#### T3: Frontend scaffold React/Vite

- Opis: Utworzenie frontendu React 19 + TypeScript + Vite z routingiem, TanStack Query, Tailwind i podstawowym layoutem aplikacji operacyjnej. Zadanie dodaje tylko shell UI, bez ekranów domenowych.
- Input: `docs/ARCH.md`, stack frontendowy, wybrany host `/var/www/ops`.
- Output: Katalog frontendu, build Vite, test runner, puste trasy bazowe.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy komponentów i smoke build.
- Przypadki testowe:
  - Given aplikacja frontendowa, when render `/`, then widoczny jest shell dashboardu i nawigacja.
  - Given build produkcyjny, when `npm run build`, then powstaje poprawny bundle bez błędów TypeScript.
- Komenda: `cd frontend && npm test -- --run && npm run build`.

#### T4: Kontrakt API i typy współdzielone

- Opis: Zdefiniowanie kontraktów odpowiedzi API dla `UnifiedLeadRow`, paginacji, stage counts, CEO inbox i scraper status. Kontrakty mają być spójne między backendem i frontendem.
- Input: T1, T3, minimalny kontrakt z `docs/ARCH.md`.
- Output: Modele Pydantic w backendzie, typy TypeScript w frontendzie, przykładowe fixtures testowe.
- Czas: 4h.
- Testy: TAK.
- Co testować: testy serializacji backendu i testy typów frontendowych.
- Przypadki testowe:
  - Given model `UnifiedLeadRow`, when serializacja, then pola mają camelCase zgodne z kontraktem TS.
  - Given nieznany `pipelineStatus`, when walidacja, then request/fixture jest odrzucony.
  - Given pusty wynik listy, when serializacja paginacji, then `items=[]`, `total=0`.
- Komenda: `cd backend && pytest -q tests/test_contracts.py`; `cd frontend && npm test -- --run`.

### Cel batcha

Po Batch 1 repo ma działający szkielet backendu i frontendu, podstawową walidację konfiguracji oraz spójny kontrakt danych do dalszej implementacji.

## Batch 2: Backend Core

### Zadania

#### T5: DB session i read-only adapter Leadpipe

- Opis: Dodanie async SQLAlchemy session oraz adaptera do czytania istniejących tabel Leadpipe. Adapter nie wykonuje migracji historycznego archiwum i nie dotyka rules YAML.
- Input: T1, T2, schema Leadpipe z v3.
- Output: Moduł DB, dependency FastAPI, repozytorium read-only dla leadów pipeline.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy integracyjne z testową bazą Postgres lub SQLite-compatible mapping, plus jednostkowe mapowanie wyników.
- Przypadki testowe:
  - Given testowa baza z leadem i scan result, when repo pobiera lead, then zwraca scalone pola bez mutacji danych.
  - Given brak powiązanego `campaign_decisions`, when mapowanie, then `campaign=null`.
  - Given błąd połączenia DB, when request API, then backend zwraca kontrolowany błąd 503.
- Komenda: `cd backend && pytest -q tests/test_db.py tests/test_leadpipe_repo.py`.

#### T6: Auth headers i role guard

- Opis: Implementacja `GET /api/me`, odrzucania requestów bez `Remote-User` oraz sprawdzania ról z `Remote-Groups`. Dodanie obsługi `X-Service-Token` dla zadań service-to-service.
- Input: T1, T2, tabela ról z `docs/ARCH.md`.
- Output: Dependency auth, role guard, endpoint `/api/me`.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy integracyjne API i jednostkowe parsera grup.
- Przypadki testowe:
  - Given brak `Remote-User` i brak service token, when request `/api/me`, then HTTP 401.
  - Given `Remote-User` i `Remote-Groups=ceo,ops`, when request `/api/me`, then zwraca usera i grupy.
  - Given rola `bartas`, when request endpointu admin-only, then HTTP 403.
  - Given poprawny `X-Service-Token`, when request endpointu service-only, then request przechodzi bez user headers.
- Komenda: `cd backend && pytest -q tests/test_auth.py`.

#### T7: Alembic dla tabel dashboardowych

- Opis: Dodanie migracji tylko dla nowych tabel dashboardu: `lead_source_payloads` i ewentualny lekki audit operacji CEO/scraper, jeśli nie da się użyć istniejących tabel Leadpipe. Migracje nie zmieniają historycznego markdown archiwum.
- Input: T5, model danych z `docs/ARCH.md`.
- Output: Konfiguracja Alembic, migracja tworząca nowe tabele dashboardowe, test migracji.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy migracji i constraintów.
- Przypadki testowe:
  - Given pusta baza, when `alembic upgrade head`, then tabela `lead_source_payloads` istnieje.
  - Given dwa payloady z tym samym `source` i `external_id`, when insert, then unique constraint blokuje duplikat.
  - Given `alembic downgrade -1` w bazie testowej, when wykonanie, then tabela jest usunięta bez wpływu na mockowane tabele Leadpipe.
- Komenda: `cd backend && pytest -q tests/test_migrations.py`.

#### T8: Unified leads API

- Opis: Implementacja `GET /api/leads` z sortowaniem, filtrowaniem i paginacją oraz mapowaniem danych Leadpipe do `UnifiedLeadRow`. Endpoint ma obsłużyć brakujące dane powiązane bez wywalania całej listy.
- Input: T4, T5, T6.
- Output: `GET /api/leads`, repozytorium query, testy API.
- Czas: 7h.
- Testy: TAK.
- Co testować: testy integracyjne API, jednostkowe mapowania statusów.
- Przypadki testowe:
  - Given lead w T0 queue, when `GET /api/leads`, then `pipelineStatus=t0_queue`.
  - Given filtr `source=cx_bot`, when request, then zwracane są tylko leady CX.
  - Given sort `createdAt desc`, when request, then najnowszy lead jest pierwszy.
  - Given `pageSize` przekracza limit, when request, then backend ogranicza rozmiar strony.
- Komenda: `cd backend && pytest -q tests/test_leads_api.py`.

#### T9: Lead detail API

- Opis: Implementacja `GET /api/leads/{id}` z podstawowymi sekcjami detail view: identity, scan result, signals, evidence, campaign, decision traces i outreach status. To przygotowuje Phase 2 timeline, ale w Phase 1 zasila klik z tabeli.
- Input: T4, T5, T6, T8.
- Output: Endpoint detail leadu i model odpowiedzi.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy integracyjne API.
- Przypadki testowe:
  - Given istniejący lead z evidence, when request detail, then response zawiera evidence links.
  - Given lead bez signals, when request detail, then response zawiera pustą listę signals.
  - Given nieistniejący lead id, when request detail, then HTTP 404.
  - Given user bez uprawnień read, when request, then HTTP 403.
- Komenda: `cd backend && pytest -q tests/test_lead_detail_api.py`.

### Cel batcha

Po Batch 2 backend ma fundament produkcyjnego API: konfigurację, auth, DB access, migracje dashboardowe oraz unified lead list/detail.

## Batch 3: CX Importer

### Zadania

#### T10: Klient CX webhook API

- Opis: Implementacja klienta HTTP do `GET http://10.186.0.10:8091/api/leads` z timeoutami, retry dla błędów przejściowych i walidacją formatu CX. Klient nie zmienia istniejącego webhooka.
- Input: T2, format CX leadów z `docs/ARCH.md`.
- Output: Moduł klienta CX i modele walidacji.
- Czas: 4h.
- Testy: TAK.
- Co testować: testy jednostkowe z mockowanym httpx.
- Przypadki testowe:
  - Given poprawny payload CX, when fetch, then klient zwraca listę zwalidowanych leadów.
  - Given timeout, when fetch, then klient zgłasza kontrolowany błąd importu.
  - Given brak pola `timestamp`, when walidacja, then lead jest odrzucony albo oznaczony jako invalid zgodnie z decyzją implementacji.
- Komenda: `cd backend && pytest -q tests/test_cx_client.py`.

#### T11: Idempotentny upsert CX do Postgresa

- Opis: Mapowanie CX leadów do Leadpipe `leads` oraz zapis pełnego payloadu w `lead_source_payloads` z unikalnym `source/external_id`. Import nie kasuje i nie nadpisuje istniejących danych pipeline poza bezpiecznym uzupełnieniem pól źródłowych.
- Input: T7, T10, mapowanie CX fields z `docs/ARCH.md`.
- Output: Serwis importu CX, idempotentny upsert, metryki importu.
- Czas: 7h.
- Testy: TAK.
- Co testować: testy integracyjne DB i jednostkowe mapowania.
- Przypadki testowe:
  - Given ten sam lead CX importowany dwa razy, when import runs twice, then powstaje jeden rekord payloadu.
  - Given email i timestamp, when external id jest liczony, then jest stabilny między uruchomieniami.
  - Given brak company, when mapowanie, then `name` trafia do display/contact field zgodnie z kontraktem.
  - Given payload z `bantScore`, when import, then wartość jest zachowana w JSON metadata.
- Komenda: `cd backend && pytest -q tests/test_cx_importer.py`.

#### T12: Endpoint ręcznego importu CX

- Opis: Dodanie `POST /api/import/cx/run` dla admin/ops oraz service token. Endpoint uruchamia import synchronicznie lub jako kontrolowane zadanie i zwraca liczby: fetched, imported, skipped, failed.
- Input: T6, T10, T11.
- Output: Endpoint manual import, role guard, response summary.
- Czas: 4h.
- Testy: TAK.
- Co testować: testy integracyjne API i uprawnień.
- Przypadki testowe:
  - Given user `ops`, when request importu, then endpoint zwraca summary.
  - Given user `bartas`, when request importu, then HTTP 403.
  - Given poprawny service token, when request importu, then endpoint działa bez `Remote-User`.
  - Given błąd CX klienta, when request, then HTTP 502 i czytelny komunikat.
- Komenda: `cd backend && pytest -q tests/test_cx_import_api.py`.

### Cel batcha

Po Batch 3 CX leady z żywego webhooka mogą być bezpiecznie i idempotentnie kopiowane do Postgresa Leadpipe, a unified lead API widzi `source=cx_bot`.

## Batch 4: Pipeline i CEO API

### Zadania

#### T13: Pipeline stage counts API

- Opis: Implementacja `GET /api/pipeline/stages` zwracającego liczbę leadów w etapach: T0 Queue, T1 Queue, Decision Gates, Campaign Assigned, T2 Queue, Copywriter, CEO Review i Done. Logika statusu musi być współdzielona z `GET /api/leads`.
- Input: T8.
- Output: Endpoint stage counts i współdzielony mapper statusów.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy integracyjne API i jednostkowe status mappera.
- Przypadki testowe:
  - Given lead z campaign decision bez T2, when stage counts, then liczy się do `t2_queue`.
  - Given lead z CEO pending, when stage counts, then liczy się do `ceo_review`.
  - Given lead spoza pipeline, when stage counts, then nie zaburza etapów pipeline albo trafia do `not_in_pipeline`.
- Komenda: `cd backend && pytest -q tests/test_pipeline_stages_api.py`.

#### T14: CEO inbox API

- Opis: Implementacja `GET /api/ceo/inbox` z leadami oczekującymi decyzji oraz polami: domain, company, T0 score, T1 signals, campaign i confidence. Endpoint jest dostępny dla `admin` i `ceo`.
- Input: T5, T6, T13.
- Output: Endpoint CEO inbox z paginacją i filtrowaniem.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy integracyjne API i uprawnień.
- Przypadki testowe:
  - Given lead z `ceoDecision=pending`, when inbox request, then lead jest widoczny.
  - Given lead z decyzją `attack`, when inbox request, then lead nie jest widoczny.
  - Given user `ops`, when inbox request, then HTTP 403.
  - Given brak confidence, when response, then `confidence=null`, bez błędu.
- Komenda: `cd backend && pytest -q tests/test_ceo_inbox_api.py`.

#### T15: CEO decision write API

- Opis: Implementacja `POST /api/ceo/decisions` dla pojedynczej decyzji `ATTACK | SKIP | MANUAL`. Zapis ma trafiać do właściwej tabeli Leadpipe lub do dashboardowego audit/trace, zgodnie z istniejącym modelem.
- Input: T6, T14, schema decyzji Leadpipe.
- Output: Endpoint pojedynczej decyzji, walidacja payloadu, audit trace.
- Czas: 7h.
- Testy: TAK.
- Co testować: testy integracyjne API i transakcji DB.
- Przypadki testowe:
  - Given pending lead, when CEO posts `ATTACK`, then decyzja zapisuje się i lead znika z inboxa.
  - Given invalid decision `YES`, when request, then HTTP 422.
  - Given user `copywriter`, when request, then HTTP 403.
  - Given DB write fails, when request, then transakcja jest rollbackowana.
- Komenda: `cd backend && pytest -q tests/test_ceo_decision_api.py`.

#### T16: Bulk CEO decisions API

- Opis: Implementacja `POST /api/ceo/decisions/bulk` z częściowym raportem sukcesów i błędów. Endpoint musi unikać sytuacji, w której jeden błędny lead maskuje wynik całej operacji.
- Input: T15.
- Output: Endpoint bulk decisions, summary per lead.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy integracyjne API.
- Przypadki testowe:
  - Given trzy pending leady, when bulk `SKIP`, then wszystkie trzy mają decyzję `skip`.
  - Given jeden nieistniejący id, when bulk request, then response pokazuje jeden błąd i sukcesy pozostałych.
  - Given pusta lista ids, when request, then HTTP 422.
  - Given ponad limit ids, when request, then HTTP 413 albo 422 zgodnie z limitem.
- Komenda: `cd backend && pytest -q tests/test_ceo_bulk_api.py`.

### Cel batcha

Po Batch 4 backend obsługuje pipeline board i pełny przepływ decyzyjny CEO dla Phase 1.

## Batch 5: Scraper Ops API

### Zadania

#### T17: Scraper status read API

- Opis: Implementacja `GET /api/scraper/status` z odczytem PID, stanu procesu, miasta, niszy, liczników discovered/verified i ostatnich linii logu. Odczyt ma być odporny na brak pliku logu.
- Input: T2, T6, ścieżki logów i PID z `docs/ARCH.md`.
- Output: Endpoint scraper status i parser logów.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy jednostkowe parsera i integracyjne API.
- Przypadki testowe:
  - Given działający PID w mocku procesu, when status, then `running=true`.
  - Given brak log file, when status, then `logTail=[]` i brak HTTP 500.
  - Given log z discovered/verified lines, when parser, then liczniki są poprawnie wyciągnięte.
  - Given user `ceo`, when status request, then HTTP 403, bo scraper ops jest dla admin/ops.
- Komenda: `cd backend && pytest -q tests/test_scraper_status_api.py`.

#### T18: Scraper control allowlist

- Opis: Implementacja bezpiecznego wykonawcy komend start/stop/restart, który używa tylko predefiniowanych poleceń i blokuje dowolny input z UI. Stop/restart musi mieć ochronę przed przypadkowym ubiciem nieallowlistowanego PID.
- Input: T17, constraint o aktywnym scraperze PID 853798.
- Output: Moduł command runner z allowlistą, bez shell stringów z requestu.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy jednostkowe command runnera.
- Przypadki testowe:
  - Given akcja `start`, when runner, then wybierana jest predefiniowana komenda start.
  - Given akcja z requestu `rm -rf`, when walidacja, then akcja jest odrzucona.
  - Given PID niezgodny z allowlistą, when stop, then operacja jest zablokowana.
  - Given dry-run/test mode, when restart, then komenda nie jest wykonywana realnie.
- Komenda: `cd backend && pytest -q tests/test_scraper_control.py`.

#### T19: Scraper control endpoints

- Opis: Dodanie `POST /api/scraper/start`, `POST /api/scraper/stop`, `POST /api/scraper/restart` z role guard `admin/ops` i odpowiedzią audytowalną. Endpointy korzystają wyłącznie z modułu allowlisty.
- Input: T17, T18.
- Output: Endpointy control, response status, testy uprawnień.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy integracyjne API.
- Przypadki testowe:
  - Given user `ops`, when `POST /api/scraper/start`, then command runner jest wywołany.
  - Given user `bartas`, when `POST /api/scraper/stop`, then HTTP 403.
  - Given runner odrzuca PID, when restart, then HTTP 409 i proces nie jest ruszony.
  - Given runner success, when request, then response zawiera action, status i timestamp.
- Komenda: `cd backend && pytest -q tests/test_scraper_control_api.py`.

### Cel batcha

Po Batch 5 dashboard może pokazać status scrapera i wykonywać kontrolowane operacje ops bez ekspozycji dowolnego shella oraz bez niejawnego naruszania aktywnego procesu.

## Batch 6: Frontend Data Layer i Layout

### Zadania

#### T20: API client i query hooks

- Opis: Implementacja klienta `/api` w frontendzie oraz hooków TanStack Query dla me, leads, lead detail, pipeline stages, CEO inbox i scraper status. Warstwa ma obsługiwać loading, error i retry w kontrolowany sposób.
- Input: T3, T4, endpointy z Batch 2-5.
- Output: `apiClient`, hooki domenowe, testy mockowanych requestów.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy jednostkowe hooków z mock fetch/MSW.
- Przypadki testowe:
  - Given API zwraca 401, when hook `useMe`, then stan błędu jest dostępny dla UI.
  - Given leads response, when `useLeads`, then dane i paginacja są zmapowane.
  - Given scraper status refetch interval, when timer ticks, then hook odświeża dane.
- Komenda: `cd frontend && npm test -- --run src/hooks`.

#### T21: Layout, nav i role-aware visibility

- Opis: Implementacja głównego layoutu dashboardu, top baru z userem z `/api/me`, nawigacji do Leads, Pipeline, CEO Inbox i Scraper. Widoczność pozycji ma respektować role, ale backend pozostaje źródłem autoryzacji.
- Input: T20, role z `docs/ARCH.md`.
- Output: Layout aplikacji, role-aware nav, error boundary.
- Czas: 5h.
- Testy: TAK.
- Co testować: testy komponentów i routing.
- Przypadki testowe:
  - Given user `ops`, when render nav, then widzi Pipeline i Scraper.
  - Given user `bartas`, when render nav, then nie widzi CEO Inbox ani Scraper.
  - Given API `/api/me` error, when render, then layout pokazuje stan błędu bez crasha.
- Komenda: `cd frontend && npm test -- --run src/components src/App.test.tsx`.

### Cel batcha

Po Batch 6 frontend ma wspólną warstwę danych, routing i layout gotowy na ekrany domenowe.

## Batch 7: Frontend Phase 1 Screens

### Zadania

#### T22: Unified Lead Table UI

- Opis: Implementacja tabeli leadów z sortowaniem, filtrowaniem, paginacją i linkiem do detail view. Tabela ma być gęsta, operacyjna i zgodna z kontraktem `UnifiedLeadRow`.
- Input: T20, T21, `GET /api/leads`.
- Output: Ekran Leads, komponent tabeli, stan filtrów w URL.
- Czas: 7h.
- Testy: TAK.
- Co testować: testy komponentów i e2e smoke.
- Przypadki testowe:
  - Given lista leadów, when render, then widoczne są kolumny ID, Domain, Company, NIP, Source, Pipeline Status, Campaign, CEO Decision, Created.
  - Given filtr `source=cx_bot`, when user wybiera filtr, then hook dostaje query param `source=cx_bot`.
  - Given click w stage link/detail, when użytkownik klika lead, then routing przechodzi do `/leads/{id}`.
  - Given pusta lista, when render, then UI pokazuje stan empty bez błędu.
- Komenda: `cd frontend && npm test -- --run src/pages/LeadsPage.test.tsx && npm run test:e2e -- --grep "leads"`.

#### T23: Lead detail UI

- Opis: Implementacja podstawowego detail view dla kliknięcia z tabeli: identity, scan summary, signals, evidence, campaign, decision traces i outreach status. Zakres Phase 1 jest read-only.
- Input: T20, T21, `GET /api/leads/{id}`.
- Output: Ekran lead detail read-only.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy komponentów i e2e routing.
- Przypadki testowe:
  - Given lead z evidence, when render detail, then evidence jest widoczne jako linki.
  - Given lead bez signals, when render detail, then sekcja signals pokazuje pusty stan.
  - Given API 404, when render detail, then UI pokazuje not found.
- Komenda: `cd frontend && npm test -- --run src/pages/LeadDetailPage.test.tsx`.

#### T24: Pipeline Status Board UI

- Opis: Implementacja boardu etapów z count per stage i kliknięciem stage, które filtruje lead table po `pipelineStatus`. Board ma korzystać z `GET /api/pipeline/stages`.
- Input: T20, T21, T22, `GET /api/pipeline/stages`.
- Output: Ekran Pipeline Board i integracja z filtrem tabeli.
- Czas: 6h.
- Testy: TAK.
- Co testować: testy komponentów i routing.
- Przypadki testowe:
  - Given stage counts, when render, then każdy etap ma poprawny count.
  - Given click `CEO Review`, when user klika stage, then przechodzi do tabeli z filtrem `pipelineStatus=ceo_review`.
  - Given API error, when render, then board pokazuje stan błędu bez crasha.
- Komenda: `cd frontend && npm test -- --run src/pages/PipelinePage.test.tsx`.

#### T25: CEO Inbox UI

- Opis: Implementacja inboxa CEO z listą pending leadów, pojedynczą decyzją `ATTACK/SKIP/MANUAL` i bulk select + bulk decide. UI ma odświeżać inbox po udanej mutacji.
- Input: T20, T21, `GET /api/ceo/inbox`, `POST /api/ceo/decisions`, `POST /api/ceo/decisions/bulk`.
- Output: Ekran CEO Inbox, akcje single i bulk, stany loading/error.
- Czas: 8h.
- Testy: TAK.
- Co testować: testy komponentów, mutacji i e2e smoke.
- Przypadki testowe:
  - Given pending lead, when user klika `ATTACK`, then mutation wysyła poprawny payload.
  - Given kilka zaznaczonych leadów, when user wybiera bulk `SKIP`, then request zawiera listę ids.
  - Given mutation error, when backend zwraca 403, then UI pokazuje błąd i nie usuwa lokalnie leada.
  - Given mutation success, when response OK, then inbox jest refetchowany.
- Komenda: `cd frontend && npm test -- --run src/pages/CeoInboxPage.test.tsx && npm run test:e2e -- --grep "ceo"`.

#### T26: Scraper Status UI

- Opis: Implementacja widoku scraper ops z running status, PID, city, niche, discovered/verified counts, log tail i przyciskami start/stop/restart. Akcje destructive wymagają potwierdzenia w UI.
- Input: T20, T21, `GET /api/scraper/status`, scraper control endpoints.
- Output: Ekran Scraper Status i kontrolowane akcje ops.
- Czas: 7h.
- Testy: TAK.
- Co testować: testy komponentów i mutacji.
- Przypadki testowe:
  - Given `running=true`, when render, then PID i status są widoczne.
  - Given brak logów, when render, then log tail pokazuje empty state.
  - Given user klika stop, when brak potwierdzenia, then mutation nie jest wysłana.
  - Given potwierdzenie restart, when mutation success, then status jest refetchowany.
- Komenda: `cd frontend && npm test -- --run src/pages/ScraperPage.test.tsx`.

### Cel batcha

Po Batch 7 użytkownik ma komplet ekranów Phase 1 w frontendzie: lead table, detail, pipeline board, CEO inbox i scraper ops.

## Batch 8: Deploy, Observability i Dokumentacja

### Zadania

#### T27: Backend runtime packaging

- Opis: Przygotowanie komend uruchomieniowych backendu na v3, healthchecka, konfiguracji Uvicorn oraz przykładowego systemd/PM2 service file. Zadanie nie wdraża sekretów do repo.
- Input: T1-T19.
- Output: Skrypty/README runtime backendu, healthcheck, przykład service unit.
- Czas: 5h.
- Testy: TAK.
- Co testować: smoke test startu aplikacji i health endpoint.
- Przypadki testowe:
  - Given test env, when backend startuje przez komendę runtime, then `/health` odpowiada 200.
  - Given brak produkcyjnego sekretu, when test runtime, then używa test settings, a nie pustej produkcji.
- Komenda: `cd backend && pytest -q && uvicorn app.main:app --host 127.0.0.1 --port 8092`.

#### T28: Frontend production build i static hosting config

- Opis: Przygotowanie builda frontendu i instrukcji publikacji `dist/` do `/var/www/ops/`. Zadanie dodaje także weryfikację, że routing SPA działa przez `try_files`.
- Input: T3, T20-T26, Caddy snippet z `docs/ARCH.md`.
- Output: Build production, dokumentacja deploy frontendu, test smoke statycznego bundle.
- Czas: 4h.
- Testy: TAK.
- Co testować: build, preview i e2e smoke.
- Przypadki testowe:
  - Given production build, when `npm run build`, then brak błędów TypeScript.
  - Given preview server, when wejście na `/leads/some-id`, then SPA route renderuje aplikację.
  - Given `/api/*`, when Caddy config, then route nie jest obsługiwany przez static fallback.
- Komenda: `cd frontend && npm test -- --run && npm run build && npm run preview`.

#### T29: Caddy i Authelia deploy guide

- Opis: Spisanie finalnego deploy guide dla `ops.luxewor.duckdns.org`, Caddy reverse proxy `/api/*` do `10.186.0.3:8092` oraz forward auth Authelii. Instrukcja musi zawierać backup istniejącej konfiguracji przed reloadem.
- Input: `docs/ARCH.md`, T27, T28.
- Output: Dokumentacja deploy, finalny Caddy snippet, lista env vars.
- Czas: 3h.
- Testy: TAK.
- Co testować: testy dokumentacyjne/checklistowe oraz walidacja Caddy.
- Przypadki testowe:
  - Given Caddyfile z nowym hostem, when `caddy validate`, then konfiguracja jest poprawna.
  - Given request bez sesji, when wejście na host, then Authelia redirect działa.
  - Given request `/api/me` po auth, when Caddy proxy, then nagłówki `Remote-*` są przekazane.
- Komenda: `caddy validate --config /etc/caddy/Caddyfile`; `curl -I https://ops.luxewor.duckdns.org`.

#### T30: End-to-end acceptance suite

- Opis: Dodanie scenariuszy E2E dla podstawowej ścieżki operatora: wejście do aplikacji, tabela leadów, filtr stage, CEO decision i scraper status. Testy używają mockowanego API albo środowiska stagingowego.
- Input: T20-T29.
- Output: Playwright/Cypress suite, fixtures API, komenda CI.
- Czas: 8h.
- Testy: TAK.
- Co testować: e2e przepływy krytyczne.
- Przypadki testowe:
  - Given mock API z leadami pipeline i CX, when user otwiera dashboard, then tabela pokazuje oba źródła.
  - Given pipeline board, when user klika `CEO Review`, then tabela filtruje leady.
  - Given CEO inbox, when user wykonuje `MANUAL`, then lead znika z inboxa po refetchu.
  - Given scraper status running, when user otwiera Scraper, then widzi PID i log tail.
- Komenda: `cd frontend && npm run test:e2e`.

### Cel batcha

Po Batch 8 MVP ma instrukcje uruchomienia, pakowanie runtime, konfigurację ingress/auth oraz e2e acceptance suite dla krytycznych ścieżek.

## Self-Review & Poprawki

### Znalezione problemy

- Pierwotny podział mógłby zbyt wcześnie mieszać frontend z backendiem. Poprawka: pierwsze batche zamykają kontrakty i API, a frontend ekranów startuje dopiero po warstwie danych.
- CX importer jest ryzykowny, jeśli nie będzie idempotentny. Poprawka: osobne zadania T10-T12, unikalny `source/external_id`, test podwójnego importu i zachowanie pełnego payloadu.
- Scraper control może być niebezpieczny przy aktywnym PID 853798. Poprawka: rozdzielenie read-only statusu, allowlist command runnera i endpointów; testy blokują dowolne komendy oraz nieallowlistowany PID.
- CEO bulk decision mogłoby być za duże w jednym zadaniu z single decision. Poprawka: rozdzielenie T15 i T16, oba poniżej 8h.
- Lead detail mogło wypaść poza Phase 1, mimo że tabela wymaga click-through. Poprawka: dodany T9 i T23 jako read-only minimal detail.
- Auth mogło zostać potraktowane tylko na froncie. Poprawka: T6 wymusza backendową autoryzację, a T21 robi wyłącznie role-aware visibility jako UX.
- Deploy mógł pominąć walidację Caddy i Authelii. Poprawka: T29 zawiera backup, `caddy validate`, redirect Authelii i przekazywanie nagłówków.

### Poprawki wprowadzone

- Wszystkie taski mają estymatę maksymalnie 8h.
- Wszystkie taski mają `Testy: TAK`, typ testów, przypadki given/when/then i komendę uruchomienia.
- Batch ordering respektuje zależności: Foundation → Backend Core → CX Importer → Pipeline/CEO → Scraper → Frontend Data/Layout → Frontend Screens → Deploy/E2E.
- Edge cases dopisane do testów: brak powiązanych danych Leadpipe, brak nagłówków Authelii, role 403, puste listy, limity paginacji, brak logów scrapera, partial failure bulk decisions, timeout CX.
- Zakres Phase 1 nie mutuje SEC, nie migruje markdown/YAML i nie zmienia CX webhooka.

### Ryzyka pozostałe

- Rzeczywisty schema Leadpipe może różnić się od założeń w `docs/ARCH.md`; T5 i T15 powinny zacząć od krótkiego spike odczytu aktualnych modeli na v3.
- Testy integracyjne DB wymagają decyzji, czy użyć testowego Postgresa w CI, czy kontenera lokalnego.
- Uprawnienia Authelii zależą od faktycznych nazw grup w konfiguracji produkcyjnej; T29 musi zweryfikować je na deployu.
- Parser liczników scrapera zależy od realnego formatu logów; T17 powinien użyć próbek z aktualnego logu przed implementacją parsera.
