# Handoff SEO — docs2static

## Contexte global

**Projet** : docs2static — outil Python qui fetch des docs (ANCT/lasuite-docs) et génère un site statique avec Zensical (MkDocs-based).  
**Version actuelle** : 0.6.3 (pyproject.toml)  
**Site de test local** : `http://localhost:8000/Docs2static/` (servi via `make serve` dans byobu pane 2.1)  
**Template actif** : `docs2static/assets/templates/phantom/overrides/main.html`

## État des tests

17 tests OK, 2 skipped — tout est vert. Ne pas casser.

```bash
cd /home/jonas/Gits/docs2static && uv run pytest tests/test_main.py -v
```

## Ce qui a déjà été fait (session précédente)

1. **Title tag** : override `{% block htmltitle %}` — homepage = site_name seul, autres pages = `page.title - site_name`
2. **Open Graph** : tags og:title, og:description, og:url, og:image déjà présents dans `main.html`
3. **Schema.org JSON-LD WebSite** : ajouté dans `extrahead`
4. **H1 unique** : hero `<h1>` → `<p class="home-title">` pour éviter double H1
5. **Double home-body** : premier div home-body en trop supprimé
6. **robots.txt + humans.txt** : générés par `zensical_backend.py::_generate_seo_files()`, copiés dans `content/site/` au déploiement

## Problèmes SEO restants à corriger

### 1. og:title — toutes les sous-pages affichent le site_name

**Symptôme** : `<meta property="og:title" content="ZenDocs : Parent">` sur TOUTES les pages.

**Cause** : dans `main.html` ligne 13 :
```jinja2
{% set page_title = page.meta.title or config.site_name %}
```
`page.meta.title` est le titre du frontmatter YAML (ex: `title: Mon titre`). Zensical expose aussi `page.title` qui est le titre H1 parsé. Les pages générées par docs2static ont le titre dans le frontmatter, donc ça devrait marcher — à vérifier si `page.meta.title` est bien rempli pour les sous-pages dans le build.

**Fix à implémenter** : utiliser `page.title` en priorité (plus fiable que `page.meta.title`) :
```jinja2
{% set page_title = page.title or page.meta.title or config.site_name %}
```

---

### 2. meta description — identique sur toutes les pages

**Symptôme** : `"des documents pour tester https://zensical.org/"` sur les 8 pages.

**Cause** : ligne 14 — `page.meta.summary or page.meta.excerpt or config.site_description`. Les sous-pages n'ont pas de `summary`/`excerpt` dans leur frontmatter.

**Fix à implémenter** : en dernier recours, utiliser le début du contenu de la page (premier paragraphe). Dans Jinja2/MkDocs on n'a pas accès direct au texte brut, mais `page.meta.description` peut exister. Ou passer par le moteur docs2static pour extraire automatiquement le premier paragraphe et l'injecter comme `excerpt` dans le frontmatter de chaque page.

Option A (template seul) — utiliser `page.meta.description` si disponible :
```jinja2
{% set page_desc = page.meta.description or page.meta.summary or page.meta.excerpt or config.site_description %}
```

Option B (moteur docs2static) — dans `main.py::process_document()`, extraire le premier paragraphe non-vide du markdown et l'injecter comme `excerpt:` dans le frontmatter si absent. **C'est l'option correcte.**

---

### 3. Schema.org url — toujours la racine du site

**Symptôme** : `"url": "https://coopcodecommun.github.io/Docs2static/"` sur toutes les pages.

**Cause** : ligne 44 dans main.html :
```jinja2
"url": "{{ base_url or page_url }}",
```
`base_url` est toujours défini (= config.site_url), donc `page_url` n'est jamais utilisé.

**Fix** :
```jinja2
"url": "{{ page_url or base_url }}",
```
Et utiliser `@type: WebPage` sur les sous-pages (WebSite seulement sur la home) :
```jinja2
{% if page.url == "" %}
"@type": "WebSite",
"url": "{{ base_url }}",
{% else %}
"@type": "WebPage",
"url": "{{ page_url }}",
{% endif %}
```

---

### 4. Images sans width/height (layout shift CLS)

**Symptôme** : toutes les `<img>` dans les tiles n'ont pas `width` et `height`.

**Cause** : on ne connaît pas les dimensions au moment du build template.

**Fix partiel acceptable** : ajouter `width="800" height="450"` comme valeur par défaut sur les images de tiles (ratio 16:9), ou plutôt forcer `aspect-ratio: 16/9` en CSS via la class `home-tile__image`. Pas de fix parfait sans traitement d'image au build.

**Fix CSS** (dans le stylesheet phantom, pas dans main.html) : ajouter
```css
.home-tile__image img { aspect-ratio: 16/9; width: 100%; height: auto; }
```
Fichier CSS : `docs2static/assets/templates/phantom/stylesheets/phantom.css`

---

### 5. Pages avec H1 = "Index"

**Symptôme** : 4 pages (agenda, premier-petit-enfant, dernier-petit-enfant, et-voici-un-n-4) ont `<h1>Index</h1>`.

**Cause** : Zensical (MkDocs) utilise le titre de navigation comme H1 de fallback quand la page markdown ne commence pas par un `# Titre`. Les pages enfants générées par docs2static commencent directement par le contenu sans répéter le titre en H1.

**Fix dans `main.py`** : dans `process_document()` ou `write_markdown_file()`, si le contenu markdown ne commence pas par `# `, ajouter `# {title}\n\n` au début du contenu avant de l'écrire.

```python
# Dans process_document() ou write_markdown_file()
if not content.lstrip().startswith('#'):
    content = f"# {title}\n\n{content}"
```

**Attention** : ne pas ajouter le H1 si le contenu possède déjà un heading (vérifier avec regex `^#\s` en multiline).

---

## Fichiers à modifier

| Fichier | Fixes |
|---------|-------|
| `docs2static/assets/templates/phantom/overrides/main.html` | og:title (fix 1), meta desc (fix 2 option A), Schema.org url (fix 3) |
| `docs2static/assets/templates/phantom/stylesheets/phantom.css` | aspect-ratio images tiles (fix 4) |
| `docs2static/main.py` | excerpt extraction (fix 2 option B), H1 injection (fix 5) |

## Workflow de test après fix

```bash
# Rebuild le site
make build   # ou : cd /home/jonas/Gits/docs2static && uv run python3 -m docs2static.main

# Vérifier SEO dans Chrome sur http://localhost:8000/Docs2static/
# Vérifier les sous-pages : /Docs2static/premier-enfant/ etc.

# Relancer les tests
uv run pytest tests/test_main.py -v
```

## Règles du projet

- **JAMAIS de git commit** — l'utilisateur commit lui-même
- **Ne pas modifier le contenu généré** dans `content/` — uniquement templates et moteur
- **Répondre en français**
- **Pas de sur-ingénierie** — résoudre exactement ce qui est demandé
