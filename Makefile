.PHONY: lint test

lint:
	uv run ruff format .
	uv run ruff check --fix .
	uv run mypy --config-file pyproject.toml src/ tests/

test:
	uv run pytest -s -vvv tests/
