.PHONY: lint test release-patch release-minor release-major

lint:
	uv run ruff format .
	uv run ruff check --fix .
	uv run mypy --config-file pyproject.toml src/ tests/

test:
	uv run pytest -s -vvv tests/

release-patch:
	./release.sh patch

release-minor:
	./release.sh minor

release-major:
	./release.sh major
