# Deploy — Aslu. (full stack)

Goal: backend on **Render**, frontend on **Firebase Hosting** (`aslu.web.app`).

Firebase Hosting is static-only, so the React SPA is hosted there and calls the
deployed gateway (on Render) directly via `VITE_API_BASE`.

## 1. Backend → Render

`render.yaml` defines 8 Web Services (discovery, user, product, cart, payment,
order, notification, gateway). Each builds the shared `Dockerfile` with the right
`SERVICE` build-arg and listens on `$PORT` (8000).

Render injects `RENDER_EXTERNAL_URL` per service. `common/service.py` maps that to
`PUBLIC_URL`, so each service registers its **real external URL** with the discovery
registry and peers can find each other across services.

Steps:
```
# a) create a secret group "ecom-secrets" in Render with:
#      JWT_SECRET = <32+ char random string>
# b) render login
render blueprint launch --yes     # or connect repo in dashboard (render.yaml present)
```
Optionally set `DATABASE_URL` per service (defaults to per-service SQLite on a volume).

## 2. Frontend → Firebase Hosting

`firebase.json` serves `frontend-react/dist` with an SPA rewrite to `index.html`.
The SPA calls the gateway at build time via `VITE_API_BASE`.

```
cd frontend-react
VITE_API_BASE=https://ecom-gateway.onrender.com npm run build
cd ..
firebase login            # must own the project that hosts aslu.web.app
firebase deploy --only hosting
```

No Firebase web config is needed — the app authenticates against the Render
backend (not Firebase Auth).

## 3. One-shot

```
bash deploy.sh            # backend + frontend
bash deploy.sh backend    # Render only
bash deploy.sh frontend   # Firebase only
```

## Notes / gotchas
- `aslu.web.app` must be a Hosting domain of the Firebase project you `firebase login` into.
- Change `.firebaserc` `projectId` to your real Firebase project.
- CORS: the gateway should allow the Firebase origin. Either deploy the gateway with
  `CORS_ORIGINS=https://aslu.web.app` (add to gateway env) or set it in `common/config.py`.
- SQLite on Render's ephemeral disk resets on deploys; for persistence use `DATABASE_URL`
  pointing at a managed Postgres (e.g. Render Postgres).
