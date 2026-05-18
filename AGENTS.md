# Instructions agents et contributeurs

## Règles Cursor (`.cursor/rules/`)

| Fichier | Portée |
|---------|--------|
| `project-core.mdc` | **Toujours actif** — rappels dépôt, quand ouvrir la doc détaillée. |
| `python-django.mdc` | Fichiers **`**/*.py`** — style et pratiques Django/Python. |

Les règles sont volontairement **courtes** ; le détail vit dans `docs/`.

## Documentation à consulter

| Document | Contenu |
|----------|---------|
| `docs/python-django-best-practices.md` | Référence longue : PEP 8, Django, structure, liens vers guides externes. |
| `README.md` | Installation, PostgreSQL 15+ (schéma `public`), `.env`, commandes courantes. |

## Arborescence utile

- Racine : `manage.py`, `config/` (settings, URLs, WSGI/ASGI), `myapp/`, `scripts/`, `docs/`.
