#!/usr/bin/env python3
import os
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

def fetch_document_tree(base_url: str, doc_id: str) -> List[Dict[str, Any]]:
    """
    Construit l'arbre généalogique complet des documents enfants.
    Builds the complete genealogy tree of child documents.
    """
    # On récupère d'abord les enfants directs / Get immediate children first
    immediate_children = fetch_document_children(base_url, doc_id)
    
    # Pour chaque enfant, on regarde s'il a lui-même des enfants
    # For each child, check if they have children themselves
    for child in immediate_children:
        # On attend un tout petit peu entre chaque branche / Wait a bit between each branch
        time.sleep(0.1)
        
        # L'API nous donne 'numchild', le nombre d'enfants directs
        # The API gives us 'numchild', the number of direct children
        num_children = child.get("numchild", 0)
        
        if num_children > 0:
            # Si il y a des enfants, on descend récursivement
            # If there are children, we go down recursively
            child["children"] = fetch_document_tree(base_url, child["id"])
        else:
            # Sinon, la liste est vide / Otherwise, the list is empty
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

def process_document(base_url: str, doc_id: str, parent_output_dir: str = "content", processed_ids: set = None, selected_format: str = "both", children_list: List[Dict[str, Any]] = None):
    """
    Traite un document et tous ses enfants de façon organisée.
    Processes a document and all its children in an organized way.
    """
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
        
        # Si le document a un chemin spécifique dans ses réglages, on peut l'utiliser
        # If the document has a specific path in its settings, we can use it
        if "path" in final_frontmatter:
             folder_name = final_frontmatter["path"]
             
        # Chemin complet vers le dossier du document / Full path to the document folder
        doc_dir = os.path.join(parent_output_dir, folder_name)
        
        logger.info(f"Traitement du document : {title} ({doc_id}) -> {doc_dir}")

        # 4. Enregistre les fichiers si ils ont été téléchargés
        # Save the files if they were downloaded
        if clean_html:
            save_file(os.path.join(doc_dir, "index.html"), clean_html)
        if clean_md:
            save_file(os.path.join(doc_dir, "index.md"), clean_md)
        
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
            
        for child in children_list:
            # On passe les enfants déjà trouvés au prochain appel pour éviter de refaire l'appel API
            # This avoids N+1 problems by using already fetched data
            # On passe le dossier actuel comme dossier parent pour les enfants
            process_document(
                base_url, 
                child["id"], 
                doc_dir, 
                processed_ids, 
                selected_format=selected_format,
                children_list=child.get("children", [])
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
        "urls", 
        nargs="*", 
        help="""
        Liste des URLs des documents à télécharger.
        List of document URLs to download.
        Exemple : https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/
        """
    )
    
    args = parser.parse_args()
    
    if args.no_cache:
        # Vide le cache si demandé / Clear cache if requested
        logger.warning("Suppression du cache local...")
        session.cache.clear()

    if not args.urls:
        # Si aucune adresse n'est donnée, utilise des exemples
        # If no address is given, use examples
        logger.info("Aucune adresse donnée, utilisation des exemples...")
        example_ids = [
            "fa5583b2-37fc-4016-998f-f5237fd41642", # Exemple du test
        ]
        base_url = "https://notes.liiib.re/docs"
        for doc_id in example_ids:
            process_document(base_url, doc_id, selected_format=args.format)
    else:
        # Pour chaque adresse donnée / For each given address
        for url in args.urls:
            try:
                base_url, doc_id = parse_docs_url(url)
                process_document(base_url, doc_id, selected_format=args.format)
            except ValueError as e:
                logger.error(e)

if __name__ == "__main__":
    main()
