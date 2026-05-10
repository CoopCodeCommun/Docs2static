# Docs2Static

Transforme des documents collaboratifs [Docs](https://docs.suite.anct.gouv.fr/) en site statique avec [Zensical](https://zensical.org/). Homepage stylisée incluse.

**Exemple :** [Document source](https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/) → [Site généré](https://CoopCodeCommun.github.io/Docs2static/)

## Démarrage rapide

Requiert **Python 3.14+** et [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. Cloner le projet
git clone git@github.com:CoopCodeCommun/Docs2static.git
cd Docs2static

# 2. Installer les dépendances
uv sync

# 3. Configurer
cp env_example .env
# Éditez .env : au minimum DOCS_URL (URL de votre document Docs racine)

# 4. Build du site (fetch + génération markdown + assets)
make build

# 5. Servir localement (live reload)
make serve   # → http://localhost:8000
```

## Configuration `.env`

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `DOCS_URL` | ✅ | URL du document Docs racine (ex: `https://notes.liiib.re/docs/UUID/`) |
| `GITHUB_REPO` | recommandé | Dépôt GitHub Pages cible (ex: `https://github.com/Org/Repo`) |
| `GITLAB_REPO` | alternative | Dépôt GitLab Pages cible |
| `SITE_URL` | optionnel | URL publique du site. Si custom domain, un `CNAME` est généré au déploiement |
| `BACKEND` | optionnel | Moteur statique (défaut : `zensical`) |
| `TEMPLATE` | optionnel | Template homepage (défaut : `phantom`) |

### Exemple concret

Le `.env` suivant produit le site [CoopCodeCommun.github.io/Docs2static](https://CoopCodeCommun.github.io/Docs2static/) :

```bash
DOCS_URL=https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/
GITHUB_REPO=https://github.com/CoopCodeCommun/Docs2static
BACKEND=zensical
```

## Commandes Make

| Commande | Description |
|----------|-------------|
| `make build` | Fetch les Docs + génère les markdown + copie les assets template |
| `make build-no-cache` | Idem, ignore le cache SQLite 24h |
| `make serve` | Lance le serveur local Zensical (live reload) sur http://localhost:8000 |
| `make audit` | Audit éditorial pré-build via le skill Claude Code (frontmatter, images, SEO, données structurées) |
| `make help` | Affiche toutes les commandes |

Pour déployer sur GitHub/GitLab Pages (mainteneurs uniquement, nécessite une clé SSH avec write access) :

```bash
uv run docs2static --deploy
```

Cette commande build et force-push le site dans la branche `gh-pages` (ou `gl-pages` pour GitLab) du dépôt configuré dans `GITHUB_REPO` / `GITLAB_REPO`. La page Mentions légales, le CNAME (si domaine custom), `robots.txt`, `humans.txt` et `sitemap.xml` sont régénérés à chaque deploy.

### Audit pré-build (skill Claude Code)

`make audit` invoque le skill **`docs-content-curator`** (embarqué dans `.claude/skills/`) qui lit vos Docs source via le MCP [`lasuite-docs`](https://github.com/CoopCodeCommun/lasuite-docs-mcp) et vérifie :

- **Frontmatter** : clés obligatoires (`titre`), recommandées (`résumé`, `auteur·ice`, `image`), orthographes
- **Images** : `alt` text, format (WebP/AVIF), dimensions raisonnables
- **SEO** : longueur title/description, unicité H1, canonical, Open Graph
- **Données structurées** : Schema.org JSON-LD (`Organization`, `Event`, `Article`…), `BreadcrumbList`
- **Mentions légales** : page auto-générée par défaut, ou page custom via `legal_url:`
- **FAQ** : suggestion de page `FAQPage` Schema.org

Sortie : rapport structuré (✅ / ⚠️ / ❌ / 💡) avec score /100 et patches optionnels appliqués via MCP (confirmation explicite requise avant écriture). Pré-requis : CLI [Claude Code](https://docs.claude.com/claude-code/quickstart) installée et MCP `lasuite-docs` configuré.

## Metadonnees (frontmatter)

Ajoutez un bloc frontmatter au debut de vos documents Docs :

```yaml
---
titre: Ma page
auteur·ice: Jonas
brouillon: non
resume: Description de la page
date: 2026-01-15
---
```

| Cle (FR / EN) | Usage |
|----------------|-------|
| `titre` / `title` | Titre de la page |
| `auteur·ice` / `author` | Auteur du site (copyright) |
| `resume` / `summary` | Description du site ou extrait |
| `licence` / `license` | Licence affichee dans le copyright |
| `brouillon` / `draft` | `oui` / `true` = page et enfants ignores |
| `date` | Date du document (AAAA-MM-JJ) |

## Homepage et templates

### Convention images

Dans le document racine Docs :

- **1re image** → logo du site (`logo_file` dans les metadonnees)
- **2e image** → image hero de fond (`hero_image` dans les metadonnees)

### Frontmatter auto-enrichi

Docs2Static extrait automatiquement ces champs si absents du frontmatter :

| Champ | Source |
|-------|--------|
| `image` | 1re image du contenu |
| `hero_image` | 2e image du contenu |
| `excerpt` | 1er paragraphe de texte (tronque a 160 caracteres) |

### Templates

Le template par defaut est `phantom` (inspire de [HTML5UP Phantom](https://html5up.net/phantom)). La homepage est generee dynamiquement depuis l'arbre de navigation : chaque section enfant devient une tuile coloree avec image, titre et extrait.

Pour changer de template :

```yaml
# Dans le frontmatter du document racine
template: phantom
```

Ou via variable d'environnement :

```bash
TEMPLATE=phantom
```

Les templates sont stockes dans `docs2static/assets/templates/{nom}/` avec les sous-dossiers `overrides/` et `stylesheets/`.

### Iframe embarque

Pour integrer un contenu externe (agenda, formulaire, etc.), ajoutez une cle `iframe` dans le frontmatter :

```yaml
---
iframe: src="https://example.com/embed/" width="100%" height="1000px"
---
```

L'iframe sera affichee sous le contenu de la page.

## Architecture

```
docs2static/
  main.py                # Orchestration : API, arbre, frontmatter, images
  zensical_backend.py    # Integration Zensical : navigation, toml, deploiement
  assets/templates/      # Templates homepage (phantom, etc.)
    phantom/
      overrides/         # Surcharge du theme Zensical (main.html)
      stylesheets/       # CSS homepage (home.css)
```

Pipeline : Docs API -> arbre -> frontmatter -> images -> Markdown -> Zensical build -> deploy

Pour plus de details, voir [guideline.md](guideline.md).

## Tests

```bash
uv run python -m pytest tests/

# Avec options
uv run python tests/test_main.py --no-cache     # Sans cache
uv run python tests/test_main.py --deploy        # Test deploiement reel
uv run python tests/test_main.py --test-zensical # Test rendu interactif
```

## Release (mainteneurs)

### Prérequis

Un token PyPI est nécessaire pour publier. Le générer sur [pypi.org](https://pypi.org) → Account settings → API tokens.

**Stocker le token dans un gestionnaire de secrets** (KeePass, Vault, Bitwarden, etc.) — ne jamais le committer.

Pour éviter de le ressaisir à chaque fois, l'exporter comme variable d'environnement :

```bash
export UV_PUBLISH_TOKEN=pypi-...
```

### Étapes

```bash
# 1. Mettre à jour la version dans pyproject.toml
#    version = "X.Y.Z"

# 2. Mettre à jour CHANGELOG.md

# 3. Builder, publier, tagger et pousser
make release
```

## Licence

Apache 2.0 - Voir [LICENSE](LICENSE).

## Credits

- Inspire par le travail de [Sylvain Zimmer](https://github.com/suitenumerique/st-home/tree/main/src/lib/docs2dsfr) (stack Node.js).
- Developpe par [CoopCodeCommun](https://github.com/CoopCodeCommun) en Python, style FALC.
