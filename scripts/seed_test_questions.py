#!/usr/bin/env python3
"""Crée des questions de test (style « question numero N ») pour le jeu.

Utilisation (depuis la racine du dépôt, venv activé, `.env` / DB configurée)::

    python scripts/seed_test_questions.py

Options::

    python scripts/seed_test_questions.py --count 20
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, repo_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    import django

    django.setup()

    from myapp.models import Question

    parser = argparse.ArgumentParser(description='Insère des questions de test en base.')
    parser.add_argument(
        '--count',
        type=int,
        default=20,
        help='Nombre de questions à créer (défaut: 20).',
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error('--count doit être >= 1')

    # Même schéma que les tests manuels : 2× faux, bonne (index 2), « duo » (index 3).
    # En mode duo : la bonne réponse + la proposition d’index duo_distractor_index (ici 3).
    created = 0
    for n in range(1, args.count + 1):
        Question(
            text=f'question numero {n}',
            choice_0='faux',
            choice_1='faux',
            choice_2='bonne',
            choice_3='duo',
            correct_index=2,
            duo_distractor_index=3,
        ).save()
        created += 1

    print(f'OK — {created} question(s) créée(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
