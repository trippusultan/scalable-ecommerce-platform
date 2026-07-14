# Convenience wrapper for the e-commerce microservices platform.
# Native run uses one SQLite DB per service under .runtime/data.

.PHONY: install start stop status seed smoke test ci clean

install:
	python -m pip install -r requirements.txt

start:
	python scripts/run_local.py start

stop:
	python scripts/run_local.py stop

status:
	python scripts/run_local.py status

seed:
	python scripts/seed.py

smoke:
	python scripts/smoke.py

test:
	python -m pytest tests/ -q

ci: test
	python -m py_compile common/*.py */main.py 2>/dev/null || python -m compileall -q common

clean:
	python scripts/run_local.py stop || true
	rm -rf .runtime
