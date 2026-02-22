.PHONY: install dev test lint run clean

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

dev:
	python -m src.kioku.server

test:
	python -m pytest tests/ -v

test-watch:
	python -m pytest tests/ -v --tb=short -x

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache __pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete
