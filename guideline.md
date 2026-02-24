# Guide d'Architecture Docs2Static 🏗️

Ce document explique comment est conçu le projet Docs2Static pour aider les futurs développeurs à comprendre, maintenir et améliorer l'outil.

## 🌟 Philosophie du projet

Docs2Static transforme une instance **Docs** (ANCT) en un **Système de Gestion de Contenu (CMS)** pour sites statiques.
- **Source** : Les documents sont édités de manière collaborative sur Docs.
- **Moteur** : Un script Python récupère, nettoie et organise les données.
- **Rendu** : Un générateur de site statique (comme Zensical) transforme les fichiers en site web.

Le code est écrit en style **FALC** (Facile À Lire et à Comprendre) : noms explicites, fonctions simples, commentaires bilingues et pas de complexité inutile.

---

## 📂 Organisation des fichiers

- `main.py` : Le cœur du programme. Il gère la logique de téléchargement, le parcours de l'arborescence et le traitement des contenus.
- `zensical_backend.py` : Module dédié au moteur de site [Zensical](https://zensical.org/). Il s'occupe de la configuration (`zensical.toml`) et du déploiement Git.
- `test_main.py` : Suite de tests automatisés utilisant des données réelles pour garantir que rien ne casse.
- `.env` : Configuration locale (URLs, dépôts Git, backend par défaut).
- `content/source/` : Dossier où sont stockés les fichiers téléchargés (Markdown, images, JSON).

---

## ⚙️ Fonctionnement interne (Le Flux)

Le programme suit un ordre logique précis pour transformer le web en fichiers locaux :

### 1. Découverte de l'arborescence (Tree Discovery)
Plutôt que de demander les enfants page par page (ce qui est lent), le script utilise l'endpoint API `/descendants/`. Cela permet de récupérer toute la généalogie d'un document en un minimum d'appels. L'arbre est ensuite reconstruit localement grâce au champ `path` de Docs.

### 2. Traitement du contenu (Processing)
Pour chaque document trouvé, la fonction `process_document` réalise les étapes suivantes :
- **Formats** : Télécharge le Markdown (obligatoire pour Zensical) et/ou l'HTML.
- **Frontmatter** : Extrait les métadonnées cachées entre les lignes `---` (auteur, date, brouillon, etc.).
- **Nettoyage** : Ajoute le titre Docs en titre principal (`# Titre`) et nettoie les paragraphes vides.
- **Images** : Télécharge chaque image localement dans le dossier du document et remplace l'URL distante par le nom du fichier local.
- **Brouillons** : Si `brouillon: oui` est détecté, le document et ses enfants sont ignorés.

### 3. Organisation des fichiers
Les dossiers sont nommés selon le **titre du document** (transformé en "slug"). Chaque dossier contient :
- `index.md` : Le contenu principal.
- `metadata.json` : Les métadonnées propres pour une utilisation future.
- Les images locales liées à la page.

### 4. Configuration du Backend
Une fois les fichiers prêts, le module `zensical_backend.py` :
- Crée un projet Zensical propre (`zensical new`).
- Configure la navigation (`nav`) dans `zensical.toml` pour respecter l'ordre exact de Docs.
- Injecte le logo, l'auteur, la description et les boutons d'édition.

---

## 🚀 Mécanismes techniques clés

- **Système de Cache** : Utilise `requests_cache` avec SQLite. Les requêtes sont mémorisées pendant 24h pour ne pas surcharger le serveur Docs et accélérer les tests.
- **Déploiement SSH** : Le script convertit automatiquement les URLs HTTPS en SSH pour permettre un déploiement automatique sur GitHub/GitLab sans demander de mot de passe.
- **Séparation des tâches** : Le téléchargement (`main.py`) et le déploiement (`--deploy`) sont séparés. On peut déployer des fichiers locaux sans avoir besoin d'internet ou de l'API Docs.

---

## 🛠️ Comment contribuer ?

### Ajouter un nouveau moteur de rendu (Backend)
1. Créez un nouveau fichier `monmoteur_backend.py`.
2. Créez une fonction `setup_monmoteur_backend`.
3. Appelez cette fonction à la fin de `process_document` dans `main.py` quand le backend correspond.

### Améliorer l'extraction des données
Toute la logique de nettoyage se trouve dans `extract_frontmatter` (pour l'HTML) et `extract_frontmatter_markdown` dans `main.py`.

### Faire évoluer les tests
Ajoutez vos tests dans `test_main.py`. Utilisez les variables `TEST_` dans le `.env` pour tester sur vos propres documents sans polluer la production.

---
*Ce projet est un commun numérique. Gardez le code simple, lisible et accessible à tous.*
