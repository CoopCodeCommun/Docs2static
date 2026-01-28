import os
import re
import subprocess
import shutil
import logging
import unicodedata
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

def build_nav_structure(tree, current_rel_path=""):
    """
    Construit récursivement la structure de navigation pour Zensical.
    Recursively builds the navigation structure for Zensical.
    """
    nav = []
    for item in tree:
        title = item.get("title", "Sans titre")
        slug = slugify(title)
        # On construit le chemin relatif par rapport au dossier racine de la doc
        # Build the relative path from the documentation root
        rel_path = f"{current_rel_path}/{slug}" if current_rel_path else slug
        
        index_file = f"{rel_path}/index.md"
        
        children = item.get("children", [])
        if children:
            # Si le document a des enfants, on crée une section
            # If the document has children, create a section
            child_nav = build_nav_structure(children, rel_path)
            section_nav = [index_file] + child_nav
            nav.append({title: section_nav})
        else:
            # Document simple
            # Simple document
            nav.append({title: index_file})
    return nav

def format_nav_to_toml(nav_list, indent=4):
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
    return f"nav = [\n    \"index.md\",\n    {content}\n]"

def setup_zensical_backend(base_dir: str, metadata: Dict[str, Any], title: str, root_docs_url: str = None, tree: List[Dict[str, Any]] = None):
    """
    Configure Zensical pour le dossier donné.
    Généré seulement s'il n'existe pas déjà.
    Configures Zensical for the given directory.
    Generated only if it doesn't already exist.
    """
    zensical_toml = os.path.join(base_dir, "zensical.toml")
    
    # Si le fichier existe déjà, on ne touche à rien
    # If the file already exists, we do nothing
    if os.path.exists(zensical_toml):
        logger.info(f"Le fichier {zensical_toml} existe déjà, skipping configuration.")
        return

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
            
            # site_description (depuis summary ou description)
            site_desc = metadata.get("site_description") or metadata.get("summary") or "Documentation générée"
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
            
            # Ajout de la navigation explicite si l'arbre est fourni
            # Add explicit navigation if tree is provided
            if tree:
                nav_list = build_nav_structure(tree)
                nav_toml = format_nav_to_toml(nav_list)
                if re.search(r'#?\s*nav\s*=', toml_content):
                    # Remplace une navigation existante (commentée ou non)
                    # Replace existing navigation (commented or not)
                    toml_content = re.sub(r'#?\s*nav\s*=\s*\[.*?\]', nav_toml, toml_content, flags=re.DOTALL)
                else:
                    # Ajoute sous la section [project] / Add under [project] section
                    toml_content = toml_content.replace('[project]', f'[project]\n{nav_toml}')

            # 3. Configuration de la navigation et du dossier source
            # Navigation and source directory configuration
            
            # docs_dir pointe vers le dossier parent (seul le fichier originel)
            # docs_dir points to the parent folder (original file only)
            parent_slug = slugify(title)
            docs_dir_value = f"source/{parent_slug}"
            
            if re.search(r'docs_dir\s*=', toml_content):
                toml_content = re.sub(r'docs_dir\s*=\s*".*?"', f'docs_dir = "{docs_dir_value}"', toml_content)
            else:
                toml_content = toml_content.replace('[project]', f'[project]\ndocs_dir = "{docs_dir_value}"')

            # Vérifie/ajoute features = ["navigation.tabs"] dans [project.theme]
            # Verify/add features = ["navigation.tabs"] in [project.theme]
            if '[project.theme]' in toml_content:
                # Ajout du logo si présent dans les métadonnées
                # Add logo if present in metadata
                logo_file = metadata.get("logo_file")
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

            with open(zensical_toml, "w", encoding="utf-8") as f:
                f.write(toml_content)
            logger.info(f"Zensical configuré avec succès : {zensical_toml}")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de zensical.toml : {e}")

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
