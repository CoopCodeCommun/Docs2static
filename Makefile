VERSION := $(shell grep '^version' pyproject.toml | cut -d'"' -f2)

.DEFAULT_GOAL := help

help:
	@echo "docs2static v$(VERSION)"
	@echo ""
	@echo "Commandes disponibles :"
	@echo "  make build           — fetch les docs et génère le site"
	@echo "  make build-no-cache  — idem, ignore le cache SQLite"
	@echo "  make serve           — lance le serveur local (http://localhost:8000)"
	@echo "  make update-deps     — met à jour toutes les dépendances (uv.lock)"
	@echo "  make release         — build, publie sur PyPI, tag git et push"
	@echo "  make help            — affiche ce message"
	@echo ""
	@echo "Prérequis release : UV_PUBLISH_TOKEN=pypi-... dans l'environnement"

build:
	uv run docs2static

build-no-cache:
	uv run docs2static --no-cache

serve:
	cd content && uv run zensical serve

update-deps:
	uv sync --upgrade

release:
	uv build
	uv publish
	git tag v$(VERSION)
	git push origin v$(VERSION)
