import os
import re
import subprocess
import shutil
import logging
import unicodedata
from typing import Dict, Any

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

def setup_zensical_backend(base_dir: str, metadata: Dict[str, Any], title: str):
    """
    Configure Zensical pour le dossier donné.
    Configures Zensical for the given directory.
    """
    zensical_toml = os.path.join(base_dir, "zensical.toml")
    
    # 1. Vérifie si zensical.toml existe, sinon lance 'zensical new'
    # Check if zensical.toml exists, otherwise run 'zensical new'
    if not os.path.exists(zensical_toml):
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
        if os.path.exists(zensical_toml):
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

                # On s'assure que navigation.sections est commenté
                # Ensure navigation.sections is commented out
                if '"navigation.sections"' in toml_content and '#"navigation.sections"' not in toml_content:
                    toml_content = toml_content.replace('"navigation.sections"', '#"navigation.sections"')

            with open(zensical_toml, "w", encoding="utf-8") as f:
                f.write(toml_content)
            logger.info(f"Zensical configuré avec succès : {zensical_toml}")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de zensical.toml : {e}")

def get_github_pages_url(github_repo: str) -> str:
    """
    Calcule l'URL de la page GitHub Pages à partir de l'URL du dépôt.
    Calculates the GitHub Pages URL from the repository URL.
    """
    if not github_repo:
        return ""
    
    # On gère le format SSH : git@github.com:User/Repo.git
    # Handle SSH format
    ssh_match = re.search(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', github_repo)
    if ssh_match:
        user, repo = ssh_match.groups()
        return f"https://{user}.github.io/{repo}/"
    
    # On gère le format HTTPS : https://github.com/User/Repo
    # Handle HTTPS format
    https_match = re.search(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', github_repo)
    if https_match:
        user, repo = https_match.groups()
        return f"https://{user}.github.io/{repo}/"
        
    return github_repo

def ensure_ssh_url(url: str) -> str:
    """
    Convertit une URL GitHub HTTPS en URL SSH si nécessaire pour éviter les demandes de mot de passe.
    Converts a GitHub HTTPS URL to an SSH URL if necessary to avoid password prompts.
    """
    if not url:
        return url
    
    # Si c'est déjà du SSH (commence par git@ ou contient un format ssh)
    # If it's already SSH
    if url.startswith("git@") or "ssh://" in url:
        return url
        
    # Si c'est du HTTPS GitHub, on le transforme / If it's HTTPS GitHub, transform it
    # Exemple : https://github.com/User/Repo.git -> git@github.com:User/Repo.git
    match = re.search(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', url)
    if match:
        user, repo = match.groups()
        ssh_url = f"git@github.com:{user}/{repo}.git"
        logger.info(f"Conversion de l'URL HTTPS en SSH pour le déploiement : {ssh_url}")
        return ssh_url
        
    return url

def deploy_zensical(base_dir: str, github_repo: str):
    """
    Lance le build de Zensical et déploie sur GitHub Pages via SSH.
    Starts the Zensical build and deploys to GitHub Pages via SSH.
    """
    if not github_repo:
        logger.error("Aucun dépôt GitHub spécifié pour le déploiement. Vérifiez GITHUB_REPO dans .env")
        # No GitHub repository specified for deployment. Check GITHUB_REPO in .env
        return

    # S'assure que l'URL est au format SSH pour éviter les prompts interactifs
    # Ensures the URL is in SSH format to avoid interactive prompts
    github_repo = ensure_ssh_url(github_repo)

    # 1. Construction du site / Site build
    logger.info("Lancement du build Zensical...")
    try:
        # On lance 'zensical build' dans le dossier du contenu
        # Runs 'zensical build' in the content directory
        subprocess.run(["uv", "run", "zensical", "build"], cwd=base_dir, check=True)
        logger.info("Build Zensical terminé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors du build Zensical : {e}")
        return

    # 2. Déploiement vers GitHub Pages / Deployment to GitHub Pages
    site_dir = os.path.join(base_dir, "site")
    if not os.path.exists(site_dir):
        logger.error(f"Dossier de build non trouvé : {site_dir}")
        return

    logger.info(f"Préparation du déploiement vers : {github_repo}")
    try:
        # On initialise un dépôt git temporaire dans le dossier 'site'
        # Initializes a temporary git repo in the 'site' folder
        subprocess.run(["git", "init"], cwd=site_dir, check=True, capture_output=True)
        
        # On essaie d'utiliser la configuration globale de l'utilisateur
        # Try to use the global user configuration
        # Si non définie, on met une valeur par défaut pour éviter que le commit échoue
        # If not defined, set a default value to prevent commit failure
        try:
            subprocess.run(["git", "config", "user.name"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "config", "user.name", "Docs2Static Bot"], cwd=site_dir, check=True, capture_output=True)
            
        try:
            subprocess.run(["git", "config", "user.email"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "config", "user.email", "bot@docs2static.local"], cwd=site_dir, check=True, capture_output=True)

        subprocess.run(["git", "add", "."], cwd=site_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Déploiement automatique via Docs2Static"], cwd=site_dir, check=True, capture_output=True)
        
        # On pousse de force vers la branche gh-pages du dépôt distant
        # Force push to the gh-pages branch of the remote repository
        logger.info("Envoi des fichiers vers GitHub (branche gh-pages)...")
        subprocess.run(["git", "push", "--force", github_repo, "HEAD:gh-pages"], cwd=site_dir, check=True, capture_output=True)
        
        logger.info("Déploiement sur GitHub Pages réussi !")
        
        # Affiche l'adresse de la page déployée / Show the deployed page URL
        pages_url = get_github_pages_url(github_repo)
        if pages_url:
            logger.info(f"Votre site est disponible à l'adresse : {pages_url}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution d'une commande Git : {e.stderr.decode() if e.stderr else e}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors du déploiement : {e}")
