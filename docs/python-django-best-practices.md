# Bonnes pratiques Python et Django (référence projet)

Document de référence pour ce dépôt. Il **synthétise** des guides reconnus ; en cas de doute, se reporter aux sources listées en fin de section. Les conventions du **projet** priment sur tout guide générique.

## Sources officielles et guides (à consulter régulièrement)

| Ressource | Rôle |
|-----------|------|
| [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/) | Style et lisibilité du code Python. |
| [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/) | Conventions des docstrings (complément de PEP 8). |
| [Django – Site officiel](https://www.djangoproject.com/) | Vision du framework, sécurité, doc, communauté. |
| [Documentation Django](https://docs.djangoproject.com/) | Référence technique (modèles, vues, déploiement, etc.). |
| [Django Best Practices (Lincoln Loop)](https://django-best-practices.readthedocs.io/en/latest/) | Pratiques projet : settings, URLs, apps, templates, static, structure. |
| [HackSoftware Django Styleguide](https://github.com/HackSoftware/Django-Styleguide) | Architecture applicative (services, sélecteurs, DRF) — **opinionated**, à adapter. |
| [Django Styleguide Example](https://github.com/HackSoftware/Django-Styleguide-Example) | Exemple concret du styleguide HackSoft. |

---

## 1. PEP 8 : principes retenus pour le code Python

- **Cohérence** : la cohérence dans le projet et le module passe avant une adhésion aveugle au PEP. Ne pas casser la rétrocompatibilité uniquement pour le style.
- **Indentation** : 4 espaces par niveau. Ne pas mélanger tabulations et espaces.
- **Longueur de ligne** : 79 caractères cible ; **jusqu’à 99** accepté pour du code d’équipe si explicitement convenu ; commentaires et docstrings idéalement limités à **72** caractères par ligne.
- **Imports** : en tête du fichier, groupés (stdlib → tiers → local), une ligne vide entre groupes ; **`import *` à éviter** ; préférer les imports **absolus**.
- **Nommage** (indications PEP 8) :
  - modules : `lowercase_with_underscores` ;
  - classes : `CapWords` ;
  - fonctions / méthodes / variables : `lowercase_with_underscores` ;
  - constantes : `UPPER_SNAKE_CASE` ;
  - exceptions : suffixe `Error` si erreur.
- **Opérateurs** : pour les coupures de ligne longues, le style « avant l’opérateur » (style Knuth) est recommandé pour la lisibilité.
- **Espaces** : pas d’espace superflu dans `()`, `[]`, `{}` ; une seule affectation par logique ; espacer les opérateurs binaires de façon cohérente.
- **Comparaisons** : pour les singletons, utiliser `is` / `is not` (ex. `is None`), pas `== None`.
- **Annotations** : suivre les règles d’espacement du PEP pour `:` et `->` sur les fonctions.

À compléter par les **recommandations de programmation** du PEP (f-strings là où c’est pertinent, compréhensions raisonnables, etc.).

---

## 2. Django (site officiel) : principes utiles au quotidien

Tirés de la présentation publique de Django sur [djangoproject.com](https://www.djangoproject.com/) et de la documentation :

- **Productivité** : privilégier les fonctionnalités du framework (ORM, auth, formulaires) plutôt que de réinventer des briques.
- **Sécurité** : utiliser les protections intégrées (CSRF, XSS, injections SQL via l’ORM, etc.), tenir Django et les dépendances à jour.
- **Montée en charge** : architecture prévue pour évoluer (cache, base de données, tâches asynchrones ou Celery selon le besoin).
- **ORM** : modéliser explicitement ; migrations versionnées ; éviter le SQL brut sauf nécessité mesurée.
- **Internationalisation** : préparer les chaînes (`gettext` / `ugettext_lazy`) dès que le produit peut être multilingue.
- Toujours **`DEBUG = False` en production**, **`ALLOWED_HOSTS`** correctement renseigné, secrets hors dépôt (variables d’environnement, coffre-fort).

---

## 3. Django Best Practices (Lincoln Loop) : projet et structure

Synthèse de [django-best-practices.readthedocs.io](https://django-best-practices.readthedocs.io/en/latest/) :

### 3.1 Settings

- Séparer la configuration **par environnement** (ex. base / local / production / tests) tout en **évitant la duplication** dangereuse.
- Secrets et valeurs sensibles : **variables d’environnement**, pas de clés dans le dépôt.

### 3.2 URLconf

- URLs **claires et hiérarchisées** ; noms d’URL (`name=`) pour les redirections et les tests.
- Éviter la logique métier complexe dans `urls.py` — déléguer aux vues / services.

### 3.3 Applications locales

- Une app = un domaine fonctionnel cohérent ; **éviter les « fourre-tout »** monolithiques.

### 3.4 Templates

- Logique **minimale** dans les templates ; calculs et règles métier côté vues / context processors / services.

### 3.5 Fichiers statiques et médias

- Distinction nette **static** (CSS/JS) vs **media** (uploads) ; configuration adaptée en production (collectstatic, stockage objet si besoin).

### 3.6 WSGI / ASGI

- Fichier d’entrée déploiement **simple** ; pas de configuration secrète dedans — tout via settings.

*(Le guide Lincoln Loop couvre aussi le style de code, le déploiement et les serveurs — voir la doc complète.)*

---

## 4. HackSoftware Django Styleguide : architecture du code

Résumé de [HackSoftware/Django-Styleguide](https://github.com/HackSoftware/Django-Styleguide) — **à valider avec l’équipe** et à ajuster au contexte du projet.

### 4.1 Où placer la logique métier

**Plutôt dans :**

- **Services** : opérations qui **écrivent** (création, mises à jour, effets de bord, appels externes orchestrés).
- **Selectors** : opérations qui **lisent** / filtrent / agrègent des données depuis la base (ou équivalent).
- **Propriétés de modèle** : valeurs dérivées **simples**, basées sur des champs du même modèle **sans** requêtes coûteuses ni jointures profondes.
- **`clean()`** sur le modèle : validations **multi-champs simples** sur une même instance ; déclencher **`full_clean()`** avant `save()` depuis les services lorsque pertinent.
- **Contraintes DB** (`CheckConstraint`, etc.) lorsque la règle peut être **déclarative** et garantie par la base (voir doc Django sur les contraintes ; depuis Django 4.1, `full_clean()` peut aussi refléter certaines contraintes).

**Éviter pour la logique métier « principale » :**

- Enfouir la règle dans **vues/APIs, serializers, forms** au-delà du mapping entrant/sortant.
- Surcharger massivement **`save()`** pour toute la règle métier.
- **`signals`** pour chaîner le cœur métier (les signaux restent utiles pour du **découplage léger**, invalidation de cache, etc., pas comme architecture principale du domaine).

**Managers / querysets personnalisés** : utiles pour **affiner l’API de requêtage**, pas pour y concentrer tout le domaine multi-modèles.

### 4.2 Modèles

- **`BaseModel` abstrait** souvent utile (`created_at`, `updated_at`, etc.).
- **`full_clean()`** dans les services avant persistance lorsque la validation modèle est requise.
- **Tests de modèle** ciblés : validations, propriétés/méthodes non triviales ; privilégier `full_clean()` sans toucher au DB quand c’est possible pour accélérer.

### 4.3 Services et sélecteurs

- Services souvent en **`services.py`** (ou package `services/`), fonctions **`snake_case`** avec préfixe domaine (`user_create`, `order_cancel`), arguments **keyword-only** quand il y a plusieurs paramètres, **annotations de type**.
- **`@transaction.atomic`** autour des opérations qui doivent être atomiques ; **`transaction.on_commit`** pour déclencher tâches async après commit.
- Sélecteurs : même discipline de nommage ; peuvent retourner des querysets ou des structures déjà filtrées ; **filtrage** souvent dans le sélecteur, pas épars dans les vues.

### 4.4 API (ex. Django REST framework)

- **Une vue/API par cas d’usage** plutôt qu’un CRUD générique qui cache la logique.
- Hériter de **`APIView` / `GenericAPIView`** plutôt que de piles abstraites lourdes si cela noie la logique dans les serializers.
- **Pas de logique métier dans la vue** : appeler services / sélecteurs ; la vue orchestre HTTP + statuts.
- **Serializer d’entrée** et **serializer de sortie** distincts (`InputSerializer` / `OutputSerializer` en classes internes à la vue si l’équipe le souhaite).
- **Listes** : filtres validés (ex. query params via un serializer de filtre) → **sélecteur** ; pagination réutilisable (helpers type `get_paginated_response`).
- **Objets complexes en sortie** : possibilité de fonction du type `something_serialize()` pour optimiser requêtes + assemblage réponse.

### 4.5 URLs

- **Une route par action** alignée sur les APIs ; regrouper par domaine (`course_patterns`, etc.) et `include()` pour limiter les conflits de fusion sur un immense `urls.py`.

### 4.6 Settings (style HackSoft / cookiecutter-django)

- Arborescence du type `config/django/base.py` + `local.py` / `production.py` / `test.py` ; modules `config/settings/*.py` pour Celery, CORS, Sentry, etc.
- **`base.py`** inclut tout ce qui est commun ; pas de réglage « production seulement » oublié hors base si cela doit exister partout avec un simple booléen.
- **`django-environ`** (ou équivalent) : fichier **`.env`** lu par un petit chargeur maison dans `settings` (stdlib) ou variables exportées dans le shell ; **`.env` hors Git** ; **`.env.example`** versionné.
- Préfixe **`DJANGO_`** pour les variables *spécifiques Django* si plusieurs services partagent la même machine ; sinon **cohérence** avant tout.
- Intégrations optionnelles : drapeau `USE_*` + chargement conditionnel pour ne pas imposer des secrets en dev.

### 4.7 Erreurs (DRF)

- S’accorder tôt sur le **format JSON des erreurs** (éventuellement proche de [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807)).
- Savoir que **`rest_framework.exceptions.ValidationError`** et **`django.core.exceptions.ValidationError`** ne se comportent pas pareil par défaut : prévoir un **exception handler** personnalisé qui convertit `django.core.exceptions.ValidationError` via `as_serializer_error` si vous exposez l’API en DRF.
- Ne pas masquer les **500** : un handler qui retourne `None` laisse remonter l’erreur — utile pour ne pas avaler les bugs (monitoring type Sentry).

### 4.8 Tests

- Couvrir **surtout la couche service** (logique métier, DB réelle pour ces tests, **mock** des appels externes et tâches async).
- **Nommage explicite** des tests ; **factory_boy** / **faker** si le projet les adopte.

### 4.9 Celery (si utilisé)

- Configuration isolée ; **retry** et **idempotence** pour les tâches ; erreurs remontées proprement ; structure de modules claire ; tâches périodiques documentées.

### 4.10 Qualité / DX

- **Annotations de type** même sans mypy obligatoire ; introduction progressive de **mypy** si l’équipe le souhaite.

---

## 5. Règles transverses pour ce dépôt

1. **Python** : respecter PEP 8 + conventions d’équipe (longueur de ligne, outils de formatage éventuels : *black*, *ruff*, etc., s’ils sont ajoutés au projet).
2. **Django** : sécurité et settings par environnement ; migrations propres ; pas de secrets dans Git.
3. **Architecture** : logique métier testable (services / sélecteurs) ; vues et serializers **minces**.
4. **Documentation** : docstrings utiles pour modules et API publiques (PEP 257 en complément).
5. **Sources externes** : lorsque ce document et une source divergent sur un détail, **la décision d’équipe sur ce repo** et la **documentation Django officielle** priment pour l’implémentation.

---

## 6. Liens rapides

- PEP 8 : https://peps.python.org/pep-0008/
- PEP 257 : https://peps.python.org/pep-0257/
- Django : https://www.djangoproject.com/
- Doc Django : https://docs.djangoproject.com/
- Django Best Practices (Lincoln Loop) : https://django-best-practices.readthedocs.io/en/latest/
- HackSoftware Django Styleguide : https://github.com/HackSoftware/Django-Styleguide
