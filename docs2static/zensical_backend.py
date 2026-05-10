import os
import re
import subprocess
import shutil
import logging
import unicodedata
import importlib.resources
from urllib.parse import urlparse
from typing import Dict, Any, List

# On récupère le logger configuré dans le main
# We get the logger configured in main
logger = logging.getLogger("docs2static")

def slugify(text: str) -> str:
    """
    Transforme un titre en nom de dossier simple et propre.
    Turns a title into a simple and clean folder name.
    """
    if not text:
        return "sans-titre"
    
    # Enlève les accents / Remove accents
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    # Garde seulement les lettres, les chiffres et les espaces / Keep only letters, numbers, and spaces
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # Remplace les espaces par des tirets / Replace spaces with dashes
    text = re.sub(r'[-\s]+', '-', text)
    return text

def build_nav_structure(tree, base_docs_dir, current_rel_path=""):
    """
    Construit récursivement la structure de navigation pour Zensical.
    Vérifie si les fichiers existent pour ignorer les brouillons.
    Recursively builds the navigation structure for Zensical.
    Checks if files exist to ignore drafts.
    """
    nav = []
    for item in tree:
        title = item.get("title", "Sans titre")
        slug = slugify(title)
        # On construit le chemin relatif par rapport au dossier racine de la doc
        # Build the relative path from the documentation root
        rel_path = f"{current_rel_path}/{slug}" if current_rel_path else slug
        
        index_file = f"{rel_path}/index.md"
        full_path = os.path.join(base_docs_dir, index_file)
        
        # Si le fichier index.md n'existe pas, c'est probablement un draft ignoré
        # If index.md does not exist, it's likely an ignored draft
        if not os.path.exists(full_path):
            logger.info(f"Navigation : Document ignoré (fichier absent) : {index_file}")
            continue
            
        children = item.get("children", [])
        if children:
            # Si le document a des enfants, on crée une section
            # If the document has children, create a section
            child_nav = build_nav_structure(children, base_docs_dir, rel_path)
            section_nav = [index_file] + child_nav
            nav.append({title: section_nav})
        else:
            # Document simple
            # Simple document
            nav.append({title: index_file})
    return nav

def format_nav_to_toml(nav_list, base_docs_dir, indent=4):
    """
    Formate une liste de navigation en format TOML.
    Formats a navigation list into TOML format.
    """
    def _format_item(item, level):
        spaces = " " * (level * indent)
        if isinstance(item, str):
            return f'"{item}"'
        elif isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, str):
                    return f'{{ "{key}" = "{value}" }}'
                elif isinstance(value, list):
                    inner_indent = level + 1
                    inner_spaces = " " * (inner_indent * indent)
                    lines = [_format_item(v, inner_indent) for v in value]
                    inner_content = f",\n{inner_spaces}".join(lines)
                    return f'{{ "{key}" = [\n{inner_spaces}{inner_content}\n{spaces}] }}'
        return str(item)

    formatted_items = [_format_item(item, 1) for item in nav_list]
    content = ",\n    ".join(formatted_items)
    
    # On vérifie si l'index racine existe pour l'ajouter ou non
    # Check if the root index exists to add it or not
    root_index_exists = os.path.exists(os.path.join(base_docs_dir, "index.md"))
    if root_index_exists:
        if content:
            return f"nav = [\n    \"index.md\",\n    {content}\n]"
        else:
            return "nav = [\n    \"index.md\"\n]"
    else:
        return f"nav = [\n    {content}\n]"

def find_matching_bracket(text: str, start: int) -> int:
    """
    Trouve le crochet fermant correspondant au crochet ouvrant à la position start.
    Finds the closing bracket matching the opening bracket at position start.
    """
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i
    return -1

def setup_zensical_backend(base_dir: str, metadata: Dict[str, Any], title: str, root_docs_url: str = None, tree: List[Dict[str, Any]] = None, template_name: str = "phantom"):
    """
    Configure Zensical pour le dossier donné.
    Initialise le projet si nécessaire, puis met à jour la navigation et les métadonnées.
    Configures Zensical for the given directory.
    Initializes the project if needed, then updates navigation and metadata.
    """
    zensical_toml = os.path.join(base_dir, "zensical.toml")

    # Si le fichier n'existe pas encore, on initialise le projet Zensical
    # If the file doesn't exist yet, initialize the Zensical project
    if not os.path.exists(zensical_toml):
        # 1. Lance 'zensical new'
        # Run 'zensical new'
        logger.info(f"Initialisation de Zensical dans {base_dir}...")
        try:
            # On crée le dossier s'il n'existe pas / Create directory if it doesn't exist
            os.makedirs(base_dir, exist_ok=True)
            # On lance la commande zensical new / Run the zensical new command
            # On utilise 'uv run' pour être sûr d'avoir les dépendances
            subprocess.run(["uv", "run", "zensical", "new", base_dir], check=True, capture_output=True)

            # Zensical new crée un dossier 'docs' par défaut.
            # Comme on utilise 'source', on peut soit renommer 'source' en 'docs'
            # soit changer la config de zensical. Ici on va garder 'source'
            # et on va supprimer le dossier 'docs' vide créé par zensical new.
            docs_dir = os.path.join(base_dir, "docs")
            if os.path.exists(docs_dir):
                shutil.rmtree(docs_dir)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Zensical : {e}")
            return
    else:
        logger.info(f"Le fichier {zensical_toml} existe déjà, mise à jour de la navigation...")

    # 2. Met à jour zensical.toml avec les métadonnées
    # Update zensical.toml with metadata
    try:
        with open(zensical_toml, "r", encoding="utf-8") as f:
            toml_content = f.read()
            
            # On remplace les variables par défaut par celles des métadonnées
            # Replace default variables with metadata ones
            
            # site_name (depuis le titre ou metadata)
            site_name = metadata.get("site_name") or metadata.get("title") or title
            toml_content = re.sub(r'site_name\s*=\s*".*?"', f'site_name = "{site_name}"', toml_content)
            
            # site_description (depuis summary, résumé ou description)
            # site_description (from summary, résumé or description)
            site_desc = metadata.get("site_description") or metadata.get("summary") or metadata.get("résumé") or metadata.get("description") or "Documentation générée"
            toml_content = re.sub(r'site_description\s*=\s*".*?"', f'site_description = "{site_desc}"', toml_content)
            
            # site_author
            site_author = metadata.get("site_author") or metadata.get("auteur·ice") or metadata.get("author") or "Docs2Static"
            toml_content = re.sub(r'site_author\s*=\s*".*?"', f'site_author = "{site_author}"', toml_content)
            
            # repo_url (URL originale de DOCS)
            if root_docs_url:
                if re.search(r'repo_url\s*=', toml_content):
                    toml_content = re.sub(r'repo_url\s*=\s*".*?"', f'repo_url = "{root_docs_url}"', toml_content)
                else:
                    toml_content = toml_content.replace('[project]', f'[project]\nrepo_url = "{root_docs_url}"')

            # site_url (env SITE_URL en priorité, sinon dérivé du dépôt)
            # site_url (env SITE_URL takes priority, else derived from repo)
            repo_for_url = os.getenv("GITHUB_REPO") or os.getenv("GITLAB_REPO") or ""
            site_url = os.getenv("SITE_URL") or get_pages_url(repo_for_url)
            if site_url:
                if re.search(r'^#?\s*site_url\s*=', toml_content, re.MULTILINE):
                    toml_content = re.sub(r'^#?\s*site_url\s*=\s*".*?"', f'site_url = "{site_url}"', toml_content, flags=re.MULTILINE)
                else:
                    toml_content = toml_content.replace('[project]', f'[project]\nsite_url = "{site_url}"')

            # language (depuis metadata ou fallback "fr")
            # language (from metadata or fallback "fr")
            language = metadata.get("langue") or metadata.get("language") or "fr"
            toml_content = re.sub(r'language\s*=\s*".*?"', f'language = "{language}"', toml_content)

            # Auto-génération de la page Mentions légales
            # Activée par défaut, désactivable via legal_auto: non dans le frontmatter racine.
            # Si legal_url: est explicitement défini par l'utilisateur, on le respecte
            # et on ne génère pas de page (l'utilisateur pointe ailleurs).
            #
            # Auto-generate the Mentions légales (Legal notice) page.
            # Enabled by default, can be disabled via legal_auto: non in root frontmatter.
            # If legal_url: is explicitly set by the user, we respect it and skip
            # auto-generation (the user points elsewhere).
            _legal_auto_raw = str(metadata.get("legal_auto", "oui")).lower()
            _legal_auto_enabled = _legal_auto_raw not in ("non", "no", "false", "0", "off")
            should_auto_generate_legal = _legal_auto_enabled and not metadata.get("legal_url")
            if should_auto_generate_legal:
                metadata["legal_url"] = "/mentions-legales/"

            # legal_url : exposé dans [project.extra] pour le footer
            # (Zensical mappe [project.extra] sur config.extra dans Jinja)
            # legal_url: exposed in [project.extra] for the footer
            # (Zensical maps [project.extra] to config.extra in Jinja)
            legal_url = metadata.get("legal_url")
            if legal_url:
                if re.search(r'^\[project\.extra\]', toml_content, re.MULTILINE):
                    if re.search(r'^\s*legal_url\s*=', toml_content, re.MULTILINE):
                        toml_content = re.sub(r'^\s*legal_url\s*=\s*".*?"', f'legal_url = "{legal_url}"', toml_content, flags=re.MULTILINE)
                    else:
                        toml_content = re.sub(r'(^\[project\.extra\][^\[]*)', rf'\1legal_url = "{legal_url}"\n', toml_content, count=1, flags=re.MULTILINE)
                else:
                    toml_content += f'\n[project.extra]\nlegal_url = "{legal_url}"\n'

            # copyright
            license_val = metadata.get("licence") or metadata.get("license")
            author_val = metadata.get("auteur·ice") or metadata.get("author") or "The authors"
            
            if license_val:
                copyright_text = f"Copyright &copy; 2026 {author_val} - {license_val}"
            else:
                copyright_text = f"Copyright &copy; 2026 {author_val}"
            
            copyright_block = f'copyright = """\n{copyright_text}\n"""'
            # Utilise DOTALL pour capturer le bloc multi-ligne / Use DOTALL to capture multi-line block
            toml_content = re.sub(r'copyright\s*=\s*""".*?"""', copyright_block, toml_content, flags=re.DOTALL)
            
            # docs_dir pointe vers le dossier parent (seul le fichier originel)
            # docs_dir points to the parent folder (original file only)
            parent_slug = slugify(title)
            docs_dir_value = f"source/{parent_slug}"
            base_docs_dir = os.path.join(base_dir, docs_dir_value)
            
            if re.search(r'docs_dir\s*=', toml_content):
                toml_content = re.sub(r'docs_dir\s*=\s*".*?"', f'docs_dir = "{docs_dir_value}"', toml_content)
            else:
                toml_content = toml_content.replace('[project]', f'[project]\ndocs_dir = "{docs_dir_value}"')

            # Ajout de la navigation explicite si l'arbre est fourni
            # Add explicit navigation if tree is provided
            if tree:
                nav_list = build_nav_structure(tree, base_docs_dir)

                # Auto-génération du markdown Mentions légales SANS l'ajouter
                # à la nav. La page est accessible via le lien du footer
                # uniquement (URL directe `/mentions-legales/`). Zensical build
                # quand même les pages présentes dans `docs_dir` même si elles
                # ne sont pas listées dans `nav` (page "orpheline" tolérée).
                #
                # Auto-generate Legal notice markdown WITHOUT adding it to nav.
                # The page is reachable through the footer link only (direct
                # URL `/mentions-legales/`). Zensical still builds pages
                # present in `docs_dir` even when not listed in `nav`
                # (orphan page tolerated).
                if should_auto_generate_legal:
                    _generate_legal_notice(
                        base_docs_dir,
                        metadata,
                        site_url,
                        repo_for_url,
                        root_docs_url,
                    )

                nav_toml = format_nav_to_toml(nav_list, base_docs_dir)
                # Cherche le bloc nav existant (non commenté, en début de ligne)
                # Find existing nav block (not commented, at start of line)
                nav_match = re.search(r'^nav\s*=\s*\[', toml_content, re.MULTILINE)
                if nav_match:
                    # Trouve le crochet fermant correspondant (gère les crochets imbriqués)
                    # Find matching closing bracket (handles nested brackets)
                    bracket_start = nav_match.start() + toml_content[nav_match.start():].index('[')
                    bracket_end = find_matching_bracket(toml_content, bracket_start)
                    if bracket_end != -1:
                        toml_content = toml_content[:nav_match.start()] + nav_toml + toml_content[bracket_end + 1:]
                    else:
                        logger.warning("Impossible de trouver la fin du bloc nav, remplacement simple.")
                        toml_content = toml_content[:nav_match.start()] + nav_toml
                else:
                    # Ajoute sous la section [project] / Add under [project] section
                    toml_content = toml_content.replace('[project]', f'[project]\n{nav_toml}')

            # Vérifie/ajoute features = ["navigation.tabs"] dans [project.theme]
            # Verify/add features = ["navigation.tabs"] in [project.theme]
            if '[project.theme]' in toml_content:
                # Ajout du logo si présent dans les métadonnées
                # Add logo if present in metadata
                logo_file = metadata.get("logo")
                if logo_file:
                    # On supprime d'éventuelles lignes logo existantes (commentées ou non) pour éviter les doublons
                    # Remove any existing logo lines (commented or not) to avoid duplicates
                    toml_content = re.sub(r'\n#?logo\s*=\s*".*?"', '', toml_content)
                    # On l'ajoute proprement sous [project.theme]
                    # Add it cleanly under [project.theme]
                    toml_content = toml_content.replace('[project.theme]', f'[project.theme]\nlogo = "{logo_file}"')

                # Si navigation.tabs est présent mais commenté, on le décommente
                # If navigation.tabs is present but commented, uncomment it
                if '#"navigation.tabs"' in toml_content:
                    toml_content = toml_content.replace('#"navigation.tabs"', '"navigation.tabs"')
                
                # Si il n'est toujours pas présent (actif), on l'ajoute
                # If it's still not present (active), add it
                if '"navigation.tabs"' not in toml_content:
                    if re.search(r'features\s*=\s*\[', toml_content):
                        # On l'ajoute au début de la liste existante
                        # Add it to the start of the existing list
                        toml_content = re.sub(r'features\s*=\s*\[', 'features = ["navigation.tabs", ', toml_content)
                    else:
                        # On crée la ligne features sous [project.theme]
                        # Create the features line under [project.theme]
                        toml_content = toml_content.replace('[project.theme]', '[project.theme]\nfeatures = ["navigation.tabs"]')

                # Ajoute les boutons d'action (Edit et View)
                # Add action buttons (Edit and View)
                for feature in ["content.action.edit", "content.action.view"]:
                    # Si c'est commenté, on le décommente / If commented, uncomment it
                    pattern_commented = rf'#\s*"{re.escape(feature)}"'
                    if re.search(pattern_commented, toml_content):
                        toml_content = re.sub(pattern_commented, f'"{feature}"', toml_content)
                    elif f'"{feature}"' not in toml_content:
                        # Si absent, on l'ajoute / If missing, add it
                        if re.search(r'features\s*=\s*\[', toml_content):
                            toml_content = re.sub(r'features\s*=\s*\[', f'features = ["{feature}", ', toml_content)

                # On s'assure que navigation.sections est commenté
                # Ensure navigation.sections is commented out
                if '"navigation.sections"' in toml_content and '#"navigation.sections"' not in toml_content:
                    toml_content = toml_content.replace('"navigation.sections"', '#"navigation.sections"')

                # Ajoute/Met à jour les icônes d'action (pencil pour edit, eye pour view, file-pen pour repo)
                # Add/Update action icons (pencil for edit, eye for view, file-pen for repo)
                icon_section = '[project.theme.icon]'
                if f'#{icon_section}' in toml_content:
                    toml_content = toml_content.replace(f'#{icon_section}', icon_section)
                
                if icon_section not in toml_content:
                    # On l'ajoute avant la fin du fichier ou après [project.theme]
                    toml_content = toml_content.replace('[project.theme]', f'[project.theme]\n{icon_section}')
                
                for icon_key, icon_val in [("edit", "material/pencil"), ("view", "material/eye"), ("repo", "fontawesome/solid/file-pen")]:
                    pattern = rf'^#?{icon_key}\s*=\s*".*?"'
                    replacement = f'{icon_key} = "{icon_val}"'
                    if re.search(pattern, toml_content, re.MULTILINE):
                        toml_content = re.sub(pattern, replacement, toml_content, flags=re.MULTILINE)
                    else:
                        # On l'insère juste après la section [project.theme.icon]
                        toml_content = toml_content.replace(icon_section, f'{icon_section}\n{replacement}')

            # Copie des assets embarqués depuis templates/{template_name}/
            # Copy embedded assets from templates/{template_name}/
            assets_dir = importlib.resources.files("docs2static") / "assets" / "templates" / template_name

            # Copie récursive de overrides/ → content/overrides/
            # Préserve la structure des sous-dossiers (ex: partials/copyright.html)
            # Recursive copy of overrides/ → content/overrides/
            # Preserves subfolder structure (e.g. partials/copyright.html)
            overrides_dst = os.path.join(base_dir, "overrides")
            with importlib.resources.as_file(assets_dir / "overrides") as overrides_src:
                shutil.copytree(overrides_src, overrides_dst, dirs_exist_ok=True)
            logger.info(f"Assets overrides/ copiés vers : {overrides_dst}")

            # Copie stylesheets/ → content/source/{slug}/stylesheets/
            stylesheets_dst = os.path.join(base_docs_dir, "stylesheets")
            os.makedirs(stylesheets_dst, exist_ok=True)
            for f_name in ("home.css",):
                src = assets_dir / "stylesheets" / f_name
                dst = os.path.join(stylesheets_dst, f_name)
                with importlib.resources.as_file(src) as src_path:
                    shutil.copy2(src_path, dst)
                logger.info(f"Asset copié : {dst}")

            # Active custom_dir et extra_css dans le toml
            # Enable custom_dir and extra_css in toml
            if re.search(r'#\s*custom_dir\s*=', toml_content):
                toml_content = re.sub(r'#\s*custom_dir\s*=\s*".*?"', 'custom_dir = "overrides"', toml_content)
            elif 'custom_dir' not in toml_content:
                toml_content = toml_content.replace('[project.theme]', '[project.theme]\ncustom_dir = "overrides"')

            if re.search(r'#\s*extra_css\s*=', toml_content):
                toml_content = re.sub(r'#\s*extra_css\s*=\s*\[.*?\]', 'extra_css = ["stylesheets/home.css"]', toml_content)
            elif 'extra_css' not in toml_content:
                toml_content = toml_content.replace('[project]', '[project]\nextra_css = ["stylesheets/home.css"]')

            with open(zensical_toml, "w", encoding="utf-8") as f:
                f.write(toml_content)
            logger.info(f"Zensical configuré avec succès : {zensical_toml}")
            _generate_seo_files(base_dir, metadata, site_url)
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de zensical.toml : {e}")

def _inject_sitemap_entry(site_dir: str, site_url: str, page_path: str):
    """
    Injecte une URL dans sitemap.xml si elle n'y est pas deja.
    Sert pour les pages "orphelines" (pas dans la nav explicite) qui doivent
    quand meme etre indexees par les moteurs de recherche — typiquement les
    Mentions legales (visibles seulement dans le footer, pas dans le menu).

    Inject a URL into sitemap.xml if not already present.
    Used for "orphan" pages (not in explicit nav) that must still be indexed
    by search engines — typically the Legal notice page (visible only in the
    footer, not in the menu).
    """
    if not site_url or not page_path:
        return
    sitemap_path = os.path.join(site_dir, "sitemap.xml")
    if not os.path.exists(sitemap_path):
        logger.warning(f"sitemap.xml introuvable, skip injection : {sitemap_path}")
        return

    full_url = site_url.rstrip("/") + "/" + page_path.lstrip("/")
    if not full_url.endswith("/"):
        full_url += "/"

    with open(sitemap_path, "r", encoding="utf-8") as f:
        content = f.read()

    if full_url in content:
        return  # déjà présent

    new_entry = f"      <url>\n        <loc>{full_url}</loc>\n      </url>\n"
    if "</urlset>" in content:
        content = content.replace("</urlset>", new_entry + "</urlset>")
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Sitemap : URL ajoutée → {full_url}")


def _generate_legal_notice(
    base_docs_dir: str,
    metadata: Dict[str, Any],
    site_url: str,
    repo_url: str,
    docs_url: str,
):
    """
    Génère automatiquement la page Mentions légales conforme LCEN/RGPD,
    avec la Coopérative Code Commun comme entité technique.
    Le contenu est hardcodé : les sites Docs2Static publiés via cette
    fabrique ont tous Code Commun comme dev/maintenance et reposent sur
    la même stack (lasuite-docs + GitHub/GitLab Pages + iframes externes).
    Les variables (éditeur, licence, hébergement, source) sont dérivées
    du frontmatter racine et du .env.

    Auto-generates the Legal notice page (LCEN/RGPD compliant), with
    Coopérative Code Commun as the technical entity. The content is
    hardcoded since all Docs2Static sites published through this factory
    share the same stack. Variables (publisher, license, hosting, source)
    are derived from root frontmatter and .env.
    """
    from urllib.parse import urlparse
    import datetime

    legal_dir = os.path.join(base_docs_dir, "mentions-legales")
    os.makedirs(legal_dir, exist_ok=True)
    legal_path = os.path.join(legal_dir, "index.md")

    # Variables dérivées
    site_name = metadata.get("title") or metadata.get("titre") or "ce site"
    domain = urlparse(site_url).hostname or site_url or "ce site"
    author = metadata.get("auteur·ice") or metadata.get("author") or "l'éditeur du site"
    license_val = metadata.get("licence") or metadata.get("license") or "CC-BY-SA"
    year = datetime.date.today().year

    # Plateforme d'hébergement (déduite du repo)
    repo_lower = (repo_url or "").lower()
    if "gitlab.com" in repo_lower:
        platform = "GitLab Pages"
        platform_company = "GitLab Inc."
    else:
        platform = "GitHub Pages"
        platform_company = "GitHub Inc. (Microsoft Corporation), 88 Colin P. Kelly Jr Street, San Francisco, CA 94107, États-Unis"

    repo_clean = repo_url.rstrip("/") if repo_url else ""
    docs_clean = docs_url.rstrip("/") if docs_url else ""

    # Construction du markdown via yaml.safe_dump pour le frontmatter
    import yaml
    fm = {
        "titre": "Mentions légales",
        "description": f"Mentions légales du site {site_name}",
        "brouillon": "non",
        "noindex": "oui",
        "order": 999,
    }
    fm_yaml = yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)

    body = f"""# Mentions légales

## Éditeur du site

Le site **{domain}** est édité par **{author}**.

## Conception et développement technique

Site réalisé avec **[Docs2Static](https://github.com/CoopCodeCommun/Docs2static)**, un commun numérique développé par la **[Coopérative Code Commun](https://codecommun.coop)** (SCIC).

- Site : [codecommun.coop](https://codecommun.coop)
- Contact : [contact@codecommun.coop](mailto:contact@codecommun.coop)
- Logiciel libre : [github.com/CoopCodeCommun/Docs2static](https://github.com/CoopCodeCommun/Docs2static)
- Licence du moteur : Apache-2.0

## Hébergement

Le site est hébergé sur **{platform}**, fourni par {platform_company}.
"""

    if repo_clean:
        body += f"\nCode source du site : [{repo_clean}]({repo_clean})\n"

    body += "\n## Source des contenus\n"

    if docs_clean:
        body += (
            f"\nLes contenus sont rédigés et tenus à jour collaborativement "
            f"sur l'instance Docs : [{docs_clean}]({docs_clean})\n"
        )
    else:
        body += "\nLes contenus sont rédigés sur une instance la-suite Docs.\n"

    body += f"\nLicence par défaut des contenus : **{license_val}**.\n"

    body += """
## Données personnelles

Ce site est statique : il n'utilise pas de cookies de suivi, ne collecte aucune donnée personnelle et n'embarque aucun script tiers de tracking.

Les iframes embarquées (cartes, billetterie, formulaires externes, etc.) peuvent en revanche déposer des cookies relevant de leurs propres politiques de confidentialité.

## Droit applicable

Droit français — Article 6 de la Loi pour la Confiance dans l'Économie Numérique (LCEN).
"""

    body += f"\n---\n\n*Page générée automatiquement par Docs2Static — dernière mise à jour : {datetime.date.today().isoformat()}.*\n"
    _ = year  # unused but kept for future use

    with open(legal_path, "w", encoding="utf-8") as f:
        f.write(f"---\n{fm_yaml}---\n\n{body}")

    logger.info(f"Page Mentions légales générée : {legal_path}")


def _generate_seo_files(base_dir: str, metadata: Dict[str, Any], site_url: str):
    """Génère robots.txt et humans.txt à la racine du projet Zensical."""
    robots_path = os.path.join(base_dir, "robots.txt")
    sitemap_url = site_url.rstrip("/") + "/sitemap.xml" if site_url else ""
    robots_content = "User-agent: *\nAllow: /\n"
    if sitemap_url:
        robots_content += f"Sitemap: {sitemap_url}\n"
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)

    humans_path = os.path.join(base_dir, "humans.txt")
    author = metadata.get("auteur·ice") or metadata.get("author") or "The authors"
    humans_content = (
        "/* TEAM */\n"
        f"Creator: {author}\n\n"
        "/* SITE */\n"
        "Generator: Docs2Static (https://github.com/CoopCodeCommun/Docs2static)\n"
        "Language: fr\n"
    )
    with open(humans_path, "w", encoding="utf-8") as f:
        f.write(humans_content)

    for filename in ("robots.txt", "humans.txt"):
        _add_extra_file(os.path.join(base_dir, "zensical.toml"), filename)


def _add_extra_file(toml_path: str, filename: str):
    """Ajoute filename dans extra_files du zensical.toml si pas déjà présent."""
    if not os.path.exists(toml_path):
        return
    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()
    if filename in content:
        return
    if re.search(r'extra_files\s*=\s*\[', content):
        content = re.sub(
            r'(extra_files\s*=\s*\[)',
            f'\\1"{filename}", ',
            content
        )
    else:
        content = content.replace('[project]', f'[project]\nextra_files = ["{filename}"]')
    with open(toml_path, "w", encoding="utf-8") as f:
        f.write(content)


def get_pages_url(repo_url: str) -> str:
    """
    Calcule l'URL de la page (GitHub ou GitLab Pages) à partir de l'URL du dépôt.
    Calculates the Pages URL (GitHub or GitLab) from the repository URL.
    """
    if not repo_url:
        return ""
    
    # GitHub
    # Format SSH : git@github.com:User/Repo.git
    ssh_github = re.search(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
    if ssh_github:
        user, repo = ssh_github.groups()
        return f"https://{user}.github.io/{repo}/"
    
    # Format HTTPS : https://github.com/User/Repo
    https_github = re.search(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
    if https_github:
        user, repo = https_github.groups()
        return f"https://{user}.github.io/{repo}/"

    # GitLab
    # Format SSH : git@gitlab.com:User/Repo.git
    ssh_gitlab = re.search(r'git@gitlab\.com:([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
    if ssh_gitlab:
        user, repo = ssh_gitlab.groups()
        return f"https://{user}.gitlab.io/{repo}/"
    
    # Format HTTPS : https://gitlab.com/User/Repo
    https_gitlab = re.search(r'https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
    if https_gitlab:
        user, repo = https_gitlab.groups()
        return f"https://{user}.gitlab.io/{repo}/"
        
    return repo_url

def ensure_ssh_url(url: str) -> str:
    """
    Convertit une URL (GitHub ou GitLab) HTTPS en URL SSH si nécessaire.
    Converts a (GitHub or GitLab) HTTPS URL to an SSH URL if necessary.
    """
    if not url:
        return url
    
    # Si c'est déjà du SSH
    if url.startswith("git@") or "ssh://" in url:
        return url
        
    # GitHub
    gh_match = re.search(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', url)
    if gh_match:
        user, repo = gh_match.groups()
        return f"git@github.com:{user}/{repo}.git"

    # GitLab
    gl_match = re.search(r'https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?$', url)
    if gl_match:
        user, repo = gl_match.groups()
        return f"git@gitlab.com:{user}/{repo}.git"
        
    return url

def _write_cname_if_custom_domain(site_dir: str):
    """
    Écrit un fichier CNAME à la racine du site si SITE_URL pointe sur un domaine custom.
    Sans ce fichier, GitHub/GitLab Pages perd le domaine custom à chaque force-push.

    Writes a CNAME file at site root if SITE_URL points to a custom domain.
    Without this file, GitHub/GitLab Pages loses the custom domain on each force-push.
    """
    site_url = os.getenv("SITE_URL", "").strip()
    if not site_url:
        return

    hostname = urlparse(site_url).hostname
    if not hostname:
        return

    # Skip les domaines par défaut Pages : pas de CNAME nécessaire
    # Skip default Pages domains: no CNAME needed
    if hostname.endswith(".github.io") or hostname.endswith(".gitlab.io") or hostname == "localhost":
        return

    cname_path = os.path.join(site_dir, "CNAME")
    with open(cname_path, "w", encoding="utf-8") as f:
        f.write(f"{hostname}\n")
    logger.info(f"CNAME écrit pour domaine custom : {hostname}")


def deploy_zensical(base_dir: str, repo_url: str):
    """
    Lance le build de Zensical et déploie sur GitHub/GitLab Pages via SSH.
    Starts the Zensical build and deploys to GitHub/GitLab Pages via SSH.
    """
    if not repo_url:
        logger.error("Aucun dépôt spécifié pour le déploiement. Vérifiez GITHUB_REPO ou GITLAB_REPO dans .env")
        return

    # Détection de la plateforme / Platform detection
    is_gitlab = "gitlab.com" in repo_url.lower()
    platform = "GitLab" if is_gitlab else "GitHub"
    # Pour GitLab, on utilise souvent 'pages' ou la même branche que GitHub 'gh-pages'
    # Par simplicité on va utiliser 'gh-pages' par défaut pour les deux, 
    # ou 'pages' pour GitLab si c'est la convention
    branch = "gh-pages"
    if is_gitlab:
        branch = "gl-pages" # Convention suggérée pour différencier

    # S'assure que l'URL est au format SSH
    repo_url = ensure_ssh_url(repo_url)

    # 1. Construction du site
    logger.info(f"Lancement du build Zensical pour {platform}...")
    try:
        subprocess.run(["uv", "run", "zensical", "build"], cwd=base_dir, check=True)
        logger.info("Build Zensical terminé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors du build Zensical : {e}")
        return

    # Copie des fichiers SEO à la racine du site (extra_files non supporté par Zensical)
    site_dir = os.path.join(base_dir, "site")
    for seo_file in ("robots.txt", "humans.txt"):
        src = os.path.join(base_dir, seo_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(site_dir, seo_file))

    # CNAME pour domaine custom GitHub/GitLab Pages
    # CNAME for custom GitHub/GitLab Pages domain
    _write_cname_if_custom_domain(site_dir)

    # Injection de la page Mentions légales dans le sitemap.xml (orpheline)
    # Inject the Legal notice page into sitemap.xml (orphan, not in nav)
    site_url_env = os.getenv("SITE_URL", "").strip()
    if site_url_env:
        _inject_sitemap_entry(site_dir, site_url_env, "mentions-legales/")

    # 2. Déploiement
    site_dir = os.path.join(base_dir, "site")
    if not os.path.exists(site_dir):
        logger.error(f"Dossier de build non trouvé : {site_dir}")
        return

    logger.info(f"Préparation du déploiement vers {platform} : {repo_url}")
    try:
        subprocess.run(["git", "init"], cwd=site_dir, check=True, capture_output=True)
        
        try:
            subprocess.run(["git", "config", "user.name"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "config", "user.name", "Docs2Static Bot"], cwd=site_dir, check=True, capture_output=True)
            
        try:
            subprocess.run(["git", "config", "user.email"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "config", "user.email", "bot@docs2static.local"], cwd=site_dir, check=True, capture_output=True)

        subprocess.run(["git", "add", "."], cwd=site_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Déploiement automatique {platform} via Docs2Static"], cwd=site_dir, check=True, capture_output=True)
        
        logger.info(f"Envoi des fichiers vers {platform} (branche {branch})...")
        subprocess.run(["git", "push", "--force", repo_url, f"HEAD:{branch}"], cwd=site_dir, check=True, capture_output=True)
        
        logger.info(f"Déploiement sur {platform} Pages réussi !")
        
        # Affiche l'adresse de la page déployée
        pages_url = get_pages_url(repo_url)
        if pages_url:
            logger.info(f"Votre site est disponible à l'adresse : {pages_url}")
            if is_gitlab:
                logger.info(f"Note: Pour GitLab, assurez-vous d'avoir un fichier .gitlab-ci.yml configuré pour servir la branche {branch}.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution d'une commande Git : {e.stderr.decode() if e.stderr else e}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors du déploiement : {e}")
