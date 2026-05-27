# VM_SETUP.md — Konfiguracja sandbox-bot-v3

Dokument krok-po-kroku jak skonfigurować VM `sandbox-bot-v3` pod leadpipe + dashboard. **Wykonuj ręcznie lub przez skrypt ansible/shell — nie przez Codex CLI.**

---

## 1. Pobierz leadpipe

```bash
# Na v3 jako hermes
cd /home/hermes
gsutil cp gs://hermes-free-494708/leadpipe-v2.tar.gz .
tar xzf leadpipe-v2.tar.gz
mv leadpipe-t0 leadpipe
cd leadpipe
```

---

## 2. Python + venv

```bash
# Sprawdź czy Python 3.11 jest (startup script powinien był zainstalować)
python3.11 --version

# Jeśli nie ma:
sudo apt-get update -qq && sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip

# Stwórz venv
python3.11 -m venv /home/hermes/.venv/leadpipe
source /home/hermes/.venv/leadpipe/bin/activate

# Zainstaluj leadpipe
pip install -U pip
pip install -e ".[test,postgres,csv]"

# Test
pytest -q
```

---

## 3. Postgres (jeśli Phase 2 — Phase 1 działa na state.json)

### Instalacja (opcjonalnie dla Phase 1, wymagane dla Phase 2)

```bash
sudo apt-get install -y -qq postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Stwórz bazę i usera
sudo -u postgres psql <<'SQL'
CREATE DATABASE leadpipe;
CREATE USER leadpipe WITH PASSWORD 'tajne_haslo_zmien_to';
GRANT ALL PRIVILEGES ON DATABASE leadpipe TO leadpipe;
\c leadpipe
GRANT ALL ON SCHEMA public TO leadpipe;
SQL

# Zapisz URL w .env
echo "DATABASE_URL=postgresql+asyncpg://leadpipe:tajne_haslo_zmien_to@localhost/leadpipe" >> /home/hermes/.env
```

### Phase 1 (state.json)

Bez Postgres — leadpipe używa pliku `.leadpipe/state.json`.

```bash
mkdir -p ~/.leadpipe
```

---

## 4. leadpipe CLI — test

```bash
source /home/hermes/.venv/leadpipe/bin/activate
leadpipe --help
leadpipe import data/sample-batch.csv
leadpipe scan batch
leadpipe decide batch
```

---

## 5. Dashboard backend wrapper (Phase 1)

### Opcja A: FastAPI wrapper nad leadpipe

```bash
cd /home/hermes/leadpipe/dashboard

# Stwórz venv dla dashboardu
python3.11 -m venv /home/hermes/.venv/dashboard
source /home/hermes/.venv/dashboard/bin/activate
pip install fastapi uvicorn python-multipart

# Zamień backend.py na FastAPI wrapper
# (kod będzie dostarczony w osobnym batchu Codex CLI lub ręcznie)
```

### Opcja B: Prosty serwer plików (obecny)

```bash
cd /home/hermes/leadpipe/dashboard
python3 backend.py
# Słucha na 127.0.0.1:8080
```

---

## 6. Dashboard frontend (jeśli React/Vite)

```bash
# Jeśli frontend to React/Vite (Phase 2 lub jak zaimplementujesz)
cd /home/hermes/leads-dashboard/frontend
npm install
npm run build

# Build idzie do dist/
# Caddy serwuje dist/ jako static
```

---

## 7. Caddy reverse proxy

### Instalacja

```bash
sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -qq && sudo apt-get install -y -qq caddy
```

### Konfiguracja

```bash
sudo tee /etc/caddy/Caddyfile.d/ops.luxewor.duckdns.org <<'CADDY'
ops.luxewor.duckdns.org {
    # Authelia forward auth
    @auth {
        not path /auth /auth/*
    }
    forward_auth @auth localhost:9091 {
        uri /api/verify?rd=https://auth.luxewor.duckdns.org
        copy_headers Remote-User Remote-Email Remote-Groups
    }

    # API backend (dashboard wrapper)
    handle_path /api/* {
        reverse_proxy localhost:8092
    }

    # Static frontend
    handle {
        root * /var/www/ops
        try_files {path} /index.html
        file_server
    }
}
CADDY

sudo caddy reload
```

---

## 8. Authelia (jeśli jeszcze nie skonfigurowany)

```bash
# Sprawdź czy Authelia działa
sudo systemctl status authelia

# Jeśli nie ma:
# https://www.authelia.com/integration/prologue/getting-started/
```

---

## 9. Systemd services

### leadpipe-scraper (jeśli masz scraper na v3)

```bash
sudo tee /etc/systemd/system/leadpipe-scraper.service <<'SYSTEMD'
[Unit]
Description=Leadpipe Scraper
After=network.target

[Service]
Type=simple
User=hermes
WorkingDirectory=/home/hermes/leadpipe
Environment="PATH=/home/hermes/.venv/leadpipe/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/hermes/.venv/leadpipe/bin/python -m leadpipe.cli pipeline 10 --file data/sample-batch.csv
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
SYSTEMD

sudo systemctl daemon-reload
sudo systemctl enable leadpipe-scraper
# sudo systemctl start leadpipe-scraper  # uruchom jak będziesz gotowy
```

### dashboard-backend

```bash
sudo tee /etc/systemd/system/leads-dashboard.service <<'SYSTEMD'
[Unit]
Description=Leads Dashboard Backend
After=network.target

[Service]
Type=simple
User=hermes
WorkingDirectory=/home/hermes/leadpipe/dashboard
Environment="PATH=/home/hermes/.venv/dashboard/bin:/usr/local/bin:/usr/bin"
Environment="LEADPIPE_STATE=/home/hermes/.leadpipe/state.json"
ExecStart=/home/hermes/.venv/dashboard/bin/uvicorn backend:app --host 127.0.0.1 --port 8092
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

sudo systemctl daemon-reload
sudo systemctl enable leads-dashboard
```

---

## 10. Firewall / VPC

```bash
# Sprawdź czy v3 widzi mennet-deploy (Caddy + Authelia)
curl -I http://10.186.0.3:80 2>/dev/null || echo "mennet-deploy nieosiągalny"

# Jeśli v3 i mennet-deploy są w tej samej VPC, powinny się widzieć
# Jeśli nie, dodaj regułę firewall w GCP:
# gcloud compute firewall-rules create allow-v3-to-mennet --allow tcp:80,tcp:443 --source-tags=sandbox-bot-v3 --target-tags=mennet-deploy
```

---

## 11. Backup state.json

```bash
# Dodaj do crona
(crontab -l 2>/dev/null; echo "0 */6 * * * cp /home/hermes/.leadpipe/state.json /home/hermes/.leadpipe/state.json.\$(date +\%Y\%m\%d_\%H\%M).bak") | crontab -

# Lub backup na GCS
gsutil cp /home/hermes/.leadpipe/state.json gs://hermes-free-494708/backups/leadpipe-state-$(date +%Y%m%d_%H%M).json
```

---

## 12. Checklist uruchomienia

- [ ] leadpipe pobrany i rozpakowany
- [ ] venv stworzony i leadpipe zainstalowany
- [ ] `pytest -q` przechodzi
- [ ] `leadpipe --help` działa
- [ ] `.leadpipe/state.json` istnieje (lub Postgres skonfigurowany)
- [ ] Dashboard backend działa na 127.0.0.1:8092
- [ ] Caddy skonfigurowany i przekierowuje `/api/*` do backendu
- [ ] Authelia działa i ma grupy (admin, ceo, ops)
- [ ] Firewall VPC pozwala na komunikację między VMkami
- [ ] Systemd services włączone (jeszcze nie uruchomione, czekaj na "go")

---

## 13. Szybkie komendy (cheatsheet)

```bash
# Status
sudo systemctl status leads-dashboard
sudo systemctl status leadpipe-scraper
sudo journalctl -u leads-dashboard -f

# Restart
sudo systemctl restart leads-dashboard
sudo systemctl restart leadpipe-scraper

# Logi
sudo tail -f /var/log/caddy/access.log
tail -f /home/hermes/.leadpipe/state.json | jq .  # jeśli jq zainstalowany

# Test API
curl -H "Remote-User: test" http://localhost:8092/api/health
```

---

**Uwaga:** Ten dokument jest planem konfiguracji. Wykonaj go ręcznie na v3 lub przez skrypt shell, nie przez Codex CLI. Po zakończeniu konfiguracji możesz wrócić do Codex CLI żeby zaimplementować dashboard frontend/backend.
