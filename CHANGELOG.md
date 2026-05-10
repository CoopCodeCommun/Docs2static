# Changelog

Toutes les modifications notables de ce projet sont consignees dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet adhere au [Semantic Versioning](https://semver.org/lang/fr/).

## [Unreleased]

### Added
- Auto-génération de la page `Mentions légales` dans tous les builds : texte LCEN/RGPD pré-rédigé citant la Coopérative Code Commun comme entité technique. Variables auto-remplies depuis frontmatter racine + .env (domaine, éditeur, licence, plateforme, repo, source Docs). Page placée dans `content/source/{root}/mentions-legales/`, accessible via URL directe (`/mentions-legales/`) et lien dans le footer. **La page n'apparaît PAS dans la nav du header/sidebar** : elle est orpheline volontairement pour ne pas polluer le menu (@JonasFW13).
- Injection automatique de la page Mentions légales dans `sitemap.xml` au moment du `--deploy` (pour que Google et les autres moteurs l'indexent malgré son absence de la nav). Nouvelle fonction `_inject_sitemap_entry()` dans `zensical_backend.py` (@JonasFW13).
- Cle frontmatter `legal_auto: non` (racine) pour désactiver l'auto-génération (@JonasFW13).
- Override explicite encore possible via `legal_url:` (frontmatter racine) qui pointe vers une page Mentions légales custom rédigée par l'éditeur (@JonasFW13).

### Changed
- Le bloc `legal_url` dans le toml utilise désormais la section `[project.extra]` (et non `[extra]`) pour que Zensical le mappe correctement sur `config.extra` côté Jinja (@JonasFW13).

### Fixed
- Le lien Mentions légales du footer n'apparaissait pas car `[extra]` n'est pas reconnu par Zensical — corrigé via `[project.extra]` (@JonasFW13).

## [0.6.7] - 2026-05-10

Cette version regroupe une refonte SEO complete (Open Graph, Twitter Cards, Schema.org JSON-LD enrichi, BreadcrumbList automatique), un correctif critique de chargement `.env` en mode editable, et l'ajout d'un skill Claude Code pour l'audit editorial pre-build. Inclut les bumps intermediaires 0.6.2 a 0.6.6.

### Added

#### SEO et donnees structurees
- Generation systematique d'`og:title`, `og:description`, `og:url`, `og:image`, `og:type` par page (@JonasFW13).
- Twitter Cards (`twitter:title`, `twitter:description`, `twitter:image`) par page (@JonasFW13).
- Schema.org JSON-LD `WebSite` (home) et `WebPage` (sous-pages) par page (@JonasFW13).
- Type Schema.org specialise via la cle frontmatter `schema_type:` (`EducationalOrganization`, `NGO`, `Organization`, `Article`, `Event`, `FAQPage`...) (@JonasFW13).
- Auto-detection du type Schema : `event_date:` -> `Event`, `date+author` -> `Article`, sinon `WebPage` (@JonasFW13).
- Schema.org `Organization` enrichie avec `logo` (URL absolue), `sameAs[]` (reseaux sociaux), `contactPoint`, `author` (@JonasFW13).
- Schema.org `Event` avec `startDate`, `endDate`, `location Place`, `organizer` via les cles `event_date:`, `event_end:`, `event_location:` (@JonasFW13).
- Schema.org `Article` avec `datePublished`, `author Person`, `image` via `date:` et `auteur·ice:`/`author:` (@JonasFW13).
- BreadcrumbList JSON-LD automatique sur toutes les sous-pages depuis `page.ancestors` (@JonasFW13).

#### Fichiers SEO
- Generation automatique de `robots.txt` (avec `Sitemap:`) et `humans.txt` a chaque build (@JonasFW13).
- Copie automatique de ces fichiers dans `content/site/` au deploiement (@JonasFW13).
- Generation automatique du fichier `CNAME` au deploiement quand `SITE_URL` pointe sur un domaine custom — preserve le mapping GitHub/GitLab Pages a chaque force-push (@JonasFW13).
- Skip auto pour `*.github.io`, `*.gitlab.io`, `localhost` (pas de CNAME inutile) (@JonasFW13).

#### Frontmatter
- Cle `description:` injectee automatiquement dans le YAML si absente (depuis `summary`/`résumé`/`excerpt`, tronquee a 160 caracteres) (@JonasFW13).
- Cle `title:` toujours injectee dans le YAML (la fallback Zensical "Index" disparait) (@JonasFW13).
- Generation automatique d'un H1 `# {title}` au debut du markdown si aucun heading present (regex multiline pour eviter les H1 dupliques) (@JonasFW13).
- Nouvelles cles supportees par le moteur :
  - `iframe_title:` — H2 semantique au-dessus de l'iframe (a11y) (@JonasFW13).
  - `legal_url:` (frontmatter racine) — lien Mentions legales dans le footer (@JonasFW13).
  - `sameAs:` (frontmatter racine) — liste URL des reseaux sociaux pour Schema.org (@JonasFW13).
  - `contact_email:`, `contact_type:` (frontmatter racine) — Schema.org `ContactPoint` (@JonasFW13).
  - `event_date:`, `event_end:`, `event_location:` — Schema.org `Event` (@JonasFW13).
  - `schema_type:` — override explicite du type Schema.org (@JonasFW13).

#### Template phantom — accessibilite
- `@media (prefers-reduced-motion: reduce)` : desactive animations et transitions pour les utilisateurs qui le demandent (WCAG 2.3.3) (@JonasFW13).
- `aria-hidden="true"` sur les tags decoratifs des tiles (faux affordance corrige) (@JonasFW13).
- `<section class="iframe-embed">` avec `aria-labelledby` ou `aria-label` selon presence de `iframe_title:` (@JonasFW13).
- `home-tile__content` toujours visible sur mobile (`@media (hover: none)`), evite la troncature inutile (@JonasFW13).
- Override `partials/copyright.html` : ajoute un lien "Mentions legales" dans le footer si `config.extra.legal_url` configure (@JonasFW13).

#### Outillage
- Nouveau skill Claude Code `.claude/skills/docs-content-curator/` : audit editorial pre-build via le MCP `lasuite-docs` (frontmatter, images, SEO, donnees structurees, mentions legales). Score /100, rapport ✅⚠️❌💡, patches optionnels avec confirmation. Lien MCP : https://github.com/CoopCodeCommun/lasuite-docs-mcp (@JonasFW13).

#### Documentation
- Nouveau fichier `docs/MOTEUR.md` : documentation technique exhaustive (12 sections couvrant pipeline, API Docs, cache, frontmatter, formats, backend Zensical, template phantom, SEO, deploiement, pieges Zensical, choix d'archi, evolutions futures) (@JonasFW13).
- `CLAUDE.md` reecrit : commandes a jour, 11 pieges connus avec solutions, mention du skill content-curator (@JonasFW13).

### Changed

- Reecriture du frontmatter YAML genere via `yaml.safe_dump` au lieu d'un format string manuel : garantit un YAML valide meme avec des valeurs contenant `:`, `"`, accents ou caracteres speciaux (@JonasFW13).
- Override `htmltitle` dans le template phantom : evite la duplication `<title>X - X</title>` sur la home quand `page.meta.title == config.site_name` (@JonasFW13).
- `og:type` est desormais `article` pour les sous-pages avec `schema_type` Article-like, `website` sinon (@JonasFW13).
- Schema.org `url` sur les sous-pages utilise `page.canonical_url` au lieu de la racine du site (@JonasFW13).
- Copie recursive de `overrides/` -> `content/overrides/` dans `setup_zensical_backend` : permet le packaging de sous-dossiers comme `partials/` (@JonasFW13).
- Detection "le markdown a-t-il deja un H1 ?" via `re.search(r'^#\s', content, re.MULTILINE)` au lieu de `re.match` sur la premiere ligne — evite les H1 dupliques quand le markdown commence par une image (@JonasFW13).

### Fixed

- **Critique** : `load_dotenv()` chargeait le mauvais fichier `.env` quand docs2static est utilise en install editable depuis un autre projet (`uv add --editable ../docs2static`). Cause : `find_dotenv()` par defaut remonte depuis le fichier appelant (`inspect.stack`), pas depuis le cwd. Fix : appel explicite a `load_dotenv(find_dotenv(usecwd=True))` dans `main()` (deplace hors du module-level) (@JonasFW13).
- Bug "YAML rendu en clair sur la home" : le frontmatter avec `title: 'ZenDocs : Parent'` (le `:` dans la valeur) cassait le parser YAML strict de Zensical, qui laissait alors le bloc `---...---` dans `page.content` au lieu d'extraire les meta. Resolu via `yaml.safe_dump` (@JonasFW13).
- Bug "double H1 sur sous-pages" : un markdown commencant par `![image]()` puis `# Titre` etait considere "sans H1" et le moteur prefixait un nouveau `# {title}` (@JonasFW13).
- Le `og:title` reflete maintenant le titre de la page courante (auparavant : toujours le `site_name`) (@JonasFW13).
- Le `<meta name="description">` est differencie par page (auparavant : fallback `site_description` global identique partout) (@JonasFW13).
- Le burger menu mobile n'est plus masque par le sidebar primary desktop (`@media (min-width: 76.25em)`) (@JonasFW13).

### Dependencies

- Ajout de `pyyaml>=6.0` aux dependencies explicites (utilise par `yaml.safe_dump`) — auparavant transitive via Zensical (@JonasFW13).

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

[Unreleased]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.6.7...HEAD
[0.6.7]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.6.1...v0.6.7
[0.6.1]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.6...v0.6.1
[0.6]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.5...v0.6
[0.5]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.3.0...v0.5
[0.3.0]: https://github.com/CoopCodeCommun/Docs2static/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/CoopCodeCommun/Docs2static/releases/tag/v0.2.0
