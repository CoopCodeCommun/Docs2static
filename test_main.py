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
    
    # Variable pour activer les tests interactifs Zensical
    # Variable to enable interactive Zensical tests
    test_zensical = False
    
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
        self.assertEqual(fm.get("brouillon"), "non")
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
        
        # Vérification des liens et du titre dans le markdown
        with open(os.path.join(parent_dir, "index.md"), "r", encoding="utf-8") as f:
            md_content = f.read()
            # Vérifie que le titre est présent en H1 au début (après le frontmatter)
            self.assertIn("# ZenDocs : Parent", md_content)
            self.assertIn(f"![badge\\_grenoble.png]({img1})", md_content)
            self.assertIn(f"![help-freestockpro-3036405.fhd.jpg]({img2})", md_content)
            self.assertNotIn("https://notes.liiib.re/media/", md_content)
        
        # 2. Enfants
        child1_dir = os.path.join(parent_dir, "premier-enfant-sous-partie")
        child2_dir = os.path.join(parent_dir, "second-enfant-deuxieme-sous-partie")
        child3_dir = os.path.join(parent_dir, "voici-un-brouillon")
        self.assertTrue(os.path.exists(child1_dir))
        self.assertTrue(os.path.exists(child2_dir))
        self.assertFalse(os.path.exists(child3_dir), "Le document brouillon ne devrait pas être créé")
        self.assertFalse(os.path.exists(os.path.join(child1_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(child1_dir, "index.md")))
        
        # 3. Petit-enfant
        gc1_dir = os.path.join(child1_dir, "premier-petit-enfant")
        gc2_dir = os.path.join(child1_dir, "petit-enfant-sous-sous-partie")
        gc3_dir = os.path.join(child1_dir, "dernier-petit-enfant")
        
        self.assertTrue(os.path.exists(gc1_dir))
        self.assertTrue(os.path.exists(gc2_dir))
        self.assertTrue(os.path.exists(gc3_dir))
        
        # 4. Arrière-petit-enfant
        ggc_dir = os.path.join(gc2_dir, "et-voici-un-n-4")
        self.assertTrue(os.path.exists(ggc_dir))
        
        # Vérification du frontmatter dans le markdown du petit-enfant
        with open(os.path.join(gc2_dir, "index.md"), "r", encoding="utf-8") as f:
            md_content = f.read()
            self.assertTrue(md_content.startswith("---"))
            self.assertIn("edit_url: https://notes.liiib.re/docs/0b4c67c5-f62f-45cc-80fd-a290cb04b384/", md_content)
            self.assertIn("category: sous sous partie 1", md_content)
        
        # Vérification d'un fichier metadata.json réel
        with open(os.path.join(gc2_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("category"), "sous sous partie 1")
            self.assertEqual(meta.get("title"), "Petit enfant : sous sous partie")
            self.assertEqual(meta.get("order"), 1, "Le petit enfant devrait avoir l'ordre 1 (il est deuxième)")
            self.assertNotIn("path", meta)
        
        # Vérification du premier petit enfant
        with open(os.path.join(gc1_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("order"), 0, "Le premier petit enfant devrait avoir l'ordre 0")
        
        # Vérification du dernier petit enfant
        with open(os.path.join(gc3_dir, "metadata.json"), "r") as f:
            meta = json.load(f)
            self.assertEqual(meta.get("order"), 2, "Le dernier petit enfant devrait avoir l'ordre 2")
        
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
            self.assertIn(f'repo_url = "{self.base_url}/docs/{self.doc_id}/"', toml_content)
            self.assertIn('copyright = """\nCopyright &copy; 2026 Coopérative Code Commun - CC-BY-SA\n"""', toml_content)
            self.assertIn('logo = "9a08b49e-498f-49c9-a3ac-dcf1c9c59292.png"', toml_content)
            self.assertIn('"navigation.tabs"', toml_content)
            self.assertIn('"content.action.edit"', toml_content)
            self.assertIn('"content.action.view"', toml_content)
            self.assertNotIn('#"content.action.edit"', toml_content)
            self.assertNotIn('#"content.action.view"', toml_content)
            self.assertIn('edit = "material/pencil"', toml_content)
            self.assertIn('view = "material/eye"', toml_content)
            self.assertIn('repo = "fontawesome/solid/file-pen"', toml_content)
            self.assertNotIn('#"navigation.tabs"', toml_content)
            self.assertIn('#"navigation.sections"', toml_content)
            
            # Vérification de la navigation explicite
            # Verification of explicit navigation
            self.assertIn('nav = [', toml_content)
            self.assertIn('"index.md"', toml_content)
            self.assertIn('Premier enfant : sous partie', toml_content)
            self.assertIn('premier-enfant-sous-partie/index.md', toml_content)
            self.assertIn('Petit enfant : sous sous partie', toml_content)
            self.assertIn('premier-enfant-sous-partie/petit-enfant-sous-sous-partie/index.md', toml_content)

            # On vérifie que la version non commentée n'est plus là, 
            # MAIS attention il peut y avoir des espaces. 
            # On cherche donc spécifiquement la version active sans le # devant
            self.assertFalse(re.search(r'^\s*"navigation.sections"', toml_content, re.MULTILINE))
        
        # --- TEST DE NON-REMPLACEMENT DU TOML ---
        # On modifie manuellement le TOML
        with open(zensical_toml, "a", encoding="utf-8") as f:
            f.write("\n# TEST_MODIFICATION\n")
        
        # On relance le traitement
        main.process_document(self.base_url, self.doc_id, parent_output_dir=self.source_dir, selected_format="both", backend=backend)
        
        # On vérifie que notre modification est toujours là
        with open(zensical_toml, "r", encoding="utf-8") as f:
            new_toml_content = f.read()
            self.assertIn("# TEST_MODIFICATION", new_toml_content, "Le fichier TOML ne doit pas être écrasé s'il existe déjà.")
            
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
        self.assertEqual(ensure_ssh_url("https://github.com/User/Repo"), "git@github.com:User/Repo.git")
        
        # Cas HTTPS GitLab
        self.assertEqual(ensure_ssh_url("https://gitlab.com/User/Repo"), "git@gitlab.com:User/Repo.git")
        
        # Cas déjà SSH
        self.assertEqual(ensure_ssh_url("git@gitlab.com:User/Repo.git"), "git@gitlab.com:User/Repo.git")
        
        logger.info("SUCCÈS: test_ensure_ssh_url")

    def test_is_draft(self):
        """Vérifie la fonction is_draft avec différents alias et valeurs."""
        logger.info("Test: is_draft")
        from main import is_draft
        
        # Anglais
        self.assertTrue(is_draft({"draft": "true"}))
        self.assertTrue(is_draft({"draft": "yes"}))
        self.assertFalse(is_draft({"draft": "false"}))
        
        # Français
        self.assertTrue(is_draft({"brouillon": "true"}))
        self.assertTrue(is_draft({"brouillon": "oui"}))
        self.assertTrue(is_draft({"brouillon": "OUI "}))
        self.assertFalse(is_draft({"brouillon": "non"}))
        self.assertFalse(is_draft({"brouillon": "false"}))
        
        # Vide / Absent
        self.assertFalse(is_draft({}))
        self.assertFalse(is_draft({"title": "Test"}))
        
        logger.info("SUCCÈS: test_is_draft")

    def test_french_metadata_aliases(self):
        """Vérifie que les alias français sont bien utilisés par le backend."""
        logger.info("Test: french metadata aliases")
        from zensical_backend import setup_zensical_backend
        import unittest.mock as mock
        
        metadata = {
            "auteur·ice": "Jean Dupont",
            "résumé": "Ceci est une description en français",
            "licence": "GPLv3"
        }
        
        # On mocke les appels système pour ne pas créer de vrais fichiers
        with mock.patch('os.path.exists', return_value=False):
            with mock.patch('os.makedirs'):
                with mock.patch('subprocess.run'):
                    with mock.patch('builtins.open', mock.mock_open(read_data='[project]\nsite_name = "test"\nsite_description = "desc"\nsite_author = "author"\ncopyright = """\ncopy\n"""\ndocs_dir = "docs"')):
                        with mock.patch('zensical_backend.build_nav_structure', return_value=[]):
                            with mock.patch('zensical_backend.format_nav_to_toml', return_value="nav = []"):
                                # On récupère le contenu écrit dans le fichier
                                with mock.patch('builtins.open', mock.mock_open(read_data='[project]\nsite_name = "test"\nsite_description = "desc"\nsite_author = "author"\ncopyright = """\ncopy\n"""\ndocs_dir = "docs"')) as m:
                                    setup_zensical_backend("temp", metadata, "Le Titre")
                                    
                                    # On vérifie ce qui a été écrit
                                    # m() est le mock_open, m().write est l'appel à write
                                    written_content = ""
                                    for call in m().write.call_args_list:
                                        written_content += call[0][0]
                                    
                                    self.assertIn('site_author = "Jean Dupont"', written_content)
                                    self.assertIn('site_description = "Ceci est une description en français"', written_content)
                                    self.assertIn('Copyright &copy; 2026 Jean Dupont - GPLv3', written_content)

        logger.info("SUCCÈS: test_french_metadata_aliases")

    def test_draft_skip(self):
        """Vérifie que les documents marqués comme draft ne sont pas enregistrés."""
        logger.info("Test: draft skip")
        import unittest.mock as mock
        
        # On mocke fetch_document_content pour retourner un contenu avec draft: true
        mock_data = {
            "title": "Draft Doc",
            "content": "---\ndraft: true\n---\nContenu brouillon"
        }
        
        with mock.patch('main.fetch_document_content', return_value=mock_data):
            with mock.patch('main.fetch_document_tree', return_value=[]):
                # On utilise un dossier de test dédié
                draft_dir = os.path.join(self.test_dir, "draft_test")
                if os.path.exists(draft_dir):
                    shutil.rmtree(draft_dir)
                
                # On traite le document
                main.process_document(self.base_url, "draft-id", draft_dir, selected_format="markdown")
                
                # Le dossier ne devrait pas contenir index.md
                # En fait, si c'est un draft, on ne devrait même pas créer le dossier doc_dir
                # ou alors on le supprime.
                doc_path = os.path.join(draft_dir, "draft-doc")
                file_path = os.path.join(doc_path, "index.md")
                
                self.assertFalse(os.path.exists(file_path), "Le fichier index.md ne devrait pas exister pour un draft")
        
        logger.info("SUCCÈS: test_draft_skip")

    def test_draft_skip_child(self):
        """Vérifie qu'un enfant marqué comme draft n'est pas enregistré mais que son parent l'est."""
        logger.info("Test: draft skip child")
        import unittest.mock as mock
        
        # Racine (publiée)
        root_data = {
            "title": "Root Doc",
            "content": "---\ndraft: false\n---\nContenu racine"
        }
        # Enfant (brouillon)
        child_data = {
            "title": "Child Draft",
            "content": "---\ndraft: true\n---\nContenu enfant brouillon"
        }
        
        # Liste des enfants
        children_list = [{"id": "child-id", "title": "Child Draft", "numchild": 0}]
        
        def side_effect(bu, doc_id, fmt="html"):
            if doc_id == "root-id":
                return root_data
            if doc_id == "child-id":
                return child_data
            return {}

        with mock.patch('main.fetch_document_content', side_effect=side_effect):
            with mock.patch('main.fetch_document_tree', return_value=children_list):
                # On utilise un dossier de test dédié
                draft_dir = os.path.join(self.test_dir, "draft_child_test")
                if os.path.exists(draft_dir):
                    shutil.rmtree(draft_dir)
                
                # On traite la racine
                main.process_document(self.base_url, "root-id", draft_dir, selected_format="markdown")
                
                # Racine doit exister
                self.assertTrue(os.path.exists(os.path.join(draft_dir, "root-doc", "index.md")))
                
                # Enfant ne doit pas exister
                self.assertFalse(os.path.exists(os.path.join(draft_dir, "root-doc", "child-draft", "index.md")))
                self.assertFalse(os.path.exists(os.path.join(draft_dir, "root-doc", "child-draft")))
        
        logger.info("SUCCÈS: test_draft_skip_child")

    def test_get_pages_url(self):
        """Vérifie le calcul des URLs de pages (GitHub/GitLab)."""
        logger.info("Test: get_pages_url")
        from zensical_backend import get_pages_url
        
        # GitHub SSH
        self.assertEqual(get_pages_url("git@github.com:User/Repo.git"), "https://User.github.io/Repo/")
        # GitHub HTTPS
        self.assertEqual(get_pages_url("https://github.com/User/Repo"), "https://User.github.io/Repo/")
        
        # GitLab SSH
        self.assertEqual(get_pages_url("git@gitlab.com:User/Repo.git"), "https://User.gitlab.io/Repo/")
        # GitLab HTTPS
        self.assertEqual(get_pages_url("https://gitlab.com/User/Repo"), "https://User.gitlab.io/Repo/")
        
        logger.info("SUCCÈS: test_get_pages_url")

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

    def test_cleanup_before_download(self):
        """Vérifie que le dossier source est bien effacé avant le téléchargement."""
        logger.info("Test: cleanup source directory before download")
        
        import unittest.mock as mock
        # On utilise des patchs pour simuler l'existence du dossier et sa suppression
        # We use patches to simulate directory existence and its deletion
        with mock.patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with mock.patch('shutil.rmtree') as mock_rmtree:
                with mock.patch('main.process_document'):
                    # On simule l'appel standard (sans --deploy)
                    test_args = ['main.py', 'https://notes.liiib.re/docs/id/']
                    with mock.patch('sys.argv', test_args):
                        with mock.patch('main.load_dotenv'):
                            main.main()
                            
                            # Vérifie que rmtree a été appelé sur le bon dossier
                            # Verify that rmtree was called on the correct directory
                            mock_rmtree.assert_called_with("content/source")
        
        logger.info("SUCCÈS: test_cleanup_before_download")

    def test_zensical_deploy(self):
        """Vérifie que le déploiement Zensical fonctionne (si demandé)."""
        if not TestDocs2Static.run_deploy:
            self.skipTest("Le déploiement n'est pas activé. Utilisez --deploy pour le tester.")
            
        logger.info("Test: zensical deploy (déploiement réel)")
        
        # On s'assure que le build est fait / Ensure build is done
        if not os.path.exists(os.path.join(self.test_dir, "site")):
            self.test_zensical_build()
            
        try:
            # On utilise le repo de test du .env / Use test repo from .env (GitHub ou GitLab)
            repo_url = os.getenv("TEST_GITHUB_REPO") or os.getenv("TEST_GITLAB_REPO")
            main.deploy_zensical(self.test_dir, repo_url)
            
            # Vérifie que l'URL Pages est affichée (via get_pages_url)
            from zensical_backend import get_pages_url
            pages_url = get_pages_url(repo_url)
            logger.info(f"Test de déploiement réussi : {pages_url}")
            
            logger.info("SUCCÈS: test_zensical_deploy")
        except Exception as e:
            self.fail(f"Le déploiement Zensical a échoué : {e}")

    def test_zensical_serve_interactive(self):
        """Test interactif pour vérifier le rendu Zensical."""
        if not TestDocs2Static.test_zensical:
            self.skipTest("Le test interactif Zensical n'est pas activé. Utilisez --test-zensical pour le tester.")
            
        logger.info("=== POINT D'ARRÊT TEST ZENSICAL ===")
        logger.info(f"Veuillez ouvrir un NOUVEAU terminal et lancer :")
        logger.info(f"cd {self.test_dir}")
        logger.info(f"uv run zensical serve --port 8000")
        input("Appuyez sur Entrée une fois que le serveur est lancé (Press Enter once the server is running)...")
        
        import requests
        try:
            response = requests.get("http://localhost:8000")
            self.assertEqual(response.status_code, 200)
            logger.info("Serveur Zensical accessible et répond correctement !")
        except Exception as e:
            self.fail(f"Impossible d'accéder au serveur Zensical : {e}")

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

    # Vérifie si on doit tester Zensical de façon interactive
    # Check if we should test Zensical interactively
    if "--test-zensical" in sys.argv:
        logger.warning("Option --test-zensical détectée : Le test interactif Zensical sera activé.")
        TestDocs2Static.test_zensical = True
        sys.argv.remove("--test-zensical")
        
    unittest.main()
