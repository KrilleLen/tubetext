.PHONY: install dev test lint docker

install:
	python -m pip install -r requirements-dev.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

lint:
	ruff check .

docker:
	docker compose up --build
