# Docs2Static 🚀

[Français](#français) | [English](#english)

---

## Français

Docs2Static est un outil en Python permettant de transformer des documents édités collaborativement sur [Docs](https://docs.suite.anct.gouv.fr/) (basé sur BlockNote) en un site web statique professionnel.

### 🌟 Principes

- **Récupération récursive** : Télécharge automatiquement toute l'arborescence (pages enfants, petits-enfants, etc.).
- **Conversion intelligente** : Transforme le contenu en Markdown propre pour les générateurs de sites statiques.
- **Gestion des médias** : Télécharge les images localement et met à jour les liens automatiquement.
- **Intégration Zensical** : Configure et construit automatiquement votre site avec le moteur [Zensical](https://zensical.org/).
- **Déploiement automatisé** : Publie votre site sur GitHub Pages ou GitLab Pages en une seule commande via SSH.

### 🛠️ Installation

Ce projet utilise [uv](https://github.com/astral-sh/uv) pour la gestion des dépendances.

```bash
# Cloner le dépôt
git clone <votre-depot>
cd Docs2static

# Installer les dépendances
uv sync
```

### ⚙️ Configuration

Copiez le fichier d'exemple et remplissez-le avec vos informations :

```bash
cp env_example .env
```

Variables dans le `.env` :
- `DOCS_URL` : L'URL de votre document Docs racine.
- `GITHUB_REPO` : L'adresse SSH de votre dépôt GitHub (ex: `git@github.com:User/Repo.git`).
- `GITLAB_REPO` : L'adresse SSH de votre dépôt GitLab (alternative).
- `BACKEND` : Le moteur statique utilisé (par défaut : `zensical`).

### 🚀 Utilisation

#### 1. Télécharger les documents
Télécharge le contenu depuis Docs et prépare la structure locale dans `content/source` :
```bash
uv run python3 main.py
```

#### 2. Déployer sur GitHub Pages
Génère le site statique et l'envoie sur la branche `gh-pages` :
```bash
uv run python3 main.py --deploy
```

#### Options disponibles :
- `-f, --format` : Choisir le format (`html`, `markdown` ou `both`).
- `--no-cache` : Forcer le téléchargement sans utiliser le cache local.
- `-b, --backend` : Spécifier le backend (ex: `zensical`).
- `-d, --deploy` : Déployer sans retélécharger les fichiers.

### 🧪 Tests

Pour vérifier que tout fonctionne correctement avec des données réelles :
```bash
uv run python3 test_main.py
```

#### Options de test :
- `--no-cache` : Vider le cache avant de lancer les tests.
- `--deploy` : Tester le déploiement réel vers le dépôt de test.
- `--test-zensical` : Activer un point d'arrêt interactif pour vérifier le rendu local avec `zensical serve`.

---

## English

Docs2Static is a Python tool that transforms collaborative documents from [Docs](https://docs.suite.anct.gouv.fr/) (based on BlockNote) into a professional static website.

### 🌟 Principles

- **Recursive Fetching**: Automatically downloads the entire tree structure (children, grandchildren, etc.).
- **Smart Conversion**: Converts content into clean Markdown for static site generators.
- **Media Management**: Downloads images locally and updates links automatically.
- **Zensical Integration**: Automatically configures and builds your site using the [Zensical](https://zensical.org/) engine.
- **Automated Deployment**: Publishes your site to GitHub Pages or GitLab Pages in a single command via SSH.

### 🛠️ Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone <your-repo>
cd Docs2static

# Install dependencies
uv sync
```

### ⚙️ Configuration

Copy the example file and fill it with your information:

```bash
cp env_example .env
```

Variables in `.env`:
- `DOCS_URL`: The URL of your root Docs document.
- `GITHUB_REPO`: The SSH address of your GitHub repository (e.g., `git@github.com:User/Repo.git`).
- `GITLAB_REPO`: The SSH address of your GitLab repository (alternative).
- `BACKEND`: The static engine used (default: `zensical`).

### 🚀 Usage

#### 1. Download documents
Downloads content from Docs and prepares the local structure in `content/source`:
```bash
uv run python3 main.py
```

#### 2. Deploy to GitHub Pages
Generates the static site and pushes it to the `gh-pages` branch:
```bash
uv run python3 main.py --deploy
```

#### Available options:
- `-f, --format`: Choose the format (`html`, `markdown`, or `both`).
- `--no-cache`: Force download without using local cache.
- `-b, --backend`: Specify the backend (e.g., `zensical`).
- `-d, --deploy`: Deploy without re-downloading files.

### 🧪 Testing

To verify everything works correctly with real data:
```bash
uv run python3 test_main.py
```

#### Testing options:
- `--no-cache`: Clear cache before running tests.
- `--deploy`: Test real deployment to the test repository.
- `--test-zensical`: Enable an interactive breakpoint to check local rendering with `zensical serve`.

---

## 🙌 Credits / Inspiration

- Inspired by the work of [Sylvain Zimmer](https://github.com/suitenumerique/st-home/tree/main/src/lib/docs2dsfr) who uses a Node.js stack for a similar result.
- Developed in Python to offer a simple and accessible alternative (FALC style).