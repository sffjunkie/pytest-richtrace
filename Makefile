.PHONY: check build build-quickstart serve-quickstart
check:
	pre-commit run --files src/pytest_richtrace/*

build:
	poetry build

build-quickstart:
	mkdocs build -f ./src/docs/quickstart.yml

serve-quickstart:
	mkdocs serve --livereload -f ./src/docs/quickstart.yml
