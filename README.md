# Docs2Static

Transforme des documents collaboratifs [Docs](https://docs.suite.anct.gouv.fr/) en site statique avec [Zensical](https://zensical.org/). Homepage stylisee incluse.

**Exemple :** [Document source](https://notes.liiib.re/docs/778c5d28-cc11-4692-a17e-8e59c94c904a/) -> [Site genere](https://nasjoe.github.io/zendocs_test/)

## Installation

```bash
# Avec pip
pip install docs2static

# Avec uv
uv add docs2static

# Depuis les sources
git clone git@github.com:CoopCodeCommun/Docs2static.git
cd Docs2static
uv sync
```

Requiert Python 3.14+.

## Configuration

```bash
cp env_example .env
```

Variables dans le `.env` :

| Variable | Description |
|----------|-------------|
| `DOCS_URL` | URL du document Docs racine |
| `GITHUB_REPO` | Adresse SSH du depot GitHub (ex: `git@github.com:User/Repo.git`) |
| `GITLAB_REPO` | Adresse SSH du depot GitLab (alternative) |
| `BACKEND` | Moteur statique (par defaut : `zensical`) |

## Usage CLI

```bash
# Telecharger les documents et construire le site
docs2static

# Deployer sur GitHub/GitLab Pages (sans retelecharger)
docs2static --deploy

# Forcer le telechargement sans cache
docs2static --no-cache

# Specifier le format de sortie
docs2static -f html        # html, markdown ou both
```

### Options

| Option | Description |
|--------|-------------|
| `-f, --format` | Format de sortie (`html`, `markdown`, `both`) |
| `--no-cache` | Ignorer le cache SQLite (24h par defaut) |
| `-b, --backend` | Moteur de site statique |
| `-d, --deploy` | Deployer sans retelecharger |

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

## Deploiement en production

### GitHub Actions

Creez `.github/workflows/docs2static.yml` :

```yaml
name: Build & Deploy Documentation

on:
  schedule:
    - cron: '0 6 * * *'   # Tous les jours a 6h
  workflow_dispatch:        # Lancement manuel

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Setup Python
        run: uv python install 3.14

      - name: Install docs2static
        run: uv add docs2static

      - name: Build & Deploy
        env:
          DOCS_URL: ${{ secrets.DOCS_URL }}
          GITHUB_REPO: ${{ secrets.GITHUB_REPO }}
          BACKEND: zensical
        run: |
          uv run docs2static
          uv run docs2static --deploy
```

Ajoutez les secrets `DOCS_URL` et `GITHUB_REPO` dans les parametres du depot.
Configurez une cle SSH de deploiement avec acces en ecriture au depot cible.

### GitLab CI

Creez `.gitlab-ci.yml` :

```yaml
pages:
  image: python:3.14
  stage: deploy
  script:
    - pip install uv
    - uv add docs2static
    - uv run docs2static
    - uv run docs2static --deploy
  variables:
    DOCS_URL: $DOCS_URL
    GITLAB_REPO: $GITLAB_REPO
    BACKEND: zensical
  only:
    - schedules
    - web
```

Ajoutez les variables `DOCS_URL` et `GITLAB_REPO` dans CI/CD > Variables.

### Deploiement manuel (serveur)

```bash
# Installation
pip install docs2static

# Configuration
export DOCS_URL="https://notes.liiib.re/docs/votre-doc-id/"
export GITHUB_REPO="git@github.com:Org/Repo.git"
export BACKEND="zensical"

# Execution
docs2static              # Telecharge + build
docs2static --deploy     # Deploie sur Pages

# Cron (optionnel)
echo "0 6 * * * cd /opt/docs && docs2static && docs2static --deploy" | crontab -
```

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

## Licence

Apache 2.0 - Voir [LICENSE](LICENSE).

## Credits

- Inspire par le travail de [Sylvain Zimmer](https://github.com/suitenumerique/st-home/tree/main/src/lib/docs2dsfr) (stack Node.js).
- Developpe par [CoopCodeCommun](https://github.com/CoopCodeCommun) en Python, style FALC.
