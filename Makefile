.PHONY: build build-quickstart serve-quickstart
build:
	poetry build

build-quickstart:
	mkdocs build -f ./src/docs/quickstart.yml

serve-quickstart:
	mkdocs serve --livereload -f ./src/docs/quickstart.yml
