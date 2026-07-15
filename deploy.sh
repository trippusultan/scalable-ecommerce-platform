#!/usr/bin/env bash
# Full deploy script for the Aslu. platform.
#   Backend  -> Render (render.yaml, 8 services)
#   Frontend -> Firebase Hosting (aslu.web.app)
#
# PREREQUISITES (you must provide these — they are NOT in the repo):
#   1. Render CLI logged in:        render login        (or set RENDER_API_KEY)
#   2. A "ecom-secrets" secret group in Render containing JWT_SECRET (32+ chars)
#   3. Firebase CLI logged in:      firebase login       (or set FIREBASE_TOKEN)
#   4. .firebaserc projectId set to your Firebase project
#   5. firebaseConfig (from Firebase console) — only needed in the browser at runtime
#      if you want auth against Firebase; here the app uses the Render backend for auth,
#      so Firebase config is NOT required for the app to work.
#
# USAGE:
#   bash deploy.sh            # deploy both backend and frontend
#   bash deploy.sh backend    # only Render services
#   bash deploy.sh frontend   # only Firebase Hosting
#
# The frontend build reads VITE_API_BASE (gateway URL) at build time.

set -euo pipefail
cd "$(dirname "$0")"

GATEWAY_URL="${VITE_API_BASE:-https://ecom-gateway.onrender.com}"
ACTION="${1:-all}"

echo ">> Gateway URL for frontend: $GATEWAY_URL"

if [[ "$ACTION" == "all" || "$ACTION" == "backend" ]]; then
  echo ">> Deploying backend to Render (render.yaml) ..."
  if command -v render >/dev/null 2>&1; then
    render blueprint launch --yes || render blueprint apply --yes
  else
    echo "!! 'render' CLI not found. Install it and run 'render login', then:"
    echo "   render blueprint launch --yes"
    echo "   (or connect the repo in the Render dashboard — render.yaml is already in the repo)"
  fi
fi

if [[ "$ACTION" == "all" || "$ACTION" == "frontend" ]]; then
  echo ">> Building frontend ..."
  cd frontend-react
  VITE_API_BASE="$GATEWAY_URL" npm run build
  cd ..
  echo ">> Deploying frontend to Firebase Hosting ..."
  if command -v firebase >/dev/null 2>&1; then
    firebase deploy --only hosting
  else
    echo "!! 'firebase' CLI not found. Install it and run 'firebase login', then:"
    echo "   VITE_API_BASE=$GATEWAY_URL npm run build   # (already done above)"
    echo "   firebase deploy --only hosting"
  fi
fi

echo ">> Done."
