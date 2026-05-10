VERSION := $(shell grep '^version' pyproject.toml | cut -d'"' -f2)

.DEFAULT_GOAL := help

help:
	@echo "docs2static v$(VERSION)"
	@echo ""
	@echo "Commandes disponibles :"
	@echo "  make audit           — audit éditorial pré-build (skill Claude Code)"
	@echo "  make build           — fetch les docs et génère le site"
	@echo "  make build-no-cache  — idem, ignore le cache SQLite"
	@echo "  make serve           — lance le serveur local (http://localhost:8000)"
	@echo "  make update-deps     — met à jour toutes les dépendances (uv.lock)"
	@echo "  make release         — build, publie sur PyPI, tag git et push"
	@echo "  make help            — affiche ce message"
	@echo ""
	@echo "Audit pré-build (recommandé avant build & deploy) :"
	@echo "  Lancer 'make audit' lance Claude Code avec le skill docs-content-curator."
	@echo "  Ce skill lit les Docs source via le MCP lasuite-docs et vérifie :"
	@echo "    • frontmatter (clés obligatoires/recommandées, orthographes)"
	@echo "    • images (alt, format, dimensions)"
	@echo "    • SEO (title, description, H1, canonical)"
	@echo "    • données structurées (Schema.org JSON-LD, BreadcrumbList)"
	@echo "    • mentions légales et page FAQ"
	@echo "  Pré-requis : claude CLI + MCP lasuite-docs configuré."
	@echo "  MCP : https://github.com/CoopCodeCommun/lasuite-docs-mcp"
	@echo ""
	@echo "Prérequis release : UV_PUBLISH_TOKEN=pypi-... dans l'environnement"

audit:
	@command -v claude >/dev/null 2>&1 || { \
		echo "❌ La commande 'claude' (Claude Code) n'est pas dans le PATH."; \
		echo "   Installation : https://docs.claude.com/claude-code/quickstart"; \
		exit 1; \
	}
	@echo "🔍 Lancement du skill docs-content-curator..."
	@echo "   (audit éditorial pré-build via lasuite-docs MCP)"
	@echo ""
	claude "/skill docs-content-curator audit complet du projet courant avant build, conseille-moi sur les améliorations frontmatter / SEO / accessibilité / mentions légales"

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
