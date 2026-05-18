# site-evg-thomas

Projet [**Django**](https://www.djangoproject.com/) 6 avec **PostgreSQL** (pas de SQLite). Les paramètres viennent des **variables d’environnement** (`os.environ`) ; un fichier **`.env`** à la racine peut être lu au démarrage (parsing minimal dans `config/settings.py`, sans paquet supplémentaire). Voir [`docs/python-django-best-practices.md`](docs/python-django-best-practices.md).

**Package Django :** le package de configuration est **`config/`** (équivalent logique de `django-admin startproject config` avec une app séparée). **`DJANGO_SETTINGS_MODULE=config.settings`**. (Le nom de package Python **`site`** est à éviter : conflit avec le module standard [`site`](https://docs.python.org/3/library/site.html).)

## Prérequis

- **Python** 3.x installé (voir [étape 1 du tutoriel](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384))
- **PostgreSQL** installé et démarré

## Installation

### 1. Environnement virtuel et dépendances

Comme [l’étape 1 du tutoriel](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384), avec le nom de venv **`venv`** :

```bash
cd /chemin/vers/evg-thomas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Sous Windows : `venv\Scripts\activate`.

Le tutoriel installe `django` et `psycopg2-binary` ; ici **`requirements.txt`** installe déjà **Django** et **`psycopg`** (pilote PostgreSQL moderne, compatible avec le même moteur Django).

### 2. Créer la base et l’utilisateur PostgreSQL

Suivre [les étapes 5.1 et 5.2 du tutoriel](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384) : ouvrir le client `psql` en superutilisateur, puis créer la base et l’utilisateur.

**Option A — script SQL** (`scripts/postgres_init.sql`) : adaptez base / utilisateur / mot de passe dans ce fichier si besoin, puis exécutez en superutilisateur :

```bash
psql -U postgres -f scripts/postgres_init.sql
```

Sur certaines installations Linux (*peer authentication*) :

```bash
sudo -u postgres psql -f scripts/postgres_init.sql
```

Équivalent pratique (depuis la racine du dépôt) : `./scripts/init_postgres.sh` — si besoin : `chmod +x scripts/init_postgres.sh` (le script appelle `psql -U postgres -f scripts/postgres_init.sql`).

**Option B — tout à la main** : connexion à `psql` :

```bash
psql -U postgres
```

Puis les mêmes commandes SQL (vous pouvez garder les noms `mydatabase` / `myuser` ou les remplacer, mais utilisez **les mêmes** dans votre `.env`) :

```sql
CREATE DATABASE mydatabase;
CREATE USER myuser WITH PASSWORD 'mypassword';
ALTER ROLE myuser SET client_encoding TO 'utf8';
ALTER ROLE myuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mydatabase TO myuser;
\c mydatabase
GRANT ALL ON SCHEMA public TO myuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO myuser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO myuser;
```

Quitter `psql` avec `\q`.

Si la base existe déjà (script ancien sans ces lignes) et que `migrate` affiche **`permission denied for schema public`**, exécutez en superutilisateur :

```bash
sudo -u postgres psql -d mydatabase -f scripts/grant_public_schema.sql
```

(adaptez `mydatabase` et éditez `myuser` dans ce fichier si besoin). Le fichier `scripts/postgres_init.sql` inclut désormais ces droits pour les nouvelles installations.

### 3. Variables d’environnement

Django lit **`POSTGRES_*`** dans `config/settings.py`. **Reproduisez** ici le nom de la base, l’utilisateur et le mot de passe définis à l’étape précédente.

**Option A — fichier `.env` (recommandé en local)**

```bash
cp .env.example .env
```

Éditez `.env` pour qu’il corresponde à votre base (exemple aligné sur le tutoriel) :

```env
POSTGRES_DB=mydatabase
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Le tutoriel utilise `HOST: localhost` dans Django ; `localhost` et `127.0.0.1` conviennent en pratique.

**Option B — shell uniquement**

```bash
export POSTGRES_DB=mydatabase
export POSTGRES_USER=myuser
export POSTGRES_PASSWORD=mypassword
export POSTGRES_HOST=localhost
```

Les autres variables utiles :

| Variable | Rôle |
|----------|------|
| `POSTGRES_DB` | **Obligatoire** — nom de la base |
| `POSTGRES_USER` | Utilisateur (sinon défaut `postgres` dans les settings si laissé vide) |
| `POSTGRES_PASSWORD` | Mot de passe |
| `POSTGRES_HOST` | Hôte (défaut `127.0.0.1` dans le code si absent) |
| `POSTGRES_PORT` | Port (défaut `5432`) |
| `DJANGO_SECRET_KEY` | Clé secrète. Génération : `./venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_DEBUG` | `True` / `False` (défaut `True` si absent) |
| `DJANGO_ALLOWED_HOSTS` | Liste séparée par des virgules (défaut `127.0.0.1,localhost`) |

Ne commitez pas **`.env`** (il est dans **`.gitignore`**).

### 4. Migrations, superutilisateur, serveur (comme les étapes 6 à 9 du tutoriel)

```bash
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- **`makemigrations`** : comme [l’étape 6](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384) ; utile dès que vous avez des modèles dans des apps.
- **`createsuperuser`** : [étape 7](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384) — accès à l’admin Django.
- **`runserver`** : [étape 8](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384).

Vérification ([étape 9 du tutoriel](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384)) : ouvrir **http://127.0.0.1:8000/admin/** et se connecter avec le superutilisateur. La page d’accueil du projet reste **http://127.0.0.1:8000/**.

Si `POSTGRES_DB` est absent, Django affiche une erreur du type *Définissez la variable d'environnement POSTGRES_DB*.

## Arborescence utile

| Élément | Description |
|---------|-------------|
| `venv/` | Environnement virtuel (**non versionné**) |
| `manage.py` | Commandes Django (racine du dépôt) |
| `AGENTS.md` | Point d’entrée pour agents Cursor / conventions du dépôt |
| `config/` | Package projet Django (`settings`, `urls`, WSGI/ASGI) |
| `config/settings.py` | Settings + chargement optionnel de `.env` |
| `myapp/` | Première application Django |
| `requirements.txt` | Django, psycopg, etc. |
| `.env.example` | Modèle pour `.env` |
| `scripts/postgres_init.sql` | Création base + rôle + droits schéma `public` (PostgreSQL 15+) |
| `scripts/grant_public_schema.sql` | Réparation droits `public` si `migrate` échoue (bases déjà créées) |
| `scripts/init_postgres.sh` | Lance `psql` sur ce fichier |
| `docs/python-django-best-practices.md` | Conventions du dépôt |

## Ressources

- [Tutoriel Medium — PostgreSQL + Django](https://medium.com/django-unleashed/complete-tutorial-set-up-postgresql-database-with-django-application-d9e789ffa384) (Mehedi Khan, *Django Unleashed*)
- [Documentation Django](https://docs.djangoproject.com/)
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)
