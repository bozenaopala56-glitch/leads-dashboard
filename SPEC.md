# Leads Dashboard — Codex Build Spec

## Overview
Build a production-ready **Leads Management Dashboard** for MeNET agency. Deployed at `https://leads.luxewor.duckdns.org` behind Caddy + Authelia SSO.

## Stack
- **React 19** + **TypeScript**
- **Vite** (build tool)
- **Tailwind CSS v4** (styling)
- **shadcn/ui** (components)
- **TanStack Table** (data grid)
- **Recharts** (charts)
- **React Router v7** (routing)

## Design Direction
- **Dark mode default** — matches MeNET brand (#0a0a0a bg, #e0e0e0 text)
- **Swiss Brutalist** influence — clean grids, sharp borders, monospace accents
- **No gradients, no blur** — flat, high contrast
- **Data-dense** — table-first layout, minimal whitespace waste

## Pages & Routes

### `/` — Leads List (default)
- TanStack Table with sorting/filtering/pagination
- Columns: ID | Name | Email | Phone | Source | Status | Created | Actions
- Bulk actions: select rows → change status / export / delete
- Filters: status dropdown, date range, source search
- Add Lead button → opens modal

### `/lead/:id` — Lead Detail
- Timeline of interactions (calls, emails, notes)
- Edit form (name, email, phone, status, notes, tags)
- Delete button with confirmation

### `/stats` — Analytics
- Recharts: leads per day (line chart), leads by source (bar), conversion funnel
- Date range picker
- Export to CSV

## API Integration
Base URL: `/api` (proxied by Caddy to `localhost:8091`)

Endpoints (webhook already exists on mennet-deploy):
- `GET /api/leads` — list all
- `GET /api/leads/:id` — single lead
- `POST /api/leads` — create
- `PUT /api/leads/:id` — update
- `DELETE /api/leads/:id` — delete
- `GET /api/stats` — analytics data

## Auth
- **Authelia** handles SSO — dashboard receives `Remote-User`, `Remote-Email`, `Remote-Groups` headers
- No own login page — if not authenticated, Caddy redirects to Authelia
- Show user name from header in top bar

## File Structure
```
src/
  components/
    ui/           # shadcn components
    layout/       # Sidebar, TopBar, PageContainer
    leads/        # LeadTable, LeadForm, LeadModal
    stats/        # Charts, DateRangePicker
  pages/
    LeadsPage.tsx
    LeadDetailPage.tsx
    StatsPage.tsx
  hooks/
    useLeads.ts
    useStats.ts
  lib/
    api.ts        # axios/fetch wrapper
    utils.ts
  types/
    lead.ts
  App.tsx
  main.tsx
```

## Build & Deploy
```bash
npm install
npm run build
# Output: dist/ → copy to /home/hermes/dashboard on mennet-deploy
```

## Constraints
- **NO placeholders** — every component must be functional
- **NO AI-typo lorem ipsum** — real labels, real data
- Mobile responsive (sidebar collapses to hamburger)
- Loading states for all async ops
- Error boundaries + toast notifications

## Deliverables
1. Complete repo with working code
2. `README.md` with setup + deploy instructions
3. Build artifact ready to copy to mennet-deploy
