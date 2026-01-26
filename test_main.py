#!/usr/bin/env python3
import unittest
import os
import shutil
import json
import sys
import re
import main
from main import logger

class TestDocs2Static(unittest.TestCase):
    """
    Tests pour le programme Docs2Static utilisant des données réelles.
    Tests for the Docs2Static program using real data.
    """
    
    # Variable pour activer le déploiement réel pendant les tests
    # Variable to enable real deployment during tests
    run_deploy = False
    
    @classmethod
    def setUpClass(cls):
        """
        Initialisation : définit l'URL de test et le dossier de sortie.
        Setup: defines the test URL and output folder.
        """
        # On utilise TEST_DOCS_URL si présent, sinon l'URL par défaut
        # Use TEST_DOCS_URL if present, otherwise default URL
        cls.test_url = os.getenv("TEST_DOCS_URL", "https://notes.liiib.re/docs/fa5583b2-37fc-4016-998f-f5237fd41642/")
        cls.test_dir = "content_test"
        cls.source_dir = os.path.join(cls.test_dir, "source")
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

    def test_env_loading(self):
        """Vérifie le chargement des variables d'environnement / Checks env var loading."""
        logger.info("Test: chargement des variables .env")
        # On vérifie que les variables de test définies dans le .env sont bien présentes
        # Check that test variables from .env are present
        self.assertEqual(os.getenv("TEST_BACKEND"), "zensical")
        self.assertIn("fa5583b2-37fc-4016-998f-f5237fd41642", os.getenv("TEST_DOCS_URL"))
        self.assertIn("git@github.com", os.getenv("TEST_GITHUB_REPO"))
        logger.info("SUCCÈS: test_env_loading")

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
        
        self.assertEqual(fm.get("auteur·ice"), "Coopérative Code Commun")
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
        
        self.assertEqual(fm.get("category"), "sous sous partie 1")
        self.assertNotIn("---", clean_content)
        logger.info("SUCCÈS: test_api_fetch_and_markdown_extraction")

    def test_full_integration_download(self):
        """
        Test d'intégration complet : vérifie que toute l'arborescence est bien créée.
        Full integration test: checks that the entire tree is correctly created.
        """
        logger.info("Test d'intégration: téléchargement complet de l'arborescence (avec Zensical)")
        # Lancement du traitement complet / Start full processing
        # Note: on demande "both" mais le script devrait forcer "markdown" à cause du backend zensical
        backend = os.getenv("TEST_BACKEND", "zensical")
        main.process_document(self.base_url, self.doc_id, parent_output_dir=self.source_dir, selected_format="both", backend=backend)
        
        # Vérification des 4 pages / Verification of the 4 pages
        # 1. Parent
        parent_dir = os.path.join(self.source_dir, "zendocs-parent")
        self.assertTrue(os.path.exists(parent_dir))
        self.assertFalse(os.path.exists(os.path.join(parent_dir, "index.html")), "Le fichier HTML ne devrait pas exister avec le backend Zensical")
        self.assertTrue(os.path.exists(os.path.join(parent_dir, "index.md")))
        
        # Vérification des images / Verification of images
        img1 = "9a08b49e-498f-49c9-a3ac-dcf1c9c59292.png"
        img2 = "70cd180e-e3fa-4e80-a79a-36ec46b11743.jpg"
        self.assertTrue(os.path.exists(os.path.join(parent_dir, img1)), f"L'image {img1} devrait être téléchargée")
        self.assertTrue(os.path.exists(os.path.join(parent_dir, img2)), f"L'image {img2} devrait être téléchargée")
        
        # Vérification des liens dans le markdown
        with open(os.path.join(parent_dir, "index.md"), "r", encoding="utf-8") as f:
            md_content = f.read()
            self.assertIn(f"![badge\\_grenoble.png]({img1})", md_content)
            self.assertIn(f"![help-freestockpro-3036405.fhd.jpg]({img2})", md_content)
            self.assertNotIn("https://notes.liiib.re/media/", md_content)
        
        # 2. Enfants
        child1_dir = os.path.join(parent_dir, "premier-enfant-sous-partie")
        child2_dir = os.path.join(parent_dir, "second-enfant-deuxieme-sous-partie")
        self.assertTrue(os.path.exists(child1_dir))
        self.assertTrue(os.path.exists(child2_dir))
        self.assertFalse(os.path.exists(os.path.join(child1_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(child1_dir, "index.md")))
        
        # 3. Petit-enfant
        gc_dir = os.path.join(child1_dir, "petit-enfant-sous-sous-partie")
        self.assertTrue(os.path.exists(gc_dir))
        self.assertFalse(os.path.exists(os.path.join(gc_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(gc_dir, "index.md")))
        
        # Vérification d'un fichier metadata.json réel
        with open(os.path.join(gc_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("category"), "sous sous partie 1")
            self.assertEqual(meta.get("title"), "Petit enfant : sous sous partie")
            self.assertEqual(meta.get("order"), 0, "Le petit enfant devrait avoir l'ordre 0 (premier de sa liste)")
            self.assertNotIn("path", meta)
        
        with open(os.path.join(parent_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("title"), "ZenDocs : Parent")
            self.assertEqual(meta.get("order"), 0, "Le parent racine devrait avoir l'ordre 0")
            self.assertNotIn("path", meta)

        # Vérification du second enfant pour l'ordre
        child2_dir = os.path.join(parent_dir, "second-enfant-deuxieme-sous-partie")
        with open(os.path.join(child2_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("order"), 1, "Le second enfant devrait avoir l'ordre 1")
        
        # Vérification de Zensical
        zensical_toml = os.path.join(self.test_dir, "zensical.toml")
        self.assertTrue(os.path.exists(zensical_toml), "zensical.toml devrait être créé")
        
        with open(zensical_toml, "r", encoding="utf-8") as f:
            toml_content = f.read()
            self.assertIn('site_name = "ZenDocs : Parent"', toml_content)
            self.assertIn('docs_dir = "source/zendocs-parent"', toml_content)
            self.assertIn('copyright = """\nCopyright &copy; 2026 Coopérative Code Commun - CC-BY-SA\n"""', toml_content)
            self.assertIn('logo = "9a08b49e-498f-49c9-a3ac-dcf1c9c59292.png"', toml_content)
            self.assertIn('"navigation.tabs"', toml_content)
            self.assertNotIn('#"navigation.tabs"', toml_content)
            self.assertIn('#"navigation.sections"', toml_content)
            # On vérifie que la version non commentée n'est plus là, 
            # MAIS attention il peut y avoir des espaces. 
            # On cherche donc spécifiquement la version active sans le # devant
            self.assertFalse(re.search(r'^\s*"navigation.sections"', toml_content, re.MULTILINE))
        
        logger.info("SUCCÈS: test_full_integration_download")

    def test_zensical_build(self):
        """Vérifie que la construction Zensical fonctionne."""
        logger.info("Test: zensical build (génération du site)")
        
        # On s'assure que les données sont là (dépend de test_full_integration_download)
        if not os.path.exists(os.path.join(self.test_dir, "zensical.toml")):
            self.test_full_integration_download()
            
        import subprocess
        try:
            # On lance le build réel / Run real build
            # stdout/stderr capturés pour ne pas polluer la sortie des tests
            subprocess.run(["uv", "run", "zensical", "build"], cwd=self.test_dir, check=True, capture_output=True)
            
            site_dir = os.path.join(self.test_dir, "site")
            self.assertTrue(os.path.exists(site_dir), "Le dossier 'site' devrait être créé après le build")
            self.assertTrue(os.path.exists(os.path.join(site_dir, "index.html")), "Le fichier index.html devrait exister dans le site généré")
            
            # Vérifie qu'une sous-page est aussi générée
            subpage_dir = os.path.join(site_dir, "premier-enfant-sous-partie")
            self.assertTrue(os.path.exists(subpage_dir), f"Le dossier de sous-page {subpage_dir} devrait exister")
            
        except Exception as e:
            self.fail(f"Le build Zensical a échoué : {e}")
            
        logger.info("SUCCÈS: test_zensical_build")

    def test_ensure_ssh_url(self):
        """Vérifie la conversion des URLs HTTPS en SSH."""
        logger.info("Test: ensure_ssh_url")
        from zensical_backend import ensure_ssh_url
        
        # Cas HTTPS GitHub
        https_url = "https://github.com/User/Repo"
        self.assertEqual(ensure_ssh_url(https_url), "git@github.com:User/Repo.git")
        
        # Cas HTTPS GitHub avec .git
        https_url_git = "https://github.com/User/Repo.git"
        self.assertEqual(ensure_ssh_url(https_url_git), "git@github.com:User/Repo.git")
        
        # Cas déjà SSH
        ssh_url = "git@github.com:User/Repo.git"
        self.assertEqual(ensure_ssh_url(ssh_url), ssh_url)
        
        # Cas autre URL (pas touché)
        other_url = "https://gitlab.com/User/Repo"
        self.assertEqual(ensure_ssh_url(other_url), other_url)
        
        logger.info("SUCCÈS: test_ensure_ssh_url")

    def test_deploy_skips_download(self):
        """Vérifie que l'option --deploy court-circuite le téléchargement dans main.py."""
        logger.info("Test: --deploy skips download in main.py")
        
        # On mocke process_document pour voir s'il est appelé
        import unittest.mock as mock
        with mock.patch('main.process_document') as mock_process:
            # On simule les arguments avec --deploy
            test_args = ['main.py', '--deploy', 'https://notes.liiib.re/docs/id/']
            with mock.patch('sys.argv', test_args):
                # On mocke aussi deploy_zensical pour ne pas faire un vrai build/deploy
                with mock.patch('main.deploy_zensical') as mock_deploy:
                    # On mocke load_dotenv pour éviter les problèmes d'environnement
                    with mock.patch('main.load_dotenv'):
                        main.main()
                        
                        # process_document ne doit PAS avoir été appelé
                        mock_process.assert_not_called()
                        # deploy_zensical DOIT avoir été appelé
                        mock_deploy.assert_called()
        
        logger.info("SUCCÈS: test_deploy_skips_download")

    def test_zensical_deploy(self):
        """Vérifie que le déploiement Zensical fonctionne (si demandé)."""
        if not TestDocs2Static.run_deploy:
            self.skipTest("Le déploiement n'est pas activé. Utilisez --deploy pour le tester.")
            
        logger.info("Test: zensical deploy (déploiement réel)")
        
        # On s'assure que le build est fait / Ensure build is done
        if not os.path.exists(os.path.join(self.test_dir, "site")):
            self.test_zensical_build()
            
        try:
            # On utilise le repo de test du .env / Use test repo from .env
            github_repo = os.getenv("TEST_GITHUB_REPO")
            main.deploy_zensical(self.test_dir, github_repo)
            
            # Vérifie que l'URL GitHub Pages est affichée (via get_github_pages_url)
            from zensical_backend import get_github_pages_url
            pages_url = get_github_pages_url(github_repo)
            logger.info(f"Test de déploiement réussi : {pages_url}")
            
            logger.info("SUCCÈS: test_zensical_deploy")
        except Exception as e:
            self.fail(f"Le déploiement Zensical a échoué : {e}")

if __name__ == "__main__":
    # Vérifie si l'utilisateur veut vider le cache avant les tests
    # Check if the user wants to clear the cache before tests
    if "--no-cache" in sys.argv:
        logger.warning("Option --no-cache détectée : Suppression du cache local...")
        main.session.cache.clear()
        # On retire l'argument pour ne pas perturber unittest
        sys.argv.remove("--no-cache")
    
    # Vérifie si on doit tester le déploiement
    # Check if we should test deployment
    if "--deploy" in sys.argv:
        logger.warning("Option --deploy détectée : Le déploiement réel sera testé.")
        TestDocs2Static.run_deploy = True
        sys.argv.remove("--deploy")
        
    unittest.main()
