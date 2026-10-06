.PHONY: run test lint format typecheck check clean

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

# --- ELT / kho dữ liệu (P-066 vòng 2) ---
.PHONY: elt-setup elt-run elt-check elt-docs db-up db-down dev-api dev-web

elt-setup:
	./scripts/setup_elt.sh

elt-run:
	.venv/bin/python -m scripts.elt.run_elt --profile all

elt-check:
	.venv/bin/python -m scripts.elt.check_warehouse

elt-docs:
	.venv/bin/python -m scripts.elt.docs_data

db-up:
	docker compose -f docker-compose.elt.yml up -d --wait

db-down:
	docker compose -f docker-compose.elt.yml down

dev-api:
	.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

dev-web:
	cd frontend && npm run dev
