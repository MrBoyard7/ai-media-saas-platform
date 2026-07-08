.PHONY: help install dev test lint format typecheck up down migrate seed

help:
	@echo "make install    - install dev dependencies"
	@echo "make dev        - run the API locally with autoreload"
	@echo "make test       - run the test suite with coverage"
	@echo "make lint       - run ruff"
	@echo "make format     - run black + isort"
	@echo "make typecheck  - run mypy"
	@echo "make up         - start the full stack (api, worker, postgres, redis) via Docker Compose"
	@echo "make down       - stop the Docker Compose stack"
	@echo "make migrate    - apply Alembic migrations"
	@echo "make seed       - seed demo plans/features"

install:
	pip install -r requirements-dev.txt
	pre-commit install

dev:
	uvicorn app.main:app --reload

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .

format:
	black .
	isort .

typecheck:
	mypy app

up:
	docker compose up --build

down:
	docker compose down -v

migrate:
	alembic upgrade head

seed:
	python -m scripts.seed_demo_data
