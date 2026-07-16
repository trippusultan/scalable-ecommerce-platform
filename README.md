# Scalable E-Commerce Platform (Microservices)

A scalable e-commerce platform built with a **microservices architecture**, an
**API gateway**, **service discovery**, and a **React storefront** — fronted by
Firebase Hosting and backed by 7 FastAPI services on Render.

Solution to the roadmap.sh project:
**https://roadmap.sh/projects/scalable-ecommerce-platform**

> **Live demo:** https://aslustore.web.app  ·  backend: `https://aslu-backend.onrender.com`

## Architecture

```
                ┌────────────┐
   browser ───▶ │ Firebase   │  (static React SPA, aslustore.web.app)
                │ Hosting    │
                └─────┬──────┘
                      │  /api/*  ──▶  CORS + HTTPS to Render
                      ▼
                ┌────────────┐
   client ─────▶ │ API Gateway│  (port 8000, routes /api/<svc>/*, forwards JWT)
                └─────┬──────┘
        ┌────────────┼──────────────────────────────┐
        ▼            ▼            ▼                 ▼
 ┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────────┐
 │ User Svc │ │Product Svc│ │ Cart Svc │ ... │Notification Svc│
 └────┬─────┘ └────┬─────┘ └────┬─────┘     └──────┬───────┘
      │            │            │                   │
   own DB      own DB       own DB             own DB
      │            │            │                   │
      └────────────┴──── event bus (RabbitMQ) ──────┘
        │   service discovery (registry)  │
        └──────────▶  discovery-service  ◀── all services self-register + heartbeat

  Monitoring: every service exposes /metrics (Prometheus) → Grafana dashboards.
```

**Service discovery**: every service self-registers with `discovery-service` on
startup and sends heartbeats; the gateway (and any service) resolves peer URLs
via the registry. If the registry is down, it falls back to static `*_SERVICE_URL`
env values, so the platform still runs without it.

**Monitoring**: each service mounts a Prometheus `/metrics` endpoint (request
count, latency histogram, 5xx count). Prometheus scrapes them; Grafana visualizes.

## Storefront (React + Vite)

`frontend-react/` is a production React SPA (`BrowserRouter`, no SSR). It talks to
the backend **only through the gateway** (`VITE_API_BASE`); product images are
real photos served from a CDN with an inline-SVG line-art fallback, so the grid
never shows a broken image. The navbar collapses into a clean two-row layout on
mobile (brand + search on row 1, an evenly-aligned tab bar on row 2), and a small
global **error shield** (`src/ext-shield.js`) swallows uncaught errors injected by
third-party browser extensions so they never surface in visitors' consoles.

```bash
cd frontend-react
export PATH="/c/Program Files/nodejs:$PATH"        # Windows/MSYS
npm install
VITE_BASE=/ VITE_API_BASE=https://aslu-backend.onrender.com npm run build
# outputs ./dist  →  firebase deploy --only hosting
```

> Build note: the SPA must be built with `VITE_BASE=/` (root asset paths). Building
> with the default `base: "/ui/"` makes Firebase's SPA fallback serve `index.html`
> for JS/CSS requests, which breaks the bundle — keep `VITE_BASE=/`.

## Services

| Service            | Port | Responsibility                                        |
|--------------------|------|-------------------------------------------------------|
| `user-service`     | 8001 | Register / login / profile (JWT)                      |
| `product-service`  | 8002 | Products, categories, inventory reserve/release      |
| `cart-service`     | 8003 | Per-user cart, add/update/remove                     |
| `payment-service`  | 8004 | Charges (Stripe-ready; mock mode without keys)       |
| `order-service`    | 8005 | Orchestrator: cart → stock → payment → order         |
| `notification-service` | 8006 | Emails/SMS on events (SendGrid/Twilio-ready)     |
| `gateway`          | 8000 | Single entry point, reverse proxy + JWT forwarding   |

Each service has its **own database** (SQLite by default; per-service Postgres
in Docker) so they scale and deploy independently. The `order-service` is the
orchestrator: it calls the other services over HTTP, reserves inventory, charges
payment, writes the order, clears the cart, and emits `order.placed` /
`payment.completed` events that the Notification Service reacts to.

## Run locally (no Docker)

Requires Python 3.12.

```bash
cd ecommerce-platform
python -m venv .venv && .venv\\Scripts\\activate        # (bash: source .venv/Scripts/activate)
pip install -r requirements.txt
python scripts/run_local.py start     # boots all 7 services + seeds real sample data
python scripts/smoke.py               # guided end-to-end demo (checkout as alice)
python scripts/run_local.py stop      # shut down
```

On first boot the cluster seeds **real sample data** (3 users, 4 categories,
8 products) so the store is populated immediately. Seeding is idempotent — it
skips anything that already exists, so restarting is safe. To add your own data
instead, just call the API (e.g. `POST /api/products/products`) or edit
`scripts/seed.py`.

> **Troubleshooting — stale clusters:** `run_local.py start` now refuses to boot
> if any service port (8000–8006, 8009) is already in use. A previous cluster left
> running in the background will be silently reused by the tests and cause confusing
> failures (e.g. mismatched JWT secrets). If you see "ports are already in use",
> run `python scripts/run_local.py stop` first; `stop` also force-kills any orphaned
> processes still bound to those ports.

- Gateway:        http://127.0.0.1:8000  (returns a JSON map of routes at `/`)
- Health:         http://127.0.0.1:8000/health   (`?deep=1` for a live fan-out to every service; default returns a cached snapshot refreshed every 5s, so it's instant)
- Swagger UI per service: http://127.0.0.1:8001/docs … :8006/docs

## Run with Docker

```bash
cp .env.example .env        # edit JWT_SECRET + DB passwords before production
docker compose up --build
# Gateway: http://localhost:8000
```

Optional centralized logging (ELK):

```bash
docker compose --profile logging up --build   # Kibana at http://localhost:5601
```

Optional monitoring (Prometheus + Grafana):

```bash
docker compose --profile monitoring up --build
# Prometheus:  http://localhost:9090   (scrapes every service /metrics)
# Grafana:     http://localhost:3000   (admin/admin — add Prometheus data source)
```

### Service discovery & monitoring

- **Discovery**: `discovery-service` (port 8009) is a Consul-style registry. Each
  service `PUT /register`s on boot and `PUT /heartbeat`s every 15s. A background
  sweeper (and every lookup) marks entries that miss their heartbeat beyond
  `DISCOVERY_TTL` as `status: "down"`, so the registry reflects reality without
  manual cleanup. Inspect it: `GET http://localhost:8009/services`. The gateway
  resolves upstreams from the registry (falls back to static env URLs if the
  registry is unavailable).
- **Metrics**: every service and the gateway expose `GET /metrics` in Prometheus
  text format (request count, latency histogram, 5xx count). Prometheus scrapes
  them via `monitoring/prometheus.yml`; Grafana visualizes.

## Configuration (env vars, 12-factor)

| Var | Meaning |
|-----|---------|
| `SERVICE_NAME` | Service id (set automatically) |
| `DATABASE_URL` | SQLAlchemy DSN (sqlite path or postgresql://…) |
| `JWT_SECRET` | HMAC secret for tokens (shared across services). Must be **>= 32 bytes** in production — a weak secret prints a `[SECURITY WARNING]` at startup. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `PORT` | Listen port inside the container |
| `*_SERVICE_URL` | Base URLs for service-to-service calls |
| `EVENT_BUS` | `memory` (dev) or `rabbitmq` (docker) |
| `DISCOVERY_URL` | Registry base URL; when set, services self-register and the gateway resolves peers dynamically (else static `*_SERVICE_URL`) |
| `DISCOVERY_TTL` / `DISCOVERY_HEARTBEAT` | Registry entry expiry / heartbeat interval (seconds) |
| `STRIPE_API_KEY` / `SENDGRID_API_KEY` / `TWILIO_*` | Optional — without them the service runs in safe mock mode |
| `DEFAULT_NOTIFY_EMAIL` / `DEFAULT_NOTIFY_PHONE` | Fallback recipient when an event lacks the user's email |
| `VITE_API_BASE` | (frontend) Base URL of the gateway, e.g. `https://aslu-backend.onrender.com` |
| `VITE_BASE` | (frontend) Asset base path — must be `/` for Firebase Hosting |

## API quick reference (all via the gateway)

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/users/register` | none |
| POST | `/api/users/login` | none |
| GET  | `/api/products/products` | none |
| POST | `/api/products/products` | none |
| GET  | `/api/products/products?q=&category_id=&min_price=&max_price=` | none — search/filter |
| PATCH | `/api/products/products/{id}` | none — update fields |
| DELETE | `/api/products/products/{id}` | none — delete |
| GET  | `/api/cart/cart` | JWT |
| POST | `/api/cart/cart/items` | JWT |
| POST | `/api/orders/checkout` | JWT |
| GET  | `/api/orders/orders` | JWT |
| POST | `/api/payments/pay` | JWT |

## Tests

```bash
pip install pytest requests
pytest tests/ -q          # boots all 7 services and exercises the full flow
```

## Project layout

```
common/                 shared: config, db, JWT, logging, http client, event bus
user_service/  product_service/  cart_service/  payment_service/
order_service/ notification_service/  gateway/        one app each
scripts/               run_local.py (start/stop/status), smoke.py (demo)
tests/                 live integration tests
frontend-react/        React + Vite storefront (aslustore.web.app)
docker-compose.yml     full stack + RabbitMQ (+ optional ELK profile)
Dockerfile             multi-stage, parameterized by --build-arg SERVICE=…
render.yaml            Render web-service + worker specs for the 7 services
firebase.json          Firebase Hosting config for the React SPA
```

## License

MIT — see [LICENSE](./LICENSE).
