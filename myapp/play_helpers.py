"""Logique d’affichage pour l’écran de jeu (questions, modes, scores)."""

from __future__ import annotations

import random
import re
import unicodedata

from myapp.models import Game, GameTeamScore, Question


def play_mode_session_key(game_id: int) -> str:
    return f'play_mode_{game_id}'


def play_duo_order_session_key(game_id: int) -> str:
    return f'play_duo_order_{game_id}'


def load_play_questions() -> list[Question]:
    """Toutes les questions en base, ordre stable (pk croissant), pour une manche."""
    return list(Question.objects.order_by('pk'))


def team_question_slots_total(n_questions: int, *, for_team_a: bool) -> int:
    """Nombre de tours de réponse pour cette équipe sur la manche (A commence, indices 0,2,4…)."""
    if n_questions <= 0:
        return 0
    if for_team_a:
        return (n_questions + 1) // 2
    return n_questions // 2


def team_turn_progress(
    play_question_index: int,
    n_questions: int,
    *,
    for_team_a: bool,
) -> tuple[int, int]:
    """
    (tours déjà joués par l'équipe, tours restants y compris celui en cours si c'est leur tour).
    ``play_question_index`` : indice 0-based de la question en cours.
    """
    if n_questions <= 0:
        return (0, 0)

    def is_team_slot(idx: int) -> bool:
        return (idx % 2 == 0) if for_team_a else (idx % 2 == 1)

    answered = sum(1 for idx in range(play_question_index) if is_team_slot(idx))
    remaining = sum(
        1 for idx in range(play_question_index, n_questions) if is_team_slot(idx)
    )
    return (answered, remaining)


def play_team_columns_progress(
    play_question_index: int,
    n_questions: int,
    *,
    finished: bool = False,
) -> dict[str, int]:
    """Compteurs au-dessus de chaque colonne équipe (tours pour cette équipe, pas le total manche seul)."""
    a_total = team_question_slots_total(n_questions, for_team_a=True)
    b_total = team_question_slots_total(n_questions, for_team_a=False)
    if finished or n_questions <= 0 or play_question_index >= n_questions:
        return {
            'play_team_a_turns_answered': a_total if n_questions > 0 else 0,
            'play_team_a_turns_left': 0,
            'play_team_a_turns_total': a_total,
            'play_team_b_turns_answered': b_total if n_questions > 0 else 0,
            'play_team_b_turns_left': 0,
            'play_team_b_turns_total': b_total,
        }
    a_ans, a_left = team_turn_progress(
        play_question_index,
        n_questions,
        for_team_a=True,
    )
    b_ans, b_left = team_turn_progress(
        play_question_index,
        n_questions,
        for_team_a=False,
    )
    return {
        'play_team_a_turns_answered': a_ans,
        'play_team_a_turns_left': a_left,
        'play_team_a_turns_total': a_total,
        'play_team_b_turns_answered': b_ans,
        'play_team_b_turns_left': b_left,
        'play_team_b_turns_total': b_total,
    }


def scores_by_team_id(game: Game) -> dict[int, GameTeamScore]:
    return {s.team_id: s for s in game.scores_by_team.all()}


def duo_display_order(game: Game, question: Question, q_index: int) -> list[int]:
    pair = [question.correct_index, question.duo_distractor_index]
    rng = random.Random(game.pk * 31 + question.pk * 7 + q_index)
    rng.shuffle(pair)
    return pair


def choice_label(question: Question, index: int) -> str:
    return getattr(question, f'choice_{index}')


def build_choice_rows(question: Question, indices: list[int]) -> list[dict[str, int | str]]:
    return [
        {'index': i, 'text': choice_label(question, int(i))}
        for i in indices
    ]


def normalize_answer_for_match(text: str) -> str:
    """Normalise une saisie pour la comparaison mode cash (FR)."""
    s = (text or '').strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.casefold()
    s = s.replace('-', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def cash_answer_matches(question: Question, answer_text: str) -> bool:
    correct = choice_label(question, question.correct_index)
    return normalize_answer_for_match(answer_text) == normalize_answer_for_match(
        correct,
    )


def play_drink_template_context(game: Game) -> dict[str, int]:
    """Compteurs gorgées / shots pour l’écran play."""
    return {
        'drink_team_a_gorgees': game.drink_gorgees_team_a,
        'drink_team_a_shots': game.drink_shots_team_a,
        'drink_team_b_gorgees': game.drink_gorgees_team_b,
        'drink_team_b_shots': game.drink_shots_team_b,
        'drink_thomas_gorgees': game.drink_gorgees_thomas,
        'drink_thomas_shots': game.drink_shots_thomas,
    }
