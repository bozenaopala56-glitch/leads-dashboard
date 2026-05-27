# leads-dashboard

Operacyjny panel webowy dla pipeline'u leadów B2B [leadpipe](https://github.com/bozenaopala56-glitch/leadpipe). Pokazuje wyniki skanowania T0/T0.5/T1, decyzje DecisionEngine i pozwala na QA override.

## Stack

- **Backend**: Python 3.11, FastAPI, Pydantic
- **Frontend**: Vanilla HTML/JS/CSS (dark mode, Swiss Brutalist)
- **Data**: `leadpipe` models + `.leadpipe/state.json`
- **Testy**: pytest (25 testów)

## Wymagania

- Python 3.11+
- [leadpipe](https://github.com/bozenaopala56-glitch/leadpipe) zainstalowany i dostępny w `PYTHONPATH`

## Szybki start

```bash
# 1. Klonuj repo
git clone https://github.com/bozenaopala56-glitch/leads-dashboard.git
cd leads-dashboard

# 2. Upewnij się że leadpipe jest w PYTHONPATH
export PYTHONPATH="../leadpipe:$PYTHONPATH"
# lub: pip install -e ../leadpipe

# 3. Stwórz venv i zainstaluj
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn python-multipart

# 4. Testy
cd dashboard
pytest -q

# 5. Uruchom backend
cd backend
LEADPIPE_ROOT=../leadpipe uvicorn app:app --reload --port 8092

# 6. Otwórz w przeglądarce
# http://127.0.0.1:8092/
```

## API Endpoints

| Method | Path | Opis |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/batches` | Lista batchy |
| POST | `/api/batches` | Import CSV |
| GET | `/api/leads` | Lista leadów |
| GET | `/api/leads/{id}` | Detail leada |
| GET | `/api/decisions` | Decyzje engine |
| POST | `/api/export` | Eksport CSV |
| POST | `/api/leads/{id}/override` | QA override |
| GET | `/api/rulesets` | Lista rulesetów YAML |

## Konfiguracja

| Zmienna | Domyślna | Opis |
|---|---|---|
| `LEADPIPE_ROOT` | `/tmp/leadpipe-t0` | Ścieżka do repo leadpipe (dla importów) |
| `LEADPIPE_STATE` | `.leadpipe/state.json` | Ścieżka do pliku stanu |
| `LEADPIPE_RULES` | (auto) | Ścieżka do rulesetów YAML |

## Dokumentacja

- [PLAN.md](docs/PLAN.md) — Plan implementacji Phase 1
- [TDD_PLAN.md](docs/TDD_PLAN.md) — Plan test-driven development
- [FUTURE_SCOPE.md](docs/FUTURE_SCOPE.md) — Phase 2 (Postgres, CX, CEO, T2, outreach)
- [VM_SETUP.md](docs/VM_SETUP.md) — Konfiguracja VM sandbox-bot-v3
- [AGENT_GUIDE.md](docs/AGENT_GUIDE.md) — Przewodnik dla przyszłych agentów

## Powiązane repo

- [leadpipe](https://github.com/bozenaopala56-glitch/leadpipe) — rdzeń pipeline'u (Python CLI)
