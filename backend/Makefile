.PHONY: install run test lint migrate worker

install:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/

migrate:
	alembic upgrade head

worker:
	celery -A app.workers.celery_app worker --loglevel=info

revision:
	alembic revision --autogenerate -m "$(name)"
