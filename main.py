import os
import requests
import json
import re
import argparse
import urllib.parse
import unicodedata
import time
from typing import Dict, Any, List, Tuple

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
    print(f"Téléchargement du format {content_format} pour {doc_id}...")
    
    # Envoie la demande / Send the request
    response = requests.get(url)
    # Vérifie si ça a fonctionné / Check if it worked
    response.raise_for_status()
    # Renvoie les données en format JSON / Return data in JSON format
    return response.json()

def fetch_document_children(base_url: str, parent_id: str) -> List[Dict[str, Any]]:
    """
    Récupère la liste des documents enfants d'un document parent.
    Gets the list of child documents for a parent document.
    """
    # Adresse pour voir les enfants / Address to see children
    url = get_docs_api_url(base_url, f"/documents/{parent_id}/children/")
    print(f"Recherche des documents enfants pour {parent_id}...")
    
    response = requests.get(url)
    response.raise_for_status()
    # Renvoie la liste des enfants / Return the list of children
    return response.json().get("results", [])

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
    match = re.search(r'^<p>---</p>(.*?)<p>---</p>', content, re.DOTALL)
    if match:
        raw_info = match.group(1)
        # Trouve chaque paire "clé: valeur" / Find each "key: value" pair
        items = re.findall(r'<p>([a-z0-9_-]+)\:\s(.+?)</p>', raw_info, re.IGNORECASE)
        for key, value in items:
            frontmatter[key.lower()] = value
        # Enlève ce bloc du texte principal / Remove this block from the main text
        content = content[match.end():]
    
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
        items = re.findall(r'^([a-z0-9_-]+)\:\s(.+)$', raw_info, re.MULTILINE)
        for key, value in items:
            frontmatter[key.lower()] = value
        content = content[match.end():]
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
    print(f"Fichier enregistré : {file_path}")

def process_document(base_url: str, doc_id: str, parent_output_dir: str = "content", processed_ids: set = None):
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

        # 1. Télécharge la version HTML / Download HTML version
        html_data = fetch_document_content(base_url, doc_id, "html")
        title = html_data.get("title") or "Sans titre"
        html_content = html_data.get("content") or ""
        
        # Extrait les métadonnées et nettoie le HTML / Extract metadata and clean HTML
        frontmatter, clean_html = extract_frontmatter(html_content)
        
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
        if "image" not in frontmatter:
            img_match = re.search(r'^<img\s+[^>]*src="([^"]+)"', clean_html)
            if img_match:
                frontmatter["image"] = img_match.group(1)

        time.sleep(0.1)

        # 2. Télécharge la version Markdown / Download Markdown version
        md_data = fetch_document_content(base_url, doc_id, "markdown")
        md_content = md_data.get("content") or ""
        md_frontmatter, clean_md = extract_frontmatter_markdown(md_content)
        
        # Fusionne toutes les métadonnées / Merge all metadata
        final_frontmatter = {**md_frontmatter, **frontmatter}
        
        # 3. Organise les dossiers / Organize folders
        # Utilise le titre pour nommer le dossier / Use the title to name the folder
        folder_name = slugify(title)
        
        # Si le document a un chemin spécifique dans ses réglages, on peut l'utiliser
        # If the document has a specific path in its settings, we can use it
        if "path" in final_frontmatter:
             folder_name = final_frontmatter["path"]
             
        # Chemin complet vers le dossier du document / Full path to the document folder
        doc_dir = os.path.join(parent_output_dir, folder_name)
        
        # 4. Enregistre les fichiers / Save the files
        save_file(os.path.join(doc_dir, "index.html"), clean_html)
        save_file(os.path.join(doc_dir, "index.md"), clean_md)
        save_file(os.path.join(doc_dir, "metadata.json"), 
                  json.dumps(final_frontmatter, indent=2, ensure_ascii=False))
        
        time.sleep(0.1)

        # 5. S'occupe des documents enfants (récursivité) / Handle child documents (recursion)
        children = fetch_document_children(base_url, doc_id)
        for child in children:
            # On passe le dossier actuel comme dossier parent pour les enfants
            # We pass the current folder as the parent folder for the children
            process_document(base_url, child["id"], doc_dir, processed_ids)

    except Exception as e:
        print(f"Erreur avec le document {doc_id} : {e}")

def main():
    """
    Fonction principale qui démarre le programme.
    Main function that starts the program.
    """
    # Gère les arguments donnés lors du lancement / Handle arguments given at launch
    parser = argparse.ArgumentParser(description="Télécharge des documents de Docs et les range.")
    parser.add_argument("urls", nargs="*", help="Adresses des documents (ex: https://docs.example.com/docs/id/)")
    
    args = parser.parse_args()
    
    if not args.urls:
        # Si aucune adresse n'est donnée, utilise des exemples
        # If no address is given, use examples
        print("Aucune adresse donnée, utilisation des exemples...")
        example_ids = [
            "0b65cc5b-2d72-408a-b5c1-0ff8d2a7a479", # Guide CMS
            "2b04cc16-fa34-4f50-a8e3-ee3e073d226e"  # Exemple avec frontmatter
        ]
        base_url = "https://docs.suite.anct.gouv.fr"
        for doc_id in example_ids:
            process_document(base_url, doc_id)
    else:
        # Pour chaque adresse donnée / For each given address
        for url in args.urls:
            try:
                base_url, doc_id = parse_docs_url(url)
                process_document(base_url, doc_id)
            except ValueError as e:
                print(e)

if __name__ == "__main__":
    main()
