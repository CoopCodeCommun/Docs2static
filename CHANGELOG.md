# Changelog

Toutes les modifications notables de ce projet sont consignees dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet adhere au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

## [0.6.1] - 2026-03-09

### Added
- Configuration des extensions Markdown dans `pyproject.toml` : `admonition`, `pymdownx.details`, `pymdownx.superfences` (@achabran).
- Bloc `home-body` supplementaire dans `phantom/overrides/main.html` qui convertit les backslashes simples (`\`) en sauts de ligne `<br>` via le filtre `replace ... | safe` (@achabran).

### Fixed
- Correction du filtre de remplacement des backslashes : `\\\\` -> `\\` pour cibler les backslashes simples du contenu (@achabran).
- Syntaxe des extensions Markdown : passage de `key = {}` a `key = true` dans `[project.markdown_extensions]` (@achabran).

## [0.6] - 2026-02-27

### Changed
- La variable d'environnement `SITE_URL` est desormais prioritaire pour la configuration de `site_url` ; commentaires mis a jour et regex ajustee pour le matching multiligne (@JonasFW13).

## [0.5] - 2026-02-27

### Added
- Templates Phantom et Solid State, avec composants SASS pour la mise en page et le style (@JonasFW13).

### Changed
- Template Phantom : ameliorations d'accessibilite, optimisation des elements `hero` et des tuiles (`tiles`) (@JonasFW13).

## [0.3.0] - 2026-02-26

### Added
- Metadonnees Open Graph et Twitter Cards (@JonasFW13).
- Support iframe ameliore (embed) (@JonasFW13).

### Changed
- Nettoyage des URLs dans le Markdown source (@JonasFW13).

### Removed
- Workflow GitHub Actions de publication PyPI (retire puis re-iterations en debug) (@JonasFW13).

## [0.2.0] - 2026-02-26

### Added
- Support des iframes via la cle `iframe` dans le frontmatter (@JonasFW13).
- Option `TEMPLATE` (env / frontmatter) pour selectionner un template de homepage (@JonasFW13).
- Workflow GitHub Actions de publication automatique sur PyPI (@JonasFW13).

## [0.1.x] - 2026-02-24 - 2026-02-26

### Added
- Integration du template Phantom pour la homepage (refactor + enrichissement metadonnees) (@JonasFW13).
- Style et structure de la homepage, mise en place des metadonnees automatiques (logo, hero_image, excerpt) (@JonasFW13).
- Restructuration en module `docs2static/` (@JonasFW13).

### Removed
- Suppression du module `docs2dsfr` (non utilise) (@JonasFW13).

## Pre-versions - 2026-01-22 - 2026-01-28

### Added
- Backend Zensical : navigation, generation de `zensical.toml`, deploiement git par SSH (@JonasFW13).
- Support GitLab Pages en plus de GitHub Pages (@JonasFW13).
- Support du frontmatter `draft` / `brouillon` : exclusion des sous-arbres marques comme brouillon (@JonasFW13).
- Mode `--test-zensical` pour tester le rendu interactif (@JonasFW13).
- Premier squelette d'API et orchestration du pipeline Docs API -> Markdown -> site statique (@JonasFW13).
- Initialisation du depot, licence Apache 2.0 (@JonasFW13).

## Contributors

Merci aux personnes qui ont contribue a ce projet :

- [@JonasFW13](https://github.com/JonasFW13) — auteur principal, conception du pipeline, backend Zensical, templates, CI/CD.
- [@achabran](https://github.com/achabran) — extensions Markdown (admonition, details, superfences), traitement des sauts de ligne dans la homepage Phantom.

Le projet est porte par [CoopCodeCommun](https://github.com/CoopCodeCommun) et inspire par le travail de [Sylvain Zimmer](https://github.com/suitenumerique/st-home/tree/main/src/lib/docs2dsfr).

[Unreleased]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.6...v0.6.1
[0.6]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.5...v0.6
[0.5]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.3.0...v0.5
[0.3.0]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/CoopCodeCommun/Docs2static/releases/tag/v0.2.0
