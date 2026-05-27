#!/usr/bin/env python3
"""Importe les questions EVG Thomas en base (Google Sheet ou jeu intégré).

Source officielle (sheet partagé)::
    https://docs.google.com/spreadsheets/d/1SoUjVK2-4milwYbdWgWFoZeFfUNA1sJkMRazMRx-7gE/

Utilisation (racine du dépôt, venv activé, `.env` / DB configurée)::

    python scripts/import_evg_questions.py

Depuis un export CSV du tableur (Fichier → Télécharger → CSV)::

    python scripts/import_evg_questions.py --csv /chemin/questions.csv

Options utiles::

    python scripts/import_evg_questions.py --replace   # vide la table avant import
    python scripts/import_evg_questions.py --dry-run   # affiche sans écrire

Les colonnes attendues (ligne d'en-tête) : Question, R1–R4, Bonne réponse,
réponse format duo. Les index de réponse dans le sheet sont **1-based** (1 = R1).
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable

SHEET_ID = '1SoUjVK2-4milwYbdWgWFoZeFfUNA1sJkMRazMRx-7gE'
SHEET_CSV_URL = (
    f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'
)

# Jeu intégré : textes relus (orthographe / grammaire légère), index 0-based.
# Ordre volontaire : Q11–14 = projet bac, lieu de naissance, 1er rdv Chloé, 1er sport.
BUILTIN_QUESTIONS: list[dict[str, object]] = [
    {
        'text': (
            'Qui, parmi les personnes présentes ici, Thomas a-t-il rencontré en premier ?'
        ),
        'choices': ['Jimmy', 'Julien', 'Chloé', 'Florian'],
        'correct': 1,
        'duo': 0,
    },
    {
        'text': 'Quel est son alcool préféré ?',
        'choices': ['Gin', 'Whisky', 'Rhum', 'Vodka'],
        'correct': 0,
        'duo': 2,
    },
    {
        'text': "Quelle est la première formation qu'a suivie Thomas après le bac ?",
        'choices': [
            'BTS fluides, énergie et environnement',
            'DUT génie thermique et énergie',
            'BTS assistant technique d’ingénieur',
            "DUT de Ville-d'Avray",
        ],
        'correct': 0,
        'duo': 1,
    },
    {
        'text': 'Quel était le nom du premier chien de Thomas ?',
        'choices': ['Tsuki', 'Prisca', 'Cannelle', 'Cassis'],
        'correct': 2,
        'duo': 3,
    },
    {
        'text': "En quelle année a-t-il déménagé à Puteaux ?",
        'choices': ['2014', '2015', '2016', '2027'],
        'correct': 1,
        'duo': 0,
    },
    {
        'text': "Quel écart d'âge Thomas a-t-il avec son frère ?",
        'choices': ['5 ans', '6 ans', '7 ans', '8 ans'],
        'correct': 2,
        'duo': 1,
    },
    {
        'text': 'Quel est le plat signature de Thomas ?',
        'choices': [
            'Le X Burger',
            'Poulet curry coco',
            'Côte de bœuf',
            'Pâtes carbonara',
        ],
        'correct': 1,
        'duo': 2,
    },
    {
        'text': 'Quelle était la première voiture de Thomas ?',
        'choices': ['Punto', 'Polo', 'C3', 'Twingo'],
        'correct': 3,
        'duo': 1,
    },
    {
        'text': 'Quel est le pseudo de Thomas sur les jeux vidéo ?',
        'choices': ['Khain', 'Tomate mozza', 'Toto', 'SuperChibre77'],
        'correct': 0,
        'duo': 1,
    },
    {
        'text': 'À quel jeu Thomas a-t-il le plus joué ?',
        'choices': ['Warzone', 'LoL', 'Lineage', 'Dofus'],
        'correct': 1,
        'duo': 2,
    },
    {
        'text': 'Quel projet a-t-il réalisé au bac ?',
        'choices': [
            'Thermomètre Bluetooth',
            'Éclairage intelligent',
            'Ascenseur miniature',
            'Mini-robot mobile',
        ],
        'correct': 3,
        'duo': 1,
    },
    {
        'text': 'Où est né Thomas ?',
        'choices': [
            'Bussy',
            'Thorigny-sur-Marne',
            'Brou-sur-Chantereine',
            'Vaires-sur-Marne',
        ],
        'correct': 2,
        'duo': 1,
    },
    {
        'text': 'Quel a été le premier date avec Chloé ?',
        'choices': [
            'Dîner péniche sur la Seine',
            'Kebab',
            'Gaufre maison pour la Saint-Valentin',
            'Avengers en 4D après une soirée',
        ],
        'correct': 2,
        'duo': 3,
    },
    {
        'text': 'Quel est le premier sport que Thomas a pratiqué ?',
        'choices': ['Judo', "Tire à l'arc", 'Foot', 'Badminton'],
        'correct': 0,
        'duo': 2,
    },
    {
        'text': 'Le dimanche, c’est…',
        'choices': [
            'Gaming et tacos',
            'Lecture et pizza',
            'Netflix et sushi',
            'Puzzle et McDo',
        ],
        'correct': 2,
        'duo': 0,
    },
    {
        'text': 'À quel âge Thomas a-t-il eu sa première fois ?',
        'choices': ['18', '17', '29 (pour faire Sasha)', '11'],
        'correct': 1,
        'duo': 0,
    },
    {
        'text': 'Combien de réveils Thomas met-il avant de se lever ?',
        'choices': [
            '1',
            '2',
            'Maintenant, le réveil, c’est le bébé',
            '5',
        ],
        'correct': 2,
        'duo': 1,
    },
    {
        'text': "Quelle est la chose qu'il oublie systématiquement ?",
        'choices': [
            'Les AirPods',
            'La montre connectée toute neuve à la salle de sport',
            'Ses papiers de voiture',
            'Ses lunettes de soleil',
        ],
        'correct': 1,
        'duo': 0,
    },
    {
        'text': 'Son moment le plus gênant devant ses beaux-parents ?',
        'choices': [
            'Les embrouilles de la famille Herbaut',
            'Le comptable en chemisette',
            'Les interventions impromptues 🔞',
            'Les blagues racistes du beau-père',
        ],
        'correct': 0,
        'duo': 3,
    },
    {
        'text': 'Comment s’appelle le frère de Thomas ?',
        'choices': ['Bruno', 'Rémi', 'Benjamin', 'Benoît'],
        'correct': 3,
        'duo': 1,
    },
]


@dataclass(frozen=True)
class QuestionRow:
    text: str
    choices: tuple[str, str, str, str]
    correct_index: int
    duo_distractor_index: int


def _norm_header(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def _sheet_index(raw: str, *, field: str) -> int:
    s = (raw or '').strip()
    if not s:
        raise ValueError(f'{field} manquant')
    try:
        n = int(s)
    except ValueError as e:
        raise ValueError(f'{field} invalide : {raw!r}') from e
    if n not in (1, 2, 3, 4):
        raise ValueError(f'{field} hors plage 1–4 : {n}')
    return n - 1


def _parse_csv_text(csv_text: str) -> list[QuestionRow]:
    reader = csv.reader(csv_text.splitlines())
    rows = list(reader)
    if not rows:
        raise ValueError('CSV vide')

    header_idx = None
    col_map: dict[str, int] = {}
    for i, row in enumerate(rows):
        normalized = [_norm_header(c) for c in row]
        if 'question' in normalized:
            header_idx = i
            col_map = {name: idx for idx, name in enumerate(normalized) if name}
            break
    if header_idx is None:
        raise ValueError('Ligne d’en-tête « Question » introuvable dans le CSV')

    def col(*names: str) -> int:
        for name in names:
            key = _norm_header(name)
            if key in col_map:
                return col_map[key]
        raise ValueError(f'Colonne introuvable : {names[0]}')

    i_question = col('question')
    i_r = [col(f'r{n}') for n in range(1, 5)]
    i_correct = col('bonne réponse', 'bonne reponse')
    i_duo = col('réponse format duo', 'reponse format duo')

    out: list[QuestionRow] = []
    for row in rows[header_idx + 1 :]:
        if i_question >= len(row):
            continue
        text = (row[i_question] or '').strip()
        if not text:
            continue
        choices = tuple(
            (row[i] if i < len(row) else '').strip() for i in i_r
        )
        if not all(choices):
            raise ValueError(f'Propositions incomplètes pour : {text!r}')
        correct = _sheet_index(
            row[i_correct] if i_correct < len(row) else '',
            field='Bonne réponse',
        )
        duo = _sheet_index(
            row[i_duo] if i_duo < len(row) else '',
            field='réponse format duo',
        )
        out.append(
            QuestionRow(
                text=text,
                choices=choices,  # type: ignore[arg-type]
                correct_index=correct,
                duo_distractor_index=duo,
            ),
        )
    if not out:
        raise ValueError('Aucune question trouvée dans le CSV')
    return out


def _dict_to_row(item: dict[str, object]) -> QuestionRow:
    choices = item['choices']
    if not isinstance(choices, list) or len(choices) != 4:
        raise ValueError('choices doit être une liste de 4 éléments')
    return QuestionRow(
        text=str(item['text']).strip(),
        choices=tuple(str(c).strip() for c in choices),  # type: ignore[arg-type]
        correct_index=int(item['correct']),
        duo_distractor_index=int(item['duo']),
    )


def load_rows(*, csv_path: str | None, from_url: bool) -> list[QuestionRow]:
    if csv_path:
        with open(csv_path, encoding='utf-8-sig', newline='') as fh:
            return _parse_csv_text(fh.read())
    if from_url:
        try:
            with urllib.request.urlopen(SHEET_CSV_URL, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.URLError as e:
            raise SystemExit(
                'Impossible de télécharger le Google Sheet '
                f'({SHEET_CSV_URL}). Exportez le CSV à la main et '
                f'utilisez --csv. Détail : {e}',
            ) from e
        return _parse_csv_text(raw.decode('utf-8-sig'))
    return [_dict_to_row(q) for q in BUILTIN_QUESTIONS]


def rows_to_models(rows: Iterable[QuestionRow], Question):
    models = []
    for row in rows:
        q = Question(
            text=row.text,
            choice_0=row.choices[0],
            choice_1=row.choices[1],
            choice_2=row.choices[2],
            choice_3=row.choices[3],
            correct_index=row.correct_index,
            duo_distractor_index=row.duo_distractor_index,
        )
        q.clean()
        models.append(q)
    return models


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Importe les questions EVG Thomas en base PostgreSQL.',
    )
    parser.add_argument(
        '--csv',
        metavar='FICHIER',
        help='Export CSV du Google Sheet (sinon jeu intégré relu).',
    )
    parser.add_argument(
        '--from-url',
        action='store_true',
        help='Télécharge le CSV public du Google Sheet (peut échouer si non public).',
    )
    parser.add_argument(
        '--replace',
        action='store_true',
        help='Supprime toutes les questions existantes avant import.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Valide et affiche sans écrire en base.',
    )
    args = parser.parse_args()

    if args.csv and args.from_url:
        parser.error('Utilisez --csv ou --from-url, pas les deux.')

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, repo_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    import django

    django.setup()

    from django.db import transaction

    from myapp.models import Question

    rows = load_rows(csv_path=args.csv, from_url=args.from_url)
    questions = rows_to_models(rows, Question)

    if args.dry_run:
        print(f'Dry-run — {len(questions)} question(s) valide(s) :')
        for i, q in enumerate(questions, start=1):
            print(f'  {i:2}. {q.text}')
            for j in range(4):
                mark = []
                if j == q.correct_index:
                    mark.append('✓')
                if j == q.duo_distractor_index:
                    mark.append('duo')
                suffix = f" [{' '.join(mark)}]" if mark else ''
                print(f'      {j + 1}. {getattr(q, f"choice_{j}")}{suffix}')
        return 0

    with transaction.atomic():
        deleted = 0
        if args.replace:
            deleted, _ = Question.objects.all().delete()
        Question.objects.bulk_create(questions)

    print(
        f'OK — {len(questions)} question(s) importée(s)'
        + (f' ({deleted} supprimée(s) avant import).' if args.replace else '.'),
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
