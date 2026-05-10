# Moteur Docs2Static — documentation technique

> Version moteur : 0.6.4 — Zensical : 0.0.41 — Python : 3.14+
> Référence pour reprendre une session avec tout le contexte technique en tête.

## Sommaire

1. [Pipeline complet](#1-pipeline-complet)
2. [API Docs (lasuite-docs)](#2-api-docs-lasuite-docs)
3. [Cache requests-cache (SQLite)](#3-cache-requests-cache-sqlite)
4. [Frontmatter : extraction et écriture](#4-frontmatter--extraction-et-écriture)
5. [Format des fichiers générés](#5-format-des-fichiers-générés)
6. [Backend Zensical](#6-backend-zensical)
7. [Template phantom (overrides + CSS)](#7-template-phantom-overrides--css)
8. [SEO : architecture et points d'extension](#8-seo--architecture-et-points-dextension)
9. [Déploiement Pages (SSH)](#9-déploiement-pages-ssh)
10. [Pièges Zensical 0.0.41](#10-pièges-zensical-0041)
11. [Choix d'architecture](#11-choix-darchitecture)
12. [Évolutions futures envisagées](#12-évolutions-futures-envisagées)

---

## 1. Pipeline complet

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
│  Docs API   │ → │ tree (paths) │ → │ process_doc    │ → │ index.md +       │
│ /descendants│   │ + frontmatter│   │ + images dl    │   │ metadata.json    │
└─────────────┘   └──────────────┘   └────────────────┘   └──────────────────┘
                                                                   ↓
                                                        ┌──────────────────────┐
                                                        │ setup_zensical_backend│
                                                        │  → zensical.toml     │
                                                        │  → copy template     │
                                                        │  → copy CSS          │
                                                        │  → robots/humans.txt │
                                                        └──────────────────────┘
                                                                   ↓
                                                        ┌──────────────────────┐
                                                        │ zensical serve/build │
                                                        │  → content/site/     │
                                                        └──────────────────────┘
                                                                   ↓
                                                        ┌──────────────────────┐
                                                        │  --deploy            │
                                                        │  → git clone+force   │
                                                        │  → push gh-pages     │
                                                        └──────────────────────┘
```

### Étapes (numérotées comme dans `process_document`)

| Étape | Fonction | Description |
|-------|----------|-------------|
| 0 | `parse_docs_url` | Extrait base URL + UUID racine |
| 1 | `fetch_document_descendants` | API `/descendants/` : récupère TOUTE l'arborescence en 1 appel (au lieu de N appels récursifs) |
| 2 | `fetch_document_tree` | Reconstruit la hiérarchie locale via le champ `path` (matériel·sé en arbre) |
| 3 | `fetch_document_content` | Télécharge HTML + Markdown |
| 4 | `extract_frontmatter` / `extract_frontmatter_markdown` | Sépare YAML `---...---` du body |
| 5 | `download_and_replace_images` | Télécharge chaque `<img>` ou `![]()` dans le dossier doc, remplace l'URL distante |
| 6 | `download_frontmatter_image` | Idem pour `logo:` et `image:` du frontmatter |
| 7 | Injection SEO (title, description, H1) | Si absentes |
| 8 | `is_draft` check | Skip si `draft:` ou `brouillon:` truthy |
| 9 | `yaml.safe_dump` | Reconstruit le frontmatter quoté correctement |
| 10 | `save_file` | Écrit `index.md` + `metadata.json` |
| 11 | Récursion sur enfants | Décrémente l'arbre |
| 12 | `setup_zensical_backend` (root only) | Configure Zensical + copie template + CSS + SEO files |

---

## 2. API Docs (lasuite-docs)

Base : `https://notes.liiib.re/api/v1.0/` (ou autre instance Docs).

**Endpoints utilisés** :

| Endpoint | Usage |
|----------|-------|
| `GET /documents/{id}/` | Métadonnées du doc (titre, dates, path) |
| `GET /documents/{id}/?type=html` | Rendu HTML |
| `GET /documents/{id}/?type=markdown` | Rendu Markdown (préféré pour Zensical) |
| `GET /documents/{id}/descendants/` | Arborescence complète (clé : champ `path`) |
| `GET /documents/{id}/children/` | Fallback si `descendants` indisponible |

**Reconstruction de l'arbre** : chaque doc renvoie un champ `path` du type `"00010002"` (chaque 4 chars = 1 niveau). On trie par `path`, puis on construit l'arbre via comparaisons de préfixe.

**Auth** : la plupart des docs partagés en `public:editor` ne nécessitent PAS d'auth pour la lecture. Pour modifier (tests via MCP), il faut cookie + CSRF (voir lasuite-docs MCP).

---

## 3. Cache requests-cache (SQLite)

```python
session = requests_cache.CachedSession(
    'docs_cache',           # → docs_cache.sqlite à la racine
    expire_after=86400,     # 24h
    cache_control=False,    # Force le cache même si serveur envoie cookies
)
```

- Cache HIT → log `[CACHE]`
- `--no-cache` → bypass complet
- Pour invalider manuellement : supprimer `docs_cache.sqlite`

---

## 4. Frontmatter : extraction et écriture

### Lecture (entrée Docs)

Le frontmatter est extrait via regex `^---\n(.*?)\n---` (lignes 285+ et 310+ de `main.py`). Parser custom (pas YAML strict) :

```python
items = re.findall(r'^\s*([^:]+?)\s*:\s*(.+)$', raw_info, re.MULTILINE)
```

⚠️ Ce parser ne gère PAS les listes YAML multi-lignes (`tags:\n  - foo`). Les listes sont reconstruites manuellement à partir de strings CSV (`mots-cles: a, b, c`).

### Aliases bilingues

```python
# tags
tags_raw = fm.get("tags") or fm.get("mots-clés") or fm.get("mots-cles") or fm.get("keywords")
# summary
if "résumé" in fm and "summary" not in fm:
    fm["summary"] = fm["résumé"]
# draft
draft = fm.get("draft") or fm.get("brouillon")  # truthy: "true", "yes", "oui", "1"
```

### Extraction automatique de `excerpt`

Premier paragraphe non-vide du markdown (skip headings/images/`---`), tronqué à 160 chars sur frontière de mot, puis `…` :

```python
if clean_md and "excerpt" not in fm:
    # ... boucle de scan, skip lignes commençant par #, !, ---
```

### Injection SEO (avant écriture YAML)

Effectuée juste avant `yaml.safe_dump` dans `process_document` :

```python
fm["title"] = title  # toujours injecté

if "description" not in fm:
    desc_source = fm.get("summary") or fm.get("résumé") or fm.get("excerpt")
    if desc_source:
        desc = str(desc_source).strip()
        if len(desc) > 160:
            desc = desc[:160].rsplit(" ", 1)[0] + "…"
        fm["description"] = desc

# H1 fallback (anti-Index de Zensical)
if clean_md and not re.match(r'^\s*#\s', clean_md.lstrip()):
    clean_md = f"# {title}\n\n{clean_md}"
```

### Écriture (sortie YAML)

**TOUJOURS via `yaml.safe_dump`** (pas de string formatting manuelle) :

```python
yaml_dump = yaml.safe_dump(
    final_frontmatter,
    allow_unicode=True,        # garde les accents
    default_flow_style=False,  # listes en multi-ligne YAML standard
    sort_keys=False,           # préserve l'ordre d'insertion
)
md_with_fm = f"---\n{yaml_dump}---\n\n"
```

**Pourquoi obligatoire** : les valeurs comme `title: ZenDocs : Parent` (le `:` dans la valeur) cassent un YAML construit manuellement. Cas réel : tout le bloc `---...---` rendu en clair dans la page (parser Zensical fail closed).

### Frontmatter final type

```yaml
---
auteur·ice: Coopérative Code Commun
langue: fr
licence: CC-BY-SA
catégorie: Présentation
résumé: des documents pour tester
brouillon: non
logo: 9a08b49e-498f-49c9-a3ac-dcf1c9c59292.png
image: 70cd180e-e3fa-4e80-a79a-36ec46b11743.jpg
iframe: src="https://example.com/embed/" width="100%" height="800px"
tags:
- Zensical
- Docs
summary: des documents pour tester
excerpt: Ceci est le document parent du test
edit_url: https://notes.liiib.re/docs/UUID/
title: 'ZenDocs : Parent'    # ← quoté car contient `:`
description: des documents pour tester
---
```

Toutes ces clés sont lues par Zensical natif et/ou par notre template phantom :

| Clé | Lue par |
|-----|---------|
| `title` | Zensical natif (`<title>`, fallback) + phantom (og:title, schema) |
| `description` | Zensical natif (`<meta name="description">`) + phantom (og:description) |
| `image` | phantom (og:image, twitter:image, hero bg) |
| `logo` | phantom (logo hero, navbar) |
| `summary`, `excerpt` | phantom (subtitle hero, tile descriptions, fallback description) |
| `tags` | Zensical natif (badges) + phantom (tile tags) |
| `iframe` | phantom (iframe embed) |
| `iframe_title` | phantom — H2 sémantique au-dessus de l'iframe (a11y) |
| `edit_url` | Zensical natif (bouton "Aller au dépôt") |
| `template` | `setup_zensical_backend` (sélection du template) |
| `brouillon` / `draft` | `is_draft` (skip subtree) |
| `schema_type` | phantom — type Schema.org (`EducationalOrganization`, `NGO`, `Event`, `Article`, `FAQPage`...) |
| `sameAs` (racine) | phantom — liste URL réseaux sociaux pour Schema.org Organization |
| `contact_email` (racine) | phantom — Schema.org `ContactPoint` |
| `contact_type` (racine) | phantom — type du ContactPoint (`customer service` par défaut) |
| `event_date`, `event_end`, `event_location` | phantom — Schema.org `Event` (auto-détecté si `event_date` présent) |
| `date`, `auteur·ice`/`author` | phantom — Schema.org `Article` (auto-détecté si les 2 présents) |
| `legal_url` (racine) | `setup_zensical_backend` — passé en `[project.extra]` du toml, lu par `partials/copyright.html` (lien Mentions légales). Auto-set à `/mentions-legales/` quand la page est auto-générée. |
| `legal_auto` (racine) | `setup_zensical_backend` — `non`/`no`/`false`/`0`/`off` désactive l'auto-génération de la page Mentions légales (par défaut activée) |

---

## 5. Format des fichiers générés

```
content/
├── source/
│   └── zendocs-parent/                          # ← slug du doc racine (docs_dir Zensical)
│       ├── index.md                             # frontmatter + markdown
│       ├── metadata.json                        # copie JSON propre des meta
│       ├── 9a08b49e-...png                      # images frontmatter (logo)
│       ├── 70cd180e-...jpg                      # images frontmatter (hero)
│       ├── stylesheets/home.css                 # copié depuis assets/templates/.../stylesheets/
│       ├── agenda/
│       │   └── index.md
│       └── premier-enfant-sous-partie/
│           ├── index.md
│           ├── c19ff90d-...jpg                  # images de contenu
│           └── premier-petit-enfant/
│               └── index.md
├── overrides/
│   └── main.html                                # template phantom copié
├── site/                                        # build Zensical (généré)
├── zensical.toml                                # config + nav
├── docs_cache.sqlite                            # cache API
├── robots.txt                                   # ← _generate_seo_files
└── humans.txt
```

**Slug** : `slugify(title)` enlève les accents, garde [a-z0-9-], remplace espaces par `-`.

**`metadata.json`** : copie du frontmatter sans `path` ni `edit_url` — utilisé pour debug ou outils tiers.

---

## 6. Backend Zensical

### Génération `zensical.toml`

```toml
[project]
extra_files = ["humans.txt", "robots.txt"]
site_url = "https://coopcodecommun.github.io/Docs2static/"
nav = [
    "index.md",
    { "Agenda" = "agenda/index.md" },
    { "Premier enfant : sous partie" = [
        "premier-enfant-sous-partie/index.md",
        { "premier petit enfant" = "premier-enfant-sous-partie/premier-petit-enfant/index.md" },
        ...
    ] },
]
docs_dir = "source/zendocs-parent"
repo_url = "https://notes.liiib.re/docs/UUID/"
site_name = "ZenDocs : Parent"
site_description = "des documents pour tester ..."
site_author = "Coopérative Code Commun"
copyright = "Copyright © 2026 ... - CC-BY-SA"
```

`build_nav_structure` parcourt récursivement l'arbre et construit la liste TOML. `format_nav_to_toml` la sérialise. Si un `index.md` n'existe pas (drafts), la branche est filtrée.

### Backend modulaire

Pour ajouter un backend :

1. Créer `docs2static/monbackend_backend.py`
2. Définir `setup_monbackend_backend(base_content_dir, frontmatter, title, ...)`
3. L'appeler dans `process_document` (ligne ~680) selon `template_name` ou `backend`

L'idée : la couche en amont (fetch, frontmatter, images) est générique. Seule la conf et la copie d'assets diffèrent par moteur.

### Copie des assets

Via `importlib.resources` (lit dans le wheel installé) :

```python
template_dir = importlib.resources.files("docs2static.assets.templates") / template_name
# → docs2static/assets/templates/phantom/
# Copie overrides/main.html → content/overrides/main.html
# Copie stylesheets/home.css → content/source/{root}/stylesheets/home.css
```

Le fichier `main.html` est placé dans `content/overrides/` car Zensical le détecte automatiquement comme template surchargé (configuré via `theme.custom_dir = "overrides"` dans `zensical.toml`).

---

## 7. Template phantom (overrides + CSS)

### Structure

```
docs2static/assets/templates/phantom/
├── overrides/
│   └── main.html        # 87 lignes — extends "base.html"
└── stylesheets/
    └── home.css         # 517 lignes — hero + tiles + responsive
```

### `main.html` — points d'extension

```jinja2
{% extends "base.html" %}

{% block htmltitle %}
  {# Override : Zensical natif duplique site_name quand page.meta.title == site_name #}
  {% if page.is_homepage or page.url == "" %}
    <title>{{ config.site_name }}</title>
  {% elif page.meta and page.meta.title %}
    <title>{{ page.meta.title }} - {{ config.site_name }}</title>
  {% elif page.title %}
    <title>{{ page.title | striptags }} - {{ config.site_name }}</title>
  {% else %}
    <title>{{ config.site_name }}</title>
  {% endif %}
{% endblock %}

{% block extrahead %}
  {# Open Graph + Twitter Card + Schema.org JSON-LD per-page #}
  ...
{% endblock %}

{% block content %}
  {% if page.url == "" %}
    {# === HOMEPAGE === #}
    {# - Hero (logo, title, subtitle) #}
    {# - {{ page.content | replace("\\", "<br>") | safe }} #}
    {# - Tiles (1 par section enfant), avec image+excerpt+tags #}
    {# - <section class="iframe-embed"> optionnel #}
  {% else %}
    {{ super() }}                {# rendu Zensical natif #}
    {# <section class="iframe-embed"> optionnel post-content #}
  {% endif %}
{% endblock %}
```

### Iframe embarqué (a11y-aware)

Pattern utilisé dans `main.html` quand `page.meta.iframe` est défini :

```jinja2
{% if page.meta and page.meta.iframe %}
{% set _iframe_title = page.meta.iframe_title or "Contenu intégré" %}
<section class="iframe-embed"
  {% if page.meta.iframe_title %}aria-labelledby="iframe-heading"
  {% else %}aria-label="{{ _iframe_title }}"{% endif %}>
  {% if page.meta.iframe_title %}
  <h2 id="iframe-heading" class="iframe-embed__title">{{ page.meta.iframe_title }}</h2>
  {% endif %}
  <iframe {{ page.meta.iframe }} title="{{ _iframe_title }}"></iframe>
</section>
{% endif %}
```

**Comportement** :

| `iframe_title:` dans frontmatter | Rendu HTML |
|----------------------------------|-----------|
| absent | `<section aria-label="Contenu intégré">` + iframe sans heading visible |
| `iframe_title: Notre carte` | `<section aria-labelledby="iframe-heading">` + `<h2>Notre carte</h2>` + iframe |

Bénéfice : l'iframe a toujours un libellé sémantique pour les screen readers et un heading H2 visible quand l'utilisateur en fournit un.

### Variables Zensical disponibles

| Variable | Source | Notes |
|----------|--------|-------|
| `page.meta` | frontmatter parsé | dict des clés YAML, `None` si parsing fail |
| `page.title` | H1 du markdown OU `nav` du toml | "Index" si fallback de Zensical |
| `page.url` | URL relative | `""` sur la home |
| `page.is_homepage` | bool | True sur racine |
| `page.canonical_url` | URL absolue | si `site_url` configuré |
| `page.content` | HTML rendu | inclut le YAML brut si parsing fail (piège !) |
| `nav.items` | liste sections | utilisé pour les tiles |
| `config.site_name` / `site_url` / `site_description` / `site_author` | depuis toml | |

### Tiles (homepage)

Boucle sur `nav.items`. Pour chaque section :

- Si `section.children` existe → on prend `section.children | first` comme `idx`, et on regarde `idx.meta.image`, `idx.meta.excerpt`, `idx.meta.tags`
- Sinon (page directe sous racine) → on regarde `section.meta` directement

Style cyclique : `style1` à `style6` (couleurs définies dans `home.css`). Le compteur `tile_count.n` boucle modulo 6.

Image absente → placeholder coloré `home-tile__image--placeholder`.

### `home.css` — sections principales

| Lignes | Section |
|--------|---------|
| 1-50 | Reset + variables CSS (`:root --color-*`) |
| 50-150 | `.home-hero` : layout flex, fond, padding |
| 150-260 | `.home-hero__logo`, `.home-title`, `.home-subtitle` |
| 260-310 | `.home-tile__image` (240px height + object-fit: cover) |
| 310-380 | `.home-tile__content` (titre, excerpt, tags) |
| 380-420 | Couleurs des 6 styles |
| 420-520 | Responsive : mobile burger fix (`@media min-width: 76.25em` pour le sidebar desktop), tile grid mobile/tablet/desktop |

**Convention CSS** : BEM strict (`block__element--modifier`). Pas de `!important`.

### Burger menu fix Zensical

Bug Zensical 0.0.41 : sur mobile, le sidebar primary reste visible derrière le burger. Fix dans `home.css` :

```css
@media (min-width: 76.25em) {
  /* Le sidebar n'est masqué que sur desktop, sinon il chevauche le burger mobile */
  .md-sidebar--primary { display: ...; }
}
```

### Accessibilité (a11y) — checklist appliquée

Le template phantom respecte explicitement :

| Critère | Implémentation |
|---------|----------------|
| **WCAG 2.3.3 Animation from Interactions** | `@media (prefers-reduced-motion: reduce)` désactive `home-fadeIn` + transitions tile (entrance, hover scale, content reveal). Voir bloc en bas de `home.css`. |
| **Focus visible** | `outline: 2px solid var(--md-accent-fg-color)` sur `.home-body a:focus-visible`, `outline: 3px solid #fff` sur `.home-tile > a:focus-visible` |
| **Contraste hero overlay** | `rgba(0,0,0,0.58)` au-dessus de l'image hero garantit un contraste >4.5:1 pour le texte blanc + `text-shadow` |
| **Tags décoratifs** | `aria-hidden="true"` sur `.home-tag` — l'info `tags:` est visuellement présente mais non annoncée par les screen readers (ce n'est pas un lien actionnable, juste une étiquette) |
| **Iframe sémantique** | `<section aria-labelledby="..."` ou `aria-label="..."` selon présence de `iframe_title:`, voir section précédente |
| **Touch / hover différenciés** | `@media (hover: hover)` pour le scale tile + reveal du content ; `@media (hover: none)` force `max-height: 15em; opacity: 1` sur `.home-tile__content` (sinon mobile = excerpt tronqué inutilement) |
| **Pas de hover-only** | Toutes les actions principales (clic sur tile entière) restent accessibles au tap, le hover n'est qu'un enrichissement visuel |

### Convention frontmatter pour la home

| Section enfant utilisant cette image | Source de l'image affichée |
|--------------------------------------|----------------------------|
| Section avec un `index.md` | `idx.meta.image` (image du frontmatter de l'index) |
| Page directe sous la racine | `section.meta.image` |
| Aucune image trouvée | `home-tile__image--placeholder` coloré (selon `style1`-`style6`) |

---

## 8. SEO : architecture et points d'extension

### Schema.org JSON-LD (depuis 0.6.5)

Le template phantom génère **2 blocs JSON-LD par sous-page**, **1 sur la home** :

| Page | Bloc 1 | Bloc 2 |
|------|--------|--------|
| Home | Type spécialisé (`WebSite` par défaut, ou `EducationalOrganization`/`NGO`/`Organization` selon `schema_type:`) avec `logo`, `sameAs`, `contactPoint`, `author` | — |
| Sous-page (général) | `WebPage` avec `isPartOf WebSite` | `BreadcrumbList` (depuis `page.ancestors`) |
| Sous-page Article | `Article` / `BlogPosting` avec `datePublished`, `author Person`, `image` | `BreadcrumbList` |
| Sous-page Event | `Event` avec `startDate`, `endDate`, `location Place`, `organizer Organization` | `BreadcrumbList` |

**Détection du type** (priorité décroissante) :

1. `page.meta.schema_type` (override explicite, gagne toujours)
2. `Event` si `page.meta.event_date` présent
3. `Article` si `page.meta.date` ET `page.meta.author`/`auteur·ice` présents
4. `WebPage` (fallback)

Ce système est conçu pour être **non-invasif** : sans rien faire dans les Docs source, le moteur produit un JSON-LD utile. Les éditeurs peuvent enrichir au cas par cas via les clés frontmatter du tableau précédent.

**Validation** : utiliser https://validator.schema.org/ et https://search.google.com/test/rich-results après chaque déploiement majeur.

### Mentions légales (auto-générées par défaut)

**Activées par défaut** dans tous les builds. Le moteur génère automatiquement :

1. Une page `mentions-legales/index.md` dans `content/source/{root_slug}/` avec un texte LCEN/RGPD pré-rédigé citant la **Coopérative Code Commun** comme entité technique. Les variables sont auto-remplies depuis le frontmatter racine et le `.env` :
   - `domain` ← `urlparse(SITE_URL).hostname`
   - `editor` ← `auteur·ice` ou `author` du frontmatter racine
   - `license` ← `licence` ou `license`
   - `platform` (GitHub/GitLab Pages) ← détecté depuis `repo_url`
   - `repo_url`, `docs_url` ← `.env`
2. Une entrée `{ "Mentions légales" = "mentions-legales/index.md" }` à la fin de la `nav` du `zensical.toml`
3. La clé `legal_url = "/mentions-legales/"` dans `[project.extra]` du toml
4. Le partial `overrides/partials/copyright.html` lit `config.extra.legal_url` → ajoute un lien `Mentions légales` dans le footer à côté du copyright

→ Footer : `Copyright … · Mentions légales · Made with Zensical`

**La page n'apparaît PAS dans la nav (header/sidebar)** — elle est volontairement orpheline pour ne pas polluer le menu. Elle est accessible via :
- Le **lien dans le footer** (toujours visible)
- L'**URL directe** `/mentions-legales/`
- Le **sitemap.xml** (l'URL y est injectée automatiquement par `_inject_sitemap_entry()` au moment du `--deploy`, pour que Google et les autres moteurs l'indexent)

**Désactivation / override** :

```yaml
# Frontmatter du doc racine Docs

# Désactiver complètement (pas de page, pas de lien footer)
---
legal_auto: non
---

# OU pointer vers une page Mentions légales custom rédigée par l'éditeur
# (la page auto NE sera PAS générée, le lien footer pointera vers cette URL)
---
legal_url: /ma-page-mentions-legales-personnalisee/
---
```

⚠️ Important pour Zensical : la section attendue est `[project.extra]`, **pas `[extra]`**. Zensical mappe `[project.extra]` sur la variable Jinja `config.extra`.

### Sources des balises HTML

| Balise | Source primaire | Fallback | Lieu de génération |
|--------|------------------|----------|---------------------|
| `<title>` | `page.meta.title` | `page.title` → `config.site_name` | `phantom/overrides/main.html::block htmltitle` |
| `<meta name="description">` | `page.meta.description` | `config.site_description` | Zensical natif `base.html` |
| `<meta name="author">` | `page.meta.author` | `config.site_author` | Zensical natif |
| `<link rel="canonical">` | `page.canonical_url` | — | Zensical natif (auto si `site_url` set) |
| `og:title` | `page.meta.title` | `page.title` → `site_name` | phantom `extrahead` |
| `og:description` | `page.meta.description` | `summary` → `excerpt` → `site_description` | phantom |
| `og:type` | `website` (home) / `article` (autres) | — | phantom |
| `og:url` | `page.canonical_url` | — | phantom |
| `og:image` | `page.meta.image` (préfixé `site_url`) | — | phantom |
| `twitter:*` | idem og | — | phantom |
| Schema.org `@type` | `WebSite` (home) / `WebPage` (autres) | — | phantom JSON-LD |
| Schema.org `url` | `page.canonical_url` | `site_url` | phantom |

### Génération `robots.txt` + `humans.txt`

`zensical_backend.py::_generate_seo_files()` :

```python
robots = "User-agent: *\nAllow: /\n"
if site_url:
    robots += f"Sitemap: {site_url}/sitemap.xml\n"

humans = """
/* TEAM */
{author}

/* SITE */
Last update: {today}
Generator: docs2static + Zensical
"""
```

Les deux fichiers sont écrits à la racine `content/`, ajoutés à `extra_files` du toml, et copiés dans `content/site/` au déploiement (ligne 840+ de `main.py`).

### Sitemap

**Généré nativement par Zensical** dans `content/site/sitemap.xml`. Aucun code custom requis. Liste toutes les pages depuis le `nav` du toml.

---

## 9. Déploiement Pages (SSH)

`deploy_zensical(base_dir, repo_url)` :

1. Convertit `https://github.com/Org/Repo` → `git@github.com:Org/Repo.git`
2. Build Zensical → `content/site/`
3. Copie `robots.txt` + `humans.txt` à la racine site/
4. **Génère `CNAME`** si domaine custom détecté (voir ci-dessous)
5. `git init` dans `content/site/` + `git add . + commit`
6. `git push --force HEAD:gh-pages` (ou `gl-pages` pour GitLab)

**Pré-requis** : clé SSH avec write access au dépôt cible (pas de password support).

**CI** : voir `.github/workflows/docs2static.yml` (cron quotidien 6h UTC).

### Domaine custom & CNAME

Quand le repo `gh-pages` est force-pushé, **tout son contenu est remplacé** — y compris le fichier `CNAME` que GitHub Pages utilise pour configurer un domaine custom (ex: `docs.example.fr`). Sans précaution, le domaine custom est perdu à chaque déploiement et l'URL retombe sur `org.github.io/repo/`.

`_write_cname_if_custom_domain(site_dir)` corrige ça :

- Lit `SITE_URL` de l'env (déjà documenté dans `env_example`)
- Extrait le hostname via `urllib.parse.urlparse`
- **Skip** si hostname ∈ {`*.github.io`, `*.gitlab.io`, `localhost`} → aucun CNAME nécessaire
- **Sinon** écrit `content/site/CNAME` avec le hostname (ex: `docs.example.fr\n`) avant le `git add`

Exemples :

| `SITE_URL` | CNAME écrit | Hostname |
|------------|-------------|----------|
| (vide) | non | — |
| `https://coopcodecommun.github.io/Docs2static/` | non | github.io ignoré |
| `https://example.gitlab.io/repo/` | non | gitlab.io ignoré |
| `http://localhost:8000/` | non | localhost ignoré |
| `https://docs.example.fr/` | oui | `docs.example.fr` |
| `https://my.docs.example.fr:443/path/` | oui | `my.docs.example.fr` (port + path strippés) |

⚠️ Côté **GitHub** : configurer le domaine custom une seule fois dans Settings → Pages → Custom domain. Le CNAME du repo doit aussi exister chez le registrar (enregistrement DNS pointant sur `org.github.io`). Notre fonction ne touche QUE le fichier `CNAME` du repo — pas la config DNS externe.

---

## 10. Pièges Zensical 0.0.41

### `page.content` peut contenir le YAML

Si le frontmatter ne se parse pas en YAML strict, Zensical garde le bloc dans `page.content`. Symptômes : `<hr /><p>auteur·ice: ...</p><hr />` rendu visiblement. **Solution** : toujours utiliser `yaml.safe_dump` côté moteur.

### Le bloc `htmltitle` natif duplique sur la home

Code natif (cf. `partials/...`) :
```jinja2
{% if page.meta and page.meta.title %}
    <title>{{ page.meta.title }} - {{ config.site_name }}</title>  ← duplique si égalité
{% elif page.title and not page.is_homepage %}
    ...
```

Sur la home, si `page.meta.title == site_name`, on a `<title>X - X</title>`. **Solution** : override avec test `page.is_homepage` en premier.

### Pas de gestion des listes YAML multi-lignes par notre parser custom

Le `extract_frontmatter_markdown` regarde uniquement les `key: value` mono-ligne. Les listes YAML (`tags:\n  - foo`) sont gérées via aliases CSV (`mots-cles: a, b, c`) puis converties en liste Python.

### `extra_files` non servi en dev

`zensical serve` ignore `extra_files`. Les fichiers (robots.txt, humans.txt) ne sont visibles qu'après `zensical build` ou `--deploy`.

### Watcher du dev server peut être confus

Quand on modifie le frontmatter de plusieurs fichiers simultanément, le watcher peut zapper certains. Force reload : `find content/source -name "*.md" -exec touch {} \;`.

### `page.meta.title` peut être `None`

Si le YAML parse mais sans clé `title`, `page.meta.title` est absente (undefined Jinja2). Toujours utiliser `page.meta.title or fallback`.

### H1 "Index" en fallback

Zensical injecte `<h1 id="__skip">{{ page.title | d(config.site_name, true) }}</h1>` si le contenu n'a pas de H1. Quand le toml ne configure pas de titre nav, fallback = "Index". **Solution** : préfixer le markdown avec `# {title}` côté moteur.

### H1 dupliqué si on cherche `^#\s` au lieu de `^#\s` MULTILINE

La détection "le markdown a-t-il déjà un H1 ?" doit utiliser `re.search(r'^#\s', clean_md, re.MULTILINE)`, pas `re.match(r'^\s*#\s', clean_md.lstrip())`. Cas réel : un markdown qui commence par `![image]()` puis `# Titre` était considéré comme "sans H1" → le moteur préfixait `# {title}` → résultat 2 H1 sur la page (anti-SEO). La regex multiline scanne TOUTES les lignes pour trouver un `# ` en début de ligne (sans matcher `## ` car le 2e caractère doit être un espace).

### Icône de page (favicon)

Zensical sert `assets/images/favicon.png` depuis ses assets internes. Pour personnaliser : ajouter `theme.favicon = "..."` dans `zensical.toml` ET copier le fichier. Pas géré par docs2static actuellement.

---

## 11. Choix d'architecture

### Pourquoi Zensical et pas MkDocs Material directement ?

Zensical = fork allégé de MkDocs Material (par les mêmes auteurs en partie). API plus propre, build plus rapide, focus sur l'écriture. Mais l'écosystème de plugins est plus pauvre. Pour Docs2Static, l'overhead est minimal (génération nav + copie assets).

### Pourquoi `requests-cache` SQLite ?

L'API Docs peut être lente et fragile. Cache 24h évite de re-fetch à chaque dev iteration. SQLite est portable, pas de dépendance Redis/Memcache.

### Pourquoi parser frontmatter custom et pas `python-frontmatter` ?

Historiquement : voulait éviter une dep tierce. Conséquence : ne gère pas les listes multi-lignes. Compromis OK pour des frontmatters simples.

**À envisager** : migrer vers `python-frontmatter` ou `yaml.safe_load` direct sur le bloc, ce qui supprimerait les bugs récurrents de parsing.

### Pourquoi `yaml.safe_dump` à la sortie ?

Garantit YAML 100% valide quels que soient les caractères dans les valeurs (`:`, `"`, accents, multi-ligne). Indispensable depuis qu'on injecte automatiquement `title:` qui peut contenir des caractères spéciaux.

### Pourquoi `importlib.resources` pour les templates ?

Permet de trouver les templates dans le wheel installé (`pip install docs2static`) sans avoir besoin de `__file__` ou de chemins relatifs. Robuste vis-à-vis du packaging.

### Pourquoi un slug par doc et pas l'UUID ?

URLs lisibles SEO-friendly. Les UUIDs des docs Docs sont opaques et non humains. Le slug est dérivé du titre via `slugify()`.

### Pourquoi `docs_dir = "source/zendocs-parent"` et pas `source/` direct ?

Le doc racine devient une "section" comme les autres dans la nav Zensical, et garde son propre `index.md` dédié. Sinon, conflit : Zensical attend `index.md` à la racine du `docs_dir`, mais on en a déjà un par section.

### Pourquoi des templates en `assets/` packagés et pas dans `overrides/` du repo ?

Pour qu'un utilisateur final qui fait `pip install docs2static` ait les templates par défaut sans cloner le repo. Les assets sont packagés dans le wheel via `[tool.hatch.build.targets.wheel] packages = ["docs2static"]`.

### Pourquoi pas de WebSocket / live reload custom ?

Zensical fournit déjà un dev server avec live reload (WebSocket dans `<script>` injecté en bas de chaque page). Inutile de réinventer.

---

## 12. Évolutions futures envisagées

### Backlog identifié à l'audit `/ui-ux-pro-max` (P3 non implémenté)

- **`noindex:` dans le frontmatter** → 3 lignes Jinja2 dans `extrahead` :
  ```jinja2
  {% if page.meta and page.meta.noindex %}
  <meta name="robots" content="noindex, nofollow">
  {% endif %}
  ```
  Cas d'usage : page interne, archive, draft sorti par accident.
- **`tile_color:` dans le frontmatter** → forcer la couleur d'une tile homepage au lieu du cycle `style1`→`style6` automatique. Permet `Agenda` toujours rose, `Qui sommes-nous` toujours bleu, indépendamment de l'ordre dans la nav.
- **`decoding="async"` + `aspect-ratio: 16/10`** sur les `<img>` des tiles → -CLS, -TBT (Core Web Vitals), pas de nouvelle clé frontmatter, juste optim HTML+CSS.

### Plus large

- **Migration `python-frontmatter`** pour supprimer les bugs de parsing custom (notre regex `key: value` ne gère pas les listes YAML multi-lignes)
- **Sitemap.xml priorisé** : ajouter `<priority>` et `<changefreq>` selon métadonnées
- **JSON-LD `BreadcrumbList`** : pour mieux apparaître en Rich Results Google
- **Plusieurs templates packagés** : `phantom`, `minimal`, `corporate`, sélectionnables via env `TEMPLATE`
- **Backend MkDocs Material direct** : pour ceux qui ne veulent pas de Zensical
- **Cache image dimensions** : pour ajouter `width`/`height` HTML aux balises `<img>` (CLS=0)
- **Tests sans API live** : recorder/replayer les réponses avec `responses` ou `vcrpy`
- **Webhook lasuite-docs** : rebuild auto sur édition d'un doc (vs cron quotidien)
- **`featured: true` / `hidden: true`** : prioriser/masquer une page dans la nav et la home
- **`og_image:` dédié** : différent du hero (ratio 1200×630 idéal pour partage social)
- **`schema_type:` Event/Article/FAQPage** : exposer Schema.org plus spécifique selon le type de contenu

---

## Références

- [Zensical docs](https://zensical.org/docs/)
- [MkDocs Material docs](https://squidfunk.github.io/mkdocs-material/) (Zensical = fork)
- [lasuite-docs API](https://docs.suite.anct.gouv.fr/) (instances ANCT)
- [Schema.org WebPage](https://schema.org/WebPage)
- [Open Graph protocol](https://ogp.me/)
- [robots.txt spec](https://www.robotstxt.org/)
