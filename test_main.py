#!/usr/bin/env python3
import unittest
import os
import shutil
import json
import sys
import main
from main import logger

class TestDocs2Static(unittest.TestCase):
    """
    Tests pour le programme Docs2Static utilisant des données réelles.
    Tests for the Docs2Static program using real data.
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Initialisation : définit l'URL de test et le dossier de sortie.
        Setup: defines the test URL and output folder.
        """
        cls.test_url = "https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/"
        cls.test_dir = "content_test"
        cls.base_url, cls.doc_id = main.parse_docs_url(cls.test_url)
        
        # Nettoyage au DÉBUT / Cleanup at the BEGINNING
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
            
        logger.info(f"Initialisation des tests avec l'URL : {cls.test_url}")
        logger.info("Note : Le cache est activé par défaut. Utilisez --no-cache pour le vider.")
        # Note: Cache is enabled by default. Use --no-cache to clear it.

    def test_slugify(self):
        """Vérifie la transformation des titres / Checks title transformation."""
        logger.info("Test: slugify (transformation des titres)")
        self.assertEqual(main.slugify("Hello World"), "hello-world")
        self.assertEqual(main.slugify("C'est l'été !"), "cest-lete")
        self.assertEqual(main.slugify(""), "sans-titre")
        logger.info("SUCCÈS: test_slugify")

    def test_parse_docs_url(self):
        """Vérifie l'analyse de l'URL / Checks URL parsing."""
        logger.info("Test: parse_docs_url (analyse de l'URL)")
        base_url, doc_id = main.parse_docs_url(self.test_url)
        self.assertEqual(base_url, "https://notes.liiib.re")
        self.assertEqual(doc_id, "fa5583b2-37fc-4016-998f-f5237fd41642")
        logger.info("SUCCÈS: test_parse_docs_url")

    def test_api_fetch_and_html_extraction(self):
        """
        Télécharge le contenu réel et teste l'extraction du frontmatter HTML.
        Fetches real content and tests HTML frontmatter extraction.
        """
        logger.info("Test: fetch_document_content + extract_frontmatter (HTML)")
        # Test de l'API / API test
        data = main.fetch_document_content(self.base_url, self.doc_id, "html")
        self.assertIn("content", data, "L'API devrait retourner un champ 'content'")
        
        # Test du moteur d'extraction / Extraction engine test
        fm, clean_content = main.extract_frontmatter(data["content"])
        
        self.assertEqual(fm.get("path"), "zendocs-parent")
        self.assertEqual(fm.get("auteur·ice"), "Jonas")
        self.assertEqual(fm.get("status"), "published")
        self.assertNotIn("---", clean_content, "Le bloc frontmatter devrait être retiré du contenu.")
        logger.info("SUCCÈS: test_api_fetch_and_html_extraction")

    def test_api_fetch_and_markdown_extraction(self):
        """
        Télécharge le contenu réel et teste l'extraction du frontmatter Markdown.
        Fetches real content and tests Markdown frontmatter extraction.
        """
        logger.info("Test: fetch_document_content + extract_frontmatter_markdown (Markdown)")
        # Identifiant du petit-enfant / ID of the grandchild
        gc_id = "0b4c67c5-f62f-45cc-80fd-a290cb04b384"
        
        # Test de l'API / API test
        data = main.fetch_document_content(self.base_url, gc_id, "markdown")
        self.assertIn("content", data)
        
        # Test du moteur d'extraction / Extraction engine test
        fm, clean_content = main.extract_frontmatter_markdown(data["content"])
        
        self.assertEqual(fm.get("path"), "zendocs-sous-sous-part1")
        self.assertEqual(fm.get("category"), "sous sous partie 1")
        self.assertNotIn("---", clean_content)
        logger.info("SUCCÈS: test_api_fetch_and_markdown_extraction")

    def test_full_integration_download(self):
        """
        Test d'intégration complet : vérifie que toute l'arborescence est bien créée.
        Full integration test: checks that the entire tree is correctly created.
        """
        logger.info("Test d'intégration: téléchargement complet de l'arborescence")
        # Lancement du traitement complet / Start full processing
        main.process_document(self.base_url, self.doc_id, parent_output_dir=self.test_dir, selected_format="both")
        
        # Vérification des 4 pages / Verification of the 4 pages
        # 1. Parent
        parent_dir = os.path.join(self.test_dir, "zendocs-parent")
        self.assertTrue(os.path.exists(parent_dir))
        
        # 2. Enfants
        child1_dir = os.path.join(parent_dir, "zendocs-sous-part1")
        child2_dir = os.path.join(parent_dir, "zendocs-sous-part2")
        self.assertTrue(os.path.exists(child1_dir))
        self.assertTrue(os.path.exists(child2_dir))
        
        # 3. Petit-enfant
        gc_dir = os.path.join(child1_dir, "zendocs-sous-sous-part1")
        self.assertTrue(os.path.exists(gc_dir))
        self.assertTrue(os.path.exists(os.path.join(gc_dir, "index.md")))
        
        # Vérification d'un fichier metadata.json réel
        with open(os.path.join(gc_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("category"), "sous sous partie 1")
        
        logger.info("SUCCÈS: test_full_integration_download")

if __name__ == "__main__":
    # Vérifie si l'utilisateur veut vider le cache avant les tests
    # Check if the user wants to clear the cache before tests
    if "--no-cache" in sys.argv:
        logger.warning("Option --no-cache détectée : Suppression du cache local...")
        main.session.cache.clear()
        # On retire l'argument pour ne pas perturber unittest
        sys.argv.remove("--no-cache")
        
    unittest.main()
