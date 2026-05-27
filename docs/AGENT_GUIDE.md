# AGENT_GUIDE.md — Przewodnik agenta implementującego leads-dashboard

> **Witaj agencie.** Ten dokument został napisany przez innego agenta (CodexLuxeworbot, deepseek-v4-flash) w ramach sesji 2026-05-27. Jest tu wszystko co musisz wiedzieć, żeby wdrożyć ten dashboard na swoim systemie.

---

## 1. Co to jest i po co

**leads-dashboard** to operacyjny panel webowy dla pipeline'u leadów MeNET (agencja webdev B Bozeny). Dashboard pokazuje wyniki skanowania stron WWW (T0/T0.5/T1), decyzje engine'u i pozwala na QA override.

### Dwa repo

| Repo | Co zawiera | URL |
|---|---|---|
| `leadpipe` | Rdzeń pipeline'u (Python, CLI, modele, engine, rulesety YAML) | `https://github.com/bozenaopala56-glitch/leadpipe` |
| `leads-dashboard` | Dashboard webowy (FastAPI backend + vanilla JS frontend) | `https://github.com/bozenaopala56-glitch/leads-dashboard` |

Dashboard jest **osobnym repo** ale **korzysta z kodu leadpipe** przez import modułów Python.

---

## 2. Struktura repo leads-dashboard

```
leads-dashboard/
├── SPEC.md                          # Specyfikacja biznesowa (co robi)
├── ARCHITEKTURA-UNIFIED.md          # Architektura integracji z leadpipe
├── CODEX-BRIEF.md                   # Brief dla Codex CLI
│
├── docs/
│   ├── ARCH.md                      # Architektura techniczna backendu
│   ├── PLAN.md                      # Plan implementacji Phase 1 (6 batchy)
│   ├── FUTURE_SCOPE.md              # Plan Phase 2 (Postgres, CX, CEO, T2, outreach)
│   ├── TDD_PLAN.md                  # Plan test-driven development
│   ├── VM_SETUP.md                  # Jak skonfigurować VM sandbox-bot-v3
│   └── AGENT_GUIDE.md               # TEN PLIK — dla Ciebie
│
└── dashboard/
    ├── backend/
    │   ├── app.py                   # FastAPI app, rejestracja routerów
    │   ├── deps.py                  # Dependency injection (state, auth)
    │   ├── routes/
    │   │   ├── health.py            # GET /api/health
    │   │   ├── batches.py           # GET/POST /api/batches (import CSV)
    │   │   ├── leads.py             # GET /api/leads, /api/leads/{id}
    │   │   ├── decisions.py         # GET /api/decisions
    │   │   ├── export.py            # POST /api/export
    │   │   ├── override.py          # POST /api/leads/{id}/override
    │   │   └── rulesets.py          # GET /api/rulesets
    │   └── services/
    │       ├── state_service.py     # Odczyt/zapis .leadpipe/state.json (file lock)
    │       └── pipeline.py          # Wrapper leadpipe CLI/modułów
    │
    ├── frontend/
    │   ├── index.html               # Główna strona (vanilla HTML)
    │   ├── app.js                   # Vanilla JS — fetch API, render tabel, filtry
    │   └── style.css                # Stylowanie (dark mode, Swiss Brutalist)
    │
    └── tests/
        ├── conftest.py              # Fixtures (client HTTP, temp state, sample lead)
        ├── test_health.py           # Test /api/health
        ├── test_batches.py          # Test importu batchy
        ├── test_leads.py            # Test listy i detail leadów
        ├── test_decisions.py        # Test decyzji
        ├── test_override.py         # Test QA override
        ├── test_rulesets.py         # Test rulesetów YAML
        └── test_state.py            # Test state.json (brak pliku, invalid JSON, lock)
```

---

## 3. Co jest już ZROBIONE

### Backend (Python, FastAPI)
- ✅ `app.py` — FastAPI z routerami, CORS, error handlers
- ✅ `deps.py` — dependency injection, ścieżka do state.json
- ✅ `state_service.py` — czytanie/zapis state.json z file lockiem (bezpieczne RMW)
- ✅ `pipeline.py` — wrapper importu CSV przez `leadpipe.cli.command_import`
- ✅ `health.py` — endpoint sprawdzający czy backend żyje
- ✅ `batches.py` — lista batchy, import CSV
- ✅ `leads.py` — lista leadów, detail leada z T0/T0.5/T1 sygnałami
- ✅ `decisions.py` — lista decyzji z DecisionEngine
- ✅ `export.py` — eksport do CSV
- ✅ `override.py` — QA override z audytem (nie nadpisuje oryginalnego trace)
- ✅ `rulesets.py` — lista plików YAML z rulesetami (chronione przed path traversal)

### Frontend (vanilla JS)
- ✅ `index.html` — layout z nawigacją, tabelami, panelami
- ✅ `app.js` — fetch `/api/*`, render przez DOM API (nie innerHTML), timeouty, obsługa błędów
- ✅ `style.css` — dark mode, Swiss Brutalist, data-dense

### Testy
- ✅ **25 testów**, wszystkie przechodzą (`pytest -q`)
- ✅ Testy: health, batches, leads, decisions, override, rulesets, state
- ✅ Edge cases: brak pliku, invalid JSON, symlink escape, race conditions

### Dokumentacja
- ✅ 8 plików markdown opisujących architekturę, plan, testy, Future Scope, VM setup

---

## 4. Co musisz ZROBIĆ (wdrożenie)

### Wymagania wstępne
1. **leadpipe** zainstalowany i działający (repo osobne)
2. Python 3.11+
3. `pip install fastapi uvicorn python-multipart`
4. `leadpipe` zainstalowane w tym samym venv co dashboard (lub w PYTHONPATH)

### Zmienne środowiskowe

| Zmienna | Domyślna | Opis |
|---|---|---|
| `LEADPIPE_ROOT` | `/tmp/leadpipe-t0` | Ścieżka do repo leadpipe (dodawana do sys.path) |
| `LEADPIPE_STATE` | `.leadpipe/state.json` | Ścieżka do pliku stanu JSON |
| `LEADPIPE_RULES` | (auto z pakietu) | Ścieżka do katalogu z rulesetami YAML |

### Kroki wdrożenia

```bash
# 1. Pobierz repo
git clone https://github.com/bozenaopala56-glitch/leads-dashboard.git
cd leads-dashboard

# 2. Stwórz venv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Zainstaluj dashboard
pip install -r requirements.txt  # lub ręcznie: fastapi uvicorn python-multipart

# 4. Upewnij się że leadpipe jest w PYTHONPATH
#    Jeśli leadpipe jest w ../leadpipe:
export PYTHONPATH="../leadpipe:$PYTHONPATH"
#    Lub zainstaluj leadpipe:
cd ../leadpipe && pip install -e . && cd ../leads-dashboard

# 5. Ustaw zmienną ze ścieżką do state.json
export LEADPIPE_STATE="/home/hermes/.leadpipe/state.json"

# 6. Uruchom testy
cd dashboard
pytest -q
# Oczekiwany wynik: 25 passed

# 7. Uruchom backend
cd backend
uvicorn app:app --host 127.0.0.1 --port 8092 --reload

# 8. Sprawdź w przeglądarce
# http://127.0.0.1:8092/ — frontend
# http://127.0.0.1:8092/api/health — API
```

### Produkcja (VM sandbox-bot-v3)

Szczegóły w `docs/VM_SETUP.md`. Skrót:
1. Skopiuj `leadpipe` na v3 (`gsutil cp gs://...` lub tarball)
2. Zainstaluj venv + leadpipe + dashboard
3. Uruchom backend jako systemd service
4. Skonfiguruj Caddy (reverse proxy + Authelia)
5. Frontend statyczny w `/var/www/ops`

---

## 5. Architektura w pigułce

```
User Browser
    |
    v
Caddy (reverse proxy + Authelia auth)
    |
    +-- /api/*  ->  FastAPI backend (port 8092)
    |                   |
    |                   +-- import modułów leadpipe
    |                   +-- czytanie .leadpipe/state.json
    |                   +-- wywoływanie CLI leadpipe
    |
    +-- /*        ->  Static files (frontend HTML/JS/CSS)
```

### Flow danych
1. Użytkownik importuje CSV przez UI → `POST /api/batches`
2. Backend wywołuje `leadpipe.cli.command_import()`
3. leadpipe zapisuje wyniki w `.leadpipe/state.json`
4. Użytkownik odświeża stronę → `GET /api/leads`
5. Backend czyta state.json przez `StateStore` (z file lock)
6. Frontend renderuje tabelę leadów z sygnałami T0/T0.5/T1

---

## 6. FAQ dla agenta

**Q: Czy mogę użyć React zamiast vanilla JS?**
A: W Phase 1 jest vanilla JS. W Phase 2 można przepisać na React/Vite — patrz `docs/FUTURE_SCOPE.md`.

**Q: Czy backend musi być FastAPI?**
A: FastAPI jest obecny i przetestowany. Można zmienić, ale trzeba przepisać testy.

**Q: Gdzie są rulesety?**
A: W repo `leadpipe` w katalogu `leadpipe/rules/`. Dashboard je tylko wyświetla (`GET /api/rulesets`).

**Q: Jak działa override decyzji?**
A: `POST /api/leads/{id}/override` zapisuje nową decyzję w state.json w polu `decision`, ale zachowuje oryginalny `trace` od DecisionEngine. Dzięki temu widać kto i dlaczego nadpisał.

**Q: Co jeśli state.json jest uszkodzony?**
A: `StateStore` obsługuje to gracefully — zwraca pusty stan i loguje błąd. Nie crashuje.

**Q: Czy można uruchomić bez leadpipe?**
A: Nie. Dashboard importuje moduły `leadpipe.models`, `leadpipe.cli`, `leadpipe.engine`. Bez leadpipe backend się nie uruchomi.

---

## 7. Gdzie szukać pomocy

| Pytanie o... | Gdzie szukać |
|---|---|
| Architekturę systemu | `docs/ARCH.md` |
| Plan implementacji | `docs/PLAN.md` |
| Testy (TDD) | `docs/TDD_PLAN.md` |
| Phase 2 (Postgres, CX, T2) | `docs/FUTURE_SCOPE.md` |
| Konfigurację VM | `docs/VM_SETUP.md` |
| Modele danych leadpipe | `leadpipe/leadpipe/models.py` |
| Rulesety YAML | `leadpipe/leadpipe/rules/*.yml` |
| DecisionEngine | `leadpipe/leadpipe/engine.py` |
| CLI leadpipe | `leadpipe/leadpipe/cli.py` |

---

## 8. Status — co działa, co nie

| Funkcja | Status | Uwagi |
|---|---|---|
| Import CSV | ✅ Działa | Przez `leadpipe.cli.command_import` |
| Skan T0/T0.5/T1 | ✅ Działa | Wywoływane przez leadpipe CLI |
| Decyzje engine | ✅ Działa | `DecisionEngine` z rulesetów YAML |
| Lista leadów | ✅ Działa | Z paginacją i filtrami |
| Detail leada | ✅ Działa | Z sygnałami T0/T0.5/T1 |
| Eksport CSV | ✅ Działa | `POST /api/export` |
| QA Override | ✅ Działa | Z audytem, bez nadpisywania trace |
| Ruleset browser | ✅ Działa | Read-only lista YAML |
| CEO Inbox | ❌ Nie ma | Phase 2 (Future Scope) |
| Postgres | ❌ Nie ma | Phase 2 (Future Scope) |
| CX Importer | ❌ Nie ma | Phase 2 (Future Scope) |
| T2 Vision | ❌ Nie ma | Phase 2 (Future Scope) |
| Outreach | ❌ Nie ma | Phase 2 (Future Scope) |

---

## 9. Komendy quick-reference

```bash
# Testy
cd dashboard && pytest -q

# Backend dev
cd dashboard/backend && uvicorn app:app --reload --port 8092

# Sprawdź czy leadpipe jest widoczne
python -c "import leadpipe; print(leadpipe.__file__)"

# Import testowy CSV
leadpipe import data/sample-batch.csv

# Sprawdź state.json
cat ~/.leadpipe/state.json | python -m json.tool | head -20
```

---

*Dokument napisany przez CodexLuxeworbot (deepseek-v4-flash, opencode-go) 2026-05-27. Jeśli coś jest niejasne — przeczytaj `docs/PLAN.md` i `docs/TDD_PLAN.md`.*
