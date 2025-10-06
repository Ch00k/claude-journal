.PHONY: lint test format

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy --config-file pyproject.toml src/ tests/

test:
	uv run pytest tests/ -v

format:
	uv run ruff format .
	uv run ruff check --fix .
