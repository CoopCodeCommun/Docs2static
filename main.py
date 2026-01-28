#!/usr/bin/env python3
import os
import shutil
from dotenv import load_dotenv
import requests_cache
import http.cookiejar
import json
import re
import argparse
import urllib.parse
import unicodedata
import time
import logging
import colorlog
from typing import Dict, Any, List, Tuple

# Import des backends / Backend imports
from zensical_backend import setup_zensical_backend, deploy_zensical, slugify

def setup_logger():
    """
    Configure un logger efficace et coloré.
    Sets up an efficient and colored logger.
    """
    # Format des messages / Message format
    # %(log_color)s ajoute de la couleur selon le niveau (INFO, ERROR, etc.)
    # %(log_color)s adds color based on the level
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger("docs2static")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

# Initialisation du logger / Logger initialization
logger = setup_logger()

# Chargement des variables d'environnement / Loading environment variables
load_dotenv()

# Utilisation d'une session avec cache pour éviter de surcharger le serveur
# On garde les résultats pendant 24 heures par défaut
# cache_control=False permet de forcer le cache même si le serveur envoie des cookies
# Using a cached session to avoid overloading the server
# We keep results for 24 hours by default
# cache_control=False forces caching even if the server sends cookies
session = requests_cache.CachedSession(
    'docs_cache',
    backend='sqlite',
    expire_after=86400,  # 24 heures / 24 hours
    cache_control=False
)
# Désactive les cookies pour garantir que les requêtes restent identiques (évite le Vary: Cookie)
# Disable cookies to ensure requests stay identical (avoids Vary: Cookie issues)
session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))

def parse_docs_url(url: str) -> Tuple[str, str]:
    """
    Extrait l'adresse du site et l'identifiant du document à partir d'une URL.
    Extracts the website address and the document ID from a URL.
    """
    # Analyse l'URL pour séparer les parties / Analyze the URL to separate parts
    parsed = urllib.parse.urlparse(url)
    # Reconstruit l'adresse de base (ex: https://docs.example.com) / Rebuild base address
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Cherche l'identifiant dans le chemin (ex: /docs/identifiant/)
    # Search for the ID in the path (e.g., /docs/id/)
    match = re.search(r'/docs/([^/]+)', parsed.path)
    if not match:
        # Si c'est juste un identifiant de 36 caractères / If it's just a 36-char ID
        if re.match(r'^[a-f0-9-]{36}$', url):
             return "https://docs.suite.anct.gouv.fr", url
        # Erreur si l'URL n'est pas reconnue / Error if URL not recognized
        raise ValueError(f"Impossible de trouver l'identifiant dans l'URL : {url}")
    
    return base_url, match.group(1)

def get_docs_api_url(base_url: str, path: str) -> str:
    """
    Crée une adresse pour appeler l'API de Docs.
    Creates an address to call the Docs API.
    """
    return f"{base_url}/api/v1.0{path}"


def fetch_document_content(base_url: str, doc_id: str, content_format: str = "html") -> Dict[str, Any]:
    """
    Télécharge le contenu d'un document depuis l'API.
    Downloads the content of a document from the API.
    """
    # Prépare l'adresse de téléchargement / Prepare the download address
    url = get_docs_api_url(base_url, f"/documents/{doc_id}/content/?content_format={content_format}")
    
    # Envoie la demande / Send the request
    response = session.get(url)
    
    # Si le serveur est surchargé, on attend un peu
    # If the server is overloaded, we wait a bit
    if response.status_code == 429:
        logger.warning(f"Le serveur demande de ralentir (429) pour {doc_id}. Attente de 2 secondes...")
        time.sleep(2)
        response = session.get(url)

    # Vérifie si ça a fonctionné / Check if it worked
    response.raise_for_status()
    
    # Affiche si la requête vient du cache ou du réseau
    # Shows if the request comes from cache or network
    source = "CACHE" if response.from_cache else "RÉSEAU"
    logger.info(f"[{source}] Téléchargement {content_format} : {doc_id}")

    # Renvoie les données en format JSON / Return data in JSON format
    return response.json()

def fetch_document_children(base_url: str, parent_id: str) -> List[Dict[str, Any]]:
    """
    Récupère la liste des documents enfants d'un document parent (niveau immédiat).
    Gets the list of immediate child documents for a parent document.
    """
    # Adresse pour voir les enfants / Address to see children
    url = get_docs_api_url(base_url, f"/documents/{parent_id}/children/")
    
    response = session.get(url)
    
    # Gestion du cas où le serveur est surchargé
    # Handling case where the server is overloaded
    if response.status_code == 429:
        logger.warning(f"Le serveur demande de ralentir (429) pour {parent_id}. Attente de 2 secondes...")
        time.sleep(2)
        response = session.get(url)

    response.raise_for_status()

    # Affiche si la requête vient du cache ou du réseau
    # Shows if the request comes from cache or network
    source = "CACHE" if response.from_cache else "RÉSEAU"
    logger.info(f"[{source}] Recherche enfants pour : {parent_id}")

    # Renvoie la liste des enfants / Return the list of children
    return response.json().get("results", [])

def fetch_document_details(base_url: str, doc_id: str) -> Dict[str, Any]:
    """
    Récupère les détails d'un document (pour avoir son path et autres infos).
    Fetches document details (to get its path and other info).
    """
    url = get_docs_api_url(base_url, f"/documents/{doc_id}/")
    response = session.get(url)
    
    if response.status_code == 429:
        time.sleep(2)
        response = session.get(url)
        
    response.raise_for_status()
    source = "CACHE" if response.from_cache else "RÉSEAU"
    logger.info(f"[{source}] Détails du document : {doc_id}")
    
    return response.json()

def fetch_document_descendants(base_url: str, doc_id: str) -> List[Dict[str, Any]]:
    """
    Récupère TOUS les descendants d'un document via la nouvelle API optimisée.
    Fetches ALL descendants of a document via the new optimized API.
    """
    # 1. On tente d'abord la route suggérée /documents/all/
    # Try the suggested route first
    for param in ["ancestor", "id"]:
        all_url = get_docs_api_url(base_url, f"/documents/all/?{param}={doc_id}")
        try:
            response = session.get(all_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("count", 0) > 0:
                    source = "CACHE" if response.from_cache else "RÉSEAU"
                    logger.info(f"[{source}] Récupération groupée via /all/ (param={param}) pour : {doc_id}")
                    return data.get("results", [])
        except Exception:
            pass

    # 2. On tente la route standard /documents/{id}/descendants/
    # Try the standard descendants route
    url = get_docs_api_url(base_url, f"/documents/{doc_id}/descendants/")
    
    results = []
    try:
        while url:
            response = session.get(url)
            
            if response.status_code == 404:
                return None if not results else results
                
            if response.status_code == 429:
                time.sleep(2)
                response = session.get(url)
                
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))
            
            # Gestion de la pagination / Handling pagination
            url = data.get("next")
            
        if results:
            source = "CACHE" if response.from_cache else "RÉSEAU"
            logger.info(f"[{source}] Récupération groupée via /descendants/ pour : {doc_id}")
            return results
            
        return None
    except Exception as e:
        logger.warning(f"Impossible d'utiliser l'API optimisée : {e}")
        return None

def fetch_document_tree(base_url: str, doc_id: str) -> List[Dict[str, Any]]:
    """
    Construit l'arbre généalogique complet des documents enfants de façon optimisée.
    Builds the complete genealogy tree of child documents in an optimized way.
    """
    # 1. On tente d'abord de récupérer tous les descendants d'un coup
    # Try to fetch all descendants at once first
    all_descendants = fetch_document_descendants(base_url, doc_id)
    
    if all_descendants is not None:
        # Si ça a marché, on reconstruit l'arbre localement à partir des 'path'
        # If it worked, rebuild the tree locally using 'path'
        root_doc = fetch_document_details(base_url, doc_id)
        root_path = root_doc.get("path")
        
        if not root_path:
            logger.warning(f"Le document racine {doc_id} n'a pas de path. Abandon de l'optimisation.")
            return fetch_document_children(base_url, doc_id) # On renvoie au moins les enfants directs
        
        # On indexe les docs par leur path pour les retrouver vite
        # Index docs by path for quick lookup
        docs_by_path = {root_path: root_doc}
        root_doc["children"] = []
        
        # On initialise les enfants de chaque descendant
        # Initialize children for each descendant
        for d in all_descendants:
            d["children"] = []
            docs_by_path[d["path"]] = d
            
        # On range chaque document chez son parent
        # Put each document under its parent
        for d in all_descendants:
            path = d["path"]
            # Sur Docs, le parent a un path qui est le préfixe (7 chars en moins)
            # On Docs, parent path is the prefix (7 chars less)
            parent_path = path[:-7]
            if parent_path in docs_by_path:
                docs_by_path[parent_path]["children"].append(d)
                
        # On renvoie la liste des enfants du document racine
        # Return the list of children of the root document
        return root_doc.get("children", [])

    # 2. Méthode de secours (récursive) si l'API optimisée n'est pas disponible
    # Fallback recursive method if optimized API is not available
    logger.info(f"Utilisation de la méthode récursive pour : {doc_id}")
    immediate_children = fetch_document_children(base_url, doc_id)
    
    for child in immediate_children:
        time.sleep(0.1)
        num_children = child.get("numchild", 0)
        if num_children > 0:
            child["children"] = fetch_document_tree(base_url, child["id"])
        else:
            child["children"] = []
            
    return immediate_children

def extract_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """
    Extrait les informations spéciales (metadata) du texte HTML.
    Extracts special info (metadata) from the HTML text.
    """
    frontmatter = {}
    # Enlève les paragraphes vides au début / Remove empty paragraphs at the start
    content = re.sub(r'^(<p></p>)+', '', content)
    
    # Cherche les infos entre deux lignes "---"
    # Search for info between two "---" lines
    match = re.search(r'^<p>---\s*</p>(.*?)<p>---\s*</p>', content, re.DOTALL | re.IGNORECASE)
    if match:
        raw_info = match.group(1)
        # Trouve chaque paire "clé: valeur" / Find each "key: value" pair
        # Utilise un regex plus souple pour les clés (caractères spéciaux, Unicode)
        # Use a more flexible regex for keys (special characters, Unicode)
        items = re.findall(r'<p>(.+?)\s*:\s*(.+?)</p>', raw_info, re.IGNORECASE)
        for key, value in items:
            frontmatter[key.strip().lower()] = value.strip()
        # Enlève ce bloc du texte principal / Remove this block from the main text
        content = content[match.end():].lstrip()
    
    return frontmatter, content

def extract_frontmatter_markdown(content: str) -> Tuple[Dict[str, str], str]:
    """
    Extrait les informations spéciales du texte Markdown.
    Extracts special info from the Markdown text.
    """
    frontmatter = {}
    # Cherche les infos entre "---" en début de fichier
    # Search for info between "---" at the start of the file
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        raw_info = match.group(1)
        # Trouve les paires "clé: valeur" / Find "key: value" pairs
        # Supporte les lignes vides et les caractères spéciaux dans les clés
        # Supports blank lines and special characters in keys
        items = re.findall(r'^\s*([^:]+?)\s*:\s*(.+)$', raw_info, re.MULTILINE)
        for key, value in items:
            frontmatter[key.strip().lower()] = value.strip()
        content = content[match.end():].lstrip()
    return frontmatter, content

def save_file(file_path: str, content: str):
    """
    Enregistre le texte dans un fichier sur l'ordinateur.
    Saves the text into a file on the computer.
    """
    # Crée les dossiers si ils n'existent pas / Create folders if they don't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # Écrit le fichier / Write the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Fichier enregistré : {file_path}")

def download_and_replace_images(content: str, doc_dir: str, content_type: str = "markdown") -> Tuple[str, str]:
    """
    Cherche les images, les télécharge et remplace les URLs par le fichier local.
    Retourne le contenu modifié et éventuellement le nom du fichier logo trouvé.
    Searches for images, downloads them, and replaces URLs with the local file.
    Returns the modified content and optionally the logo filename found.
    """
    if not content:
        return content, None

    logo_filename = None

    # On cherche les images Markdown : ![alt](url)
    # Search for Markdown images
    if content_type == "markdown":
        # Regex pour trouver ![texte](url)
        pattern = r'!\[(.*?)\]\((https?://.*?)\)'
        
        def md_replacer(match):
            nonlocal logo_filename
            alt, url = match.groups()
            try:
                # Extrait le nom du fichier / Extract filename
                filename = os.path.basename(urllib.parse.urlparse(url).path)
                if not filename: return match.group(0)
                
                local_path = os.path.join(doc_dir, filename)
                os.makedirs(doc_dir, exist_ok=True)
                
                # Téléchargement via la session avec cache
                # Download via cached session
                img_res = session.get(url)
                if img_res.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_res.content)
                    source = "CACHE" if img_res.from_cache else "RÉSEAU"
                    logger.info(f"[{source}] Image localisée : {filename}")
                    
                    # On prend la première image rencontrée comme logo
                    # We take the first image encountered as the logo
                    if not logo_filename:
                        logo_filename = filename
                        
                    return f"![{alt}]({filename})"
                return match.group(0)
            except Exception as e:
                logger.error(f"Erreur image Markdown {url} : {e}")
                return match.group(0)
        
        new_content = re.sub(pattern, md_replacer, content)

        return new_content, logo_filename

    # On cherche les images HTML : <img src="url">
    # Search for HTML images
    else:
        # Regex pour trouver <img ... src="url" ...>
        pattern = r'<img\s+([^>]*?)src="(https?://.*?)"([^>]*?)>'
        
        def html_replacer(match):
            nonlocal logo_filename
            before, url, after = match.groups()
            try:
                filename = os.path.basename(urllib.parse.urlparse(url).path)
                if not filename: return match.group(0)
                
                local_path = os.path.join(doc_dir, filename)
                os.makedirs(doc_dir, exist_ok=True)
                
                img_res = session.get(url)
                if img_res.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_res.content)
                    source = "CACHE" if img_res.from_cache else "RÉSEAU"
                    logger.info(f"[{source}] Image localisée : {filename}")
                    
                    # On prend la première image rencontrée comme logo
                    # We take the first image encountered as the logo
                    if not logo_filename:
                        logo_filename = filename

                    return f'<img {before}src="{filename}"{after}>'
                return match.group(0)
            except Exception as e:
                logger.error(f"Erreur image HTML {url} : {e}")
                return match.group(0)
                
        new_content = re.sub(pattern, html_replacer, content)

        return new_content, logo_filename

def process_document(base_url: str, doc_id: str, parent_output_dir: str = "content/source", processed_ids: set = None, selected_format: str = "both", children_list: List[Dict[str, Any]] = None, backend: str = None, order: int = 0):
    """
    Traite un document et tous ses enfants de façon organisée.
    Processes a document and all its children in an organized way.
    """
    # Si le backend est zensical, on force le format markdown uniquement
    # If the backend is zensical, we force markdown format only
    if backend == "zensical" and selected_format != "markdown":
        selected_format = "markdown"

    # Initialise la liste des documents déjà faits / Initialize the list of done documents
    if processed_ids is None:
        processed_ids = set()
    
    # Si on a déjà fait ce document, on s'arrête / If already done, stop
    if doc_id in processed_ids:
        return
    processed_ids.add(doc_id)

    try:
        # On attend un petit peu pour ne pas fatiguer le serveur
        # We wait a little bit not to exhaust the server
        time.sleep(0.2)

        # Variables pour stocker les résultats / Variables to store results
        title = "Sans titre"
        final_frontmatter = {}
        clean_html = ""
        clean_md = ""

        # 1. Télécharge la version HTML si demandée / Download HTML version if requested
        if selected_format in ["html", "both"]:
            html_data = fetch_document_content(base_url, doc_id, "html")
            title = html_data.get("title") or title
            html_content = html_data.get("content") or ""
            
            # Extrait les métadonnées et nettoie le HTML / Extract metadata and clean HTML
            html_frontmatter, clean_html = extract_frontmatter(html_content)
            final_frontmatter.update(html_frontmatter)
            
            # Convertit les balises spéciales comme <accordion-list>
            # Converts special tags like <accordion-list>
            for tag in ["accordion-list"]:
                clean_html = re.sub(
                    rf'<p>&lt;{tag}&gt;</p>(.*?)<p>&lt;/{tag}&gt;</p>',
                    rf'<{tag}>\1</{tag}>',
                    clean_html,
                    flags=re.DOTALL
                )
            
            # Cherche une image si elle n'est pas déjà dans les métadonnées
            # Looks for an image if not already in metadata
            if "image" not in final_frontmatter:
                img_match = re.search(r'^<img\s+[^>]*src="([^"]+)"', clean_html)
                if img_match:
                    final_frontmatter["image"] = img_match.group(1)

            time.sleep(0.1)

        # 2. Télécharge la version Markdown si demandée / Download Markdown version if requested
        if selected_format in ["markdown", "both"]:
            md_data = fetch_document_content(base_url, doc_id, "markdown")
            title = md_data.get("title") or title
            md_content = md_data.get("content") or ""
            
            # Extrait les métadonnées et nettoie le Markdown / Extract metadata and clean Markdown
            md_frontmatter, clean_md = extract_frontmatter_markdown(md_content)
            final_frontmatter.update(md_frontmatter)
            
            time.sleep(0.1)
        
        # 3. Organise les dossiers / Organize folders
        # Utilise le titre pour nommer le dossier / Use the title to name the folder
        folder_name = slugify(title)
        
        # Chemin complet vers le dossier du document / Full path to the document folder
        doc_dir = os.path.join(parent_output_dir, folder_name)
        
        # 3.5 Traitement des images / Image processing
        logo_filename = None
        if clean_html:
            clean_html, html_logo = download_and_replace_images(clean_html, doc_dir, "html")
            logo_filename = logo_filename or html_logo
        if clean_md:
            clean_md, md_logo = download_and_replace_images(clean_md, doc_dir, "markdown")
            logo_filename = logo_filename or md_logo
        
        # Si un logo a été trouvé, on l'ajoute aux métadonnées temporairement pour le backend
        # If a logo was found, add it to metadata temporarily for the backend
        if logo_filename:
            final_frontmatter["logo_file"] = logo_filename
        
        # Si une image est dans les métadonnées, on la localise aussi
        # If an image is in metadata, localize it too
        if "image" in final_frontmatter and final_frontmatter["image"].startswith("http"):
            url = final_frontmatter["image"]
            try:
                img_filename = os.path.basename(urllib.parse.urlparse(url).path)
                if img_filename:
                    img_local_path = os.path.join(doc_dir, img_filename)
                    os.makedirs(doc_dir, exist_ok=True)
                    img_res = session.get(url)
                    if img_res.status_code == 200:
                        with open(img_local_path, "wb") as f:
                            f.write(img_res.content)
                        final_frontmatter["image"] = img_filename
                        logger.info(f"Image de couverture localisée : {img_filename}")
            except Exception as e:
                logger.error(f"Erreur image metadata {url} : {e}")

        logger.info(f"Traitement du document : {title} ({doc_id}) -> {doc_dir}")

        # 4. Enregistre les fichiers si ils ont été téléchargés
        # Save the files if they were downloaded
        if clean_html:
            save_file(os.path.join(doc_dir, "index.html"), clean_html)
        
        if clean_md:
            # Ajout de l'URL d'édition aux métadonnées pour Zensical
            # Add the edit URL to metadata for Zensical
            final_frontmatter["edit_url"] = f"{base_url}/docs/{doc_id}/"
            
            # Reconstruit le bloc frontmatter en Markdown pour index.md
            # Rebuild the Markdown frontmatter block for index.md
            md_with_fm = "---\n"
            for key, value in final_frontmatter.items():
                # On évite de mettre des objets complexes si il y en a
                # Avoid adding complex objects if any
                if isinstance(value, (str, int, float)):
                    md_with_fm += f"{key}: {value}\n"
            md_with_fm += "---\n\n"
            
            # Ajout du titre en tant que titre H1 au début du contenu
            # Add the title as H1 heading at the beginning of the content
            md_with_fm += f"# {title}\n\n"
            
            md_with_fm += clean_md
            
            save_file(os.path.join(doc_dir, "index.md"), md_with_fm)
        
        # 4.5 Configuration du backend si c'est le premier document
        # Backend configuration if it's the first document
        if len(processed_ids) == 1 and backend:
            # Si on n'a pas encore la liste des enfants, on construit l'arbre généalogique
            # nécessaire pour la navigation
            # If we don't have the children list yet, build the genealogy tree
            # needed for navigation
            if children_list is None:
                logger.info(f"Construction de la généalogie pour {doc_id}...")
                children_list = fetch_document_tree(base_url, doc_id)

            # On remonte d'un cran par rapport à 'source'
            # Go up one level from 'source'
            base_content_dir = os.path.dirname(parent_output_dir)
            if backend.lower() == "zensical":
                # L'URL racine est l'URL du premier document
                root_docs_url = f"{base_url}/docs/{doc_id}/"
                setup_zensical_backend(base_content_dir, final_frontmatter, title, root_docs_url=root_docs_url, tree=children_list)

        # 4.6 Nettoyage et sauvegarde des métadonnées
        # Metadata cleanup and saving
        
        # Ajoute le titre officiel aux métadonnées / Add official title to metadata
        final_frontmatter["title"] = title
        
        # Ajoute l'ordre d'apparition / Add appearance order
        final_frontmatter["order"] = order
        
        # On retire les champs temporaires ou inutiles pour le stockage final dans metadata.json
        # Remove temporary or unnecessary fields for final storage in metadata.json
        for field in ["path", "logo_file", "edit_url"]:
            if field in final_frontmatter:
                del final_frontmatter[field]

        # Enregistre toujours les métadonnées / Always save metadata
        save_file(os.path.join(doc_dir, "metadata.json"), 
                  json.dumps(final_frontmatter, indent=2, ensure_ascii=False))

        time.sleep(0.1)

        # 5. S'occupe des documents enfants (récursivité) / Handle child documents (recursion)
        # Si on n'a pas encore la liste des enfants, on construit l'arbre généalogique
        # If we don't have the children list yet, build the genealogy tree
        if children_list is None:
            logger.info(f"Construction de la généalogie pour {doc_id}...")
            children_list = fetch_document_tree(base_url, doc_id)
            
        for i, child in enumerate(children_list):
            # On passe les enfants déjà trouvés au prochain appel pour éviter de refaire l'appel API
            # This avoids N+1 problems by using already fetched data
            # On passe le dossier actuel comme dossier parent pour les enfants
            process_document(
                base_url, 
                child["id"], 
                doc_dir, 
                processed_ids, 
                selected_format=selected_format,
                children_list=child.get("children", []),
                backend=backend,
                order=i
            )

    except Exception as e:
        logger.error(f"Erreur avec le document {doc_id} : {e}")

def main():
    """
    Fonction principale qui démarre le programme.
    Main function that starts the program.
    """
    # Gère les arguments donnés lors du lancement / Handle arguments given at launch
    parser = argparse.ArgumentParser(
        description="""
        Télécharge des documents depuis Docs (BlockNote) vers un format statique (HTML/Markdown).
        Downloads documents from Docs (BlockNote) to a static format (HTML/Markdown).
        
        Ce programme recrée l'arborescence des pages et télécharge les contenus.
        This program recreates the page hierarchy and downloads the content.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )
    
    # Support pour la faute de frappe mentionnée dans la consigne
    # Support for the typo mentioned in the instructions
    parser.add_argument("--hlep", action="help", help=argparse.SUPPRESS)
    
    parser.add_argument(
        "--format", "-f",
        choices=["html", "markdown", "both"],
        default="both",
        help="""
        Format de téléchargement : html, markdown ou both (les deux par défaut).
        Download format: html, markdown or both (default).
        """
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="""
        Ne pas utiliser le cache et forcer le téléchargement depuis le serveur.
        Do not use cache and force download from the server.
        """
    )

    parser.add_argument(
        "--backend", "-b",
        choices=["zensical"],
        default=os.getenv("BACKEND"),
        help="""
        Moteur de site statique à utiliser pour la configuration (peut être défini via BACKEND dans .env).
        Static site generator backend to use for configuration (can be set via BACKEND in .env).
        """
    )

    parser.add_argument(
        "--deploy", "-d",
        action="store_true",
        help="""
        Lance le build et le déploiement vers GitHub Pages après le téléchargement.
        Starts the build and deployment to GitHub Pages after downloading.
        """
    )

    parser.add_argument(
        "urls", 
        nargs="*", 
        help="""
        Liste des URLs des documents à télécharger.
        List of document URLs to download.
        Exemple : https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/
        """
    )
    
    args = parser.parse_args()
    
    # Si le backend est zensical, on force le format markdown uniquement
    # If the backend is zensical, we force markdown format only
    if args.backend == "zensical" and args.format != "markdown":
        logger.info("Backend Zensical détecté : Forçage du format Markdown uniquement.")
        args.format = "markdown"

    if args.no_cache:
        # Vide le cache si demandé / Clear cache if requested
        logger.warning("Suppression du cache local...")
        session.cache.clear()

    if not args.urls:
        # Si aucune adresse n'est donnée, utilise le .env ou des exemples
        # If no address is given, use .env or examples
        env_url = os.getenv("DOCS_URL")
        if env_url:
            logger.info(f"Utilisation de l'URL du fichier .env : {env_url}")
            args.urls = [env_url]
        else:
            logger.info("Aucune adresse donnée, utilisation des exemples...")
            args.urls = ["https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/"]
    
    # Si l'option deploy est désactivée, on procède au téléchargement
    # Conformément à la consigne, on ne télécharge pas si on déploie
    # If deploy option is disabled, we proceed to download
    # As per instructions, we don't download if we are deploying
    if not args.deploy:
        # Nettoyage du dossier source avant le nouveau téléchargement
        # Cleaning the source folder before the new download
        source_dir = "content/source"
        if os.path.exists(source_dir):
            logger.info(f"Nettoyage du dossier source : {source_dir}")
            shutil.rmtree(source_dir)

        # Pour chaque adresse donnée / For each given address
        for i, url in enumerate(args.urls):
            try:
                base_url, doc_id = parse_docs_url(url)
                process_document(base_url, doc_id, selected_format=args.format, backend=args.backend, order=i)
            except ValueError as e:
                logger.error(e)
    else:
        logger.info("Option --deploy détectée : Utilisation des fichiers locaux existants (pas de téléchargement).")
            
    # Si l'option deploy est activée / If deploy option is enabled
    if args.deploy:
        if args.backend == "zensical":
            # On récupère l'adresse du dépôt depuis le .env (GitHub ou GitLab)
            # Get the repo address from .env (GitHub or GitLab)
            repo_url = os.getenv("GITHUB_REPO") or os.getenv("GITLAB_REPO")
            deploy_zensical("content", repo_url)
        else:
            logger.warning("Le déploiement n'est pas encore supporté pour ce backend.")
            # Deployment is not yet supported for this backend.

if __name__ == "__main__":
    main()
