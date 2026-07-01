.PHONY: dev dev-build prod prod-build logs stop clean test

# ─── Development ───
dev:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --app-dir .

dev-build:
	docker compose up -d --build thoth redis

dev-with-ollama:
	docker compose --profile llm-local up -d --build

# ─── Production ───
prod:
	docker compose --profile prod up -d --build

prod-build:
	docker compose build

# ─── Logs ───
logs:
	docker compose logs -f

logs-thoth:
	docker compose logs -f thoth

# ─── Management ───
stop:
	docker compose down

clean:
	docker compose down -v

restart:
	docker compose restart

# ─── Testing ───
test:
	python3 -m pytest tests/ -v

# ─── Utilities ───
shell:
	docker compose exec thoth /bin/bash

pull-models:
	docker compose run --rm ollama ollama pull llama3.2
	docker compose run --rm ollama ollama pull llama3.2:1b

