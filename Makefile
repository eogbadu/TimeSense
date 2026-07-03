.PHONY: up down logs migrate test build backend-shell

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

test:
	cd backend && source .venv/bin/activate && pytest -v

backend-shell:
	docker compose exec backend bash

health:
	curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
