import random

import math

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from myapp import play_helpers
from myapp.forms import (
    GameForm,
    ParticipantForm,
    TeamForm,
    TeamMemberAddForm,
    TeamMemberForm,
)
from myapp.models import (
    AnswerMode,
    Game,
    GameTeamScore,
    GameStatus,
    Participant,
    Team,
    TeamMember,
)

ACTION_ADD_PARTICIPANT = 'add_participant'
ACTION_ADD_TEAM = 'add_team'
ACTION_ADD_TEAM_MEMBER = 'add_team_member'
ACTION_ADD_TEAM_MEMBER_PAGE = 'add_member'
ACTION_REMOVE_TEAM_MEMBER = 'remove_member'
ACTION_MOVE_MEMBER_UP = 'move_up'
ACTION_MOVE_MEMBER_DOWN = 'move_down'
ACTION_ADD_GAME = 'add_game'
ACTION_CREATE_AND_PLAY = 'create_and_play'
ACTION_START_GAME = 'start_game'
ACTION_START_AND_PLAY = 'start_and_play'
ACTION_FINISH_GAME = 'finish_game'
ACTION_COMPOSE_SAVE_START = 'save_and_start'
ERROR_PREFIX = 'Corrigez le formulaire : '


def _format_validation_error(exc: ValidationError) -> str:
    if hasattr(exc, 'message_dict'):
        parts = []
        for field, msgs in exc.message_dict.items():
            parts.append(f'{field}: {"; ".join(str(m) for m in msgs)}')
        return ' | '.join(parts)
    return '; '.join(str(m) for m in exc.messages)


PLAY_PARTIAL_HEADER = 'HTTP_X_PLAY_PARTIAL'


def _play_wants_partial(request) -> bool:
    return request.META.get(PLAY_PARTIAL_HEADER) == '1'


def _play_document_title(ctx: dict) -> str:
    if ctx.get('play_finished'):
        return 'Fin — Quiz'
    if ctx.get('play_no_questions'):
        return 'Quiz'
    qn = ctx.get('question_number')
    qt = ctx.get('question_total')
    if qn is not None and qt is not None:
        return f'Question {qn}/{qt}'
    return 'Quiz'


def _game_for_play(pk: int) -> Game:
    return get_object_or_404(
        Game.objects.select_related('team_a', 'team_b').prefetch_related(
            Prefetch(
                'scores_by_team',
                queryset=GameTeamScore.objects.select_related('team'),
            ),
            Prefetch(
                'team_a__memberships',
                queryset=TeamMember.objects.select_related('participant').order_by(
                    'sort_order',
                    'pk',
                ),
            ),
            Prefetch(
                'team_b__memberships',
                queryset=TeamMember.objects.select_related('participant').order_by(
                    'sort_order',
                    'pk',
                ),
            ),
        ),
        pk=pk,
    )


def _play_scores_context(game: Game) -> dict:
    sm = play_helpers.scores_by_team_id(
        Game.objects.prefetch_related(
            Prefetch(
                'scores_by_team',
                queryset=GameTeamScore.objects.select_related('team'),
            ),
        ).get(pk=game.pk),
    )
    sa = sm.get(game.team_a_id)
    sb = sm.get(game.team_b_id)
    return {
        'score_a_total': sa.score_total if sa else 0,
        'score_b_total': sb.score_total if sb else 0,
        'score_a_bm': (sa.correct_answers_count, sa.wrong_answers_count)
        if sa
        else (0, 0),
        'score_b_bm': (sb.correct_answers_count, sb.wrong_answers_count)
        if sb
        else (0, 0),
    }


def _play_assemble_active_context(
    request,
    game: Game,
    questions: list,
    n_questions: int,
    pk: int,
) -> dict:
    mode_key = play_helpers.play_mode_session_key(pk)
    duo_key = play_helpers.play_duo_order_session_key(pk)
    mode = request.session.get(mode_key)
    question = questions[game.play_question_index]
    duo_order = None
    choice_rows: list[dict] = []
    if mode == AnswerMode.DUO:
        duo_order = request.session.get(duo_key)
        if duo_order:
            choice_rows = play_helpers.build_choice_rows(
                question,
                list(duo_order),
            )
        else:
            mode = None
            request.session.pop(mode_key, None)
    elif mode == AnswerMode.CARRE:
        choice_rows = play_helpers.build_choice_rows(question, [0, 1, 2, 3])
    game.refresh_from_db()
    idx = game.play_question_index
    return {
        'game': game,
        'question': question,
        'question_number': idx + 1,
        'question_total': n_questions,
        **play_helpers.play_team_columns_progress(idx, n_questions),
        'current_team': game.team_for_turn,
        'mode': mode,
        'choice_rows': choice_rows,
        'play_finished': False,
        'play_no_questions': False,
    }


def _play_render(
    request,
    ctx: dict,
    *,
    answer_verdict: str | None = None,
):
    ctx['play_document_title'] = _play_document_title(ctx)
    if _play_wants_partial(request):
        resp = render(request, 'myapp/_play_live.html', ctx)
        resp.headers['X-Play-Title'] = ctx['play_document_title']
        if answer_verdict in ('correct', 'wrong'):
            resp.headers['X-Play-Answer-Verdict'] = answer_verdict
        return resp
    return render(request, 'myapp/play.html', ctx)


def _move_membership(team_id: int, membership_id: int, delta: int) -> bool:
    rows = list(
        TeamMember.objects.filter(team_id=team_id).order_by('sort_order', 'pk'),
    )
    ids = [r.pk for r in rows]
    try:
        idx = ids.index(membership_id)
    except ValueError:
        return False
    j = idx + delta
    if j < 0 or j >= len(rows):
        return False
    a, b = rows[idx], rows[j]
    a.sort_order, b.sort_order = b.sort_order, a.sort_order
    TeamMember.objects.bulk_update([a, b], ['sort_order'])
    return True


def _base_context():
    return {
        'participant_form': ParticipantForm(),
        'team_form': TeamForm(),
        'team_member_form': TeamMemberForm(),
        'game_form': GameForm(),
        'participants': Participant.objects.all(),
        'teams': Team.objects.prefetch_related(
            Prefetch(
                'memberships',
                queryset=TeamMember.objects.select_related('participant').order_by(
                    'sort_order',
                    'pk',
                ),
            ),
        ),
        'games': Game.objects.select_related('team_a', 'team_b')
        .prefetch_related(
            Prefetch(
                'scores_by_team',
                queryset=GameTeamScore.objects.select_related('team'),
            ),
        )
        .order_by('-created_at'),
    }


def home(request):
    rng = random.Random()
    stars = []
    for _ in range(32):
        # Fractions des demi-axes (bx ≈ 47 % largeur, by ≈ 41 % hauteur côté JS).
        rx_pct = round(rng.uniform(0.36, 0.99), 4)
        ry_pct = round(rng.uniform(0.34, 0.97), 4)
        # Vitesses en rad/s (une orbite complète ≈ 18–55 s).
        speed = round(rng.uniform(0.11, 0.35), 4)
        phase = round(rng.uniform(0, 2 * math.pi), 4)
        stars.append(
            {
                'rx_pct': rx_pct,
                'ry_pct': ry_pct,
                'speed': speed,
                'phase': phase,
                'tilt': round(rng.uniform(-48, 48), 2),
                'size': round(rng.uniform(14, 30), 2),
            },
        )
    home_icon_files = (
        'whisky.png',
        'gin-tonic.png',
        'clipart4519843.png',
    )
    home_icons = []
    for fname in home_icon_files:
        for _ in range(7):
            # Orbite un peu plus large que les étoiles (demi-axes relatifs plus grands).
            rx_pct = round(rng.uniform(0.52, 1.08), 4)
            ry_pct = round(rng.uniform(0.50, 1.06), 4)
            speed = round(rng.uniform(0.11, 0.35), 4)
            phase = round(rng.uniform(0, 2 * math.pi), 4)
            home_icons.append(
                {
                    'file': fname,
                    'rx_pct': rx_pct,
                    'ry_pct': ry_pct,
                    # Sens inverse aux étoiles (même formule, vitesse négative).
                    'speed': -speed,
                    'phase': phase,
                    'tilt': round(rng.uniform(-48, 48), 2),
                    'size': round(rng.uniform(20, 44), 2),
                },
            )
    home_photo_tilt = 'left' if rng.random() < 0.5 else 'right'
    return render(
        request,
        'myapp/home.html',
        {
            'stars': stars,
            'home_icons': home_icons,
            'home_photo_tilt': home_photo_tilt,
        },
    )


@staff_member_required(login_url='/admin/login/')
def begin_party(request):
    """Crée une partie en préparation (2 équipes) et ouvre la composition."""
    teams = list(Team.objects.order_by('name')[:2])
    if len(teams) < 2:
        messages.info(
            request,
            'Créez au moins deux équipes depuis la préparation pour lancer une partie.',
        )
        return redirect('setup')
    team_a, team_b = teams[0], teams[1]
    game = Game.objects.create(team_a=team_a, team_b=team_b)
    return redirect('compose_game', pk=game.pk)


@staff_member_required(login_url='/admin/login/')
def setup_dashboard(request):
    context = _base_context()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == ACTION_ADD_PARTICIPANT:
            form = ParticipantForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'Participant enregistré.')
                return redirect('setup')
            context['participant_form'] = form
            messages.error(
                request,
                ERROR_PREFIX + form.errors.as_text(),
            )

        elif action == ACTION_ADD_TEAM:
            form = TeamForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Équipe créée.')
                return redirect('setup')
            context['team_form'] = form
            messages.error(request, ERROR_PREFIX + form.errors.as_text())

        elif action == ACTION_ADD_TEAM_MEMBER:
            form = TeamMemberForm(request.POST)
            if form.is_valid():
                membership = form.save(commit=False)
                max_order = TeamMember.objects.filter(
                    team_id=membership.team_id,
                ).aggregate(m=Max('sort_order'))['m']
                membership.sort_order = 0 if max_order is None else max_order + 1
                membership.save()
                messages.success(request, 'Participant ajouté à l’équipe.')
                return redirect('setup')
            context['team_member_form'] = form
            messages.error(request, ERROR_PREFIX + form.errors.as_text())

        elif action == ACTION_ADD_GAME:
            form = GameForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Partie créée (préparation).')
                return redirect('setup')
            context['game_form'] = form
            messages.error(request, ERROR_PREFIX + form.errors.as_text())

        elif action == ACTION_CREATE_AND_PLAY:
            form = GameForm(request.POST)
            if form.is_valid():
                game = form.save()
                return redirect('compose_game', pk=game.pk)
            context['game_form'] = form
            messages.error(request, ERROR_PREFIX + form.errors.as_text())

        elif action == ACTION_START_GAME:
            try:
                game = Game.objects.get(pk=request.POST.get('game_id'))
            except (Game.DoesNotExist, TypeError, ValueError):
                messages.error(request, 'Partie introuvable.')
                return redirect('setup')
            try:
                game.start()
            except ValidationError as e:
                messages.error(request, _format_validation_error(e))
            else:
                messages.success(request, 'Partie démarrée.')
            return redirect('setup')

        elif action == ACTION_START_AND_PLAY:
            try:
                game = Game.objects.get(pk=request.POST.get('game_id'))
            except (Game.DoesNotExist, TypeError, ValueError):
                messages.error(request, 'Partie introuvable.')
                return redirect('setup')
            if game.status != GameStatus.PREPARATION:
                messages.error(
                    request,
                    'Seule une partie en préparation peut être composée ainsi.',
                )
                return redirect('setup')
            return redirect('compose_game', pk=game.pk)

        elif action == ACTION_FINISH_GAME:
            try:
                game = Game.objects.get(pk=request.POST.get('game_id'))
            except (Game.DoesNotExist, TypeError, ValueError):
                messages.error(request, 'Partie introuvable.')
                return redirect('setup')
            try:
                game.finish()
            except ValidationError as e:
                messages.error(request, _format_validation_error(e))
            else:
                messages.success(request, 'Partie terminée.')
            return redirect('setup')

        else:
            messages.error(request, 'Action non reconnue.')
            return redirect('setup')

    return render(request, 'myapp/setup.html', context)


@staff_member_required(login_url='/admin/login/')
def edit_participant(request, pk: int):
    participant = get_object_or_404(Participant, pk=pk)
    if request.method == 'POST':
        form = ParticipantForm(request.POST, request.FILES, instance=participant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Participant mis à jour.')
            return redirect('setup')
        messages.error(request, ERROR_PREFIX + form.errors.as_text())
    else:
        form = ParticipantForm(instance=participant)
    return render(
        request,
        'myapp/setup_participant_edit.html',
        {'form': form, 'participant': participant},
    )


@staff_member_required(login_url='/admin/login/')
def edit_team(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, 'Équipe mise à jour.')
            return redirect('setup')
        messages.error(request, ERROR_PREFIX + form.errors.as_text())
    else:
        form = TeamForm(instance=team)
    return render(
        request,
        'myapp/setup_team_edit.html',
        {'form': form, 'team': team},
    )


@staff_member_required(login_url='/admin/login/')
def manage_team_members(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    redirect_target = redirect('manage_team_members', pk=team.pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == ACTION_ADD_TEAM_MEMBER_PAGE:
            form = TeamMemberAddForm(
                request.POST,
                team=team,
            )
            if form.is_valid():
                membership = form.save(commit=False)
                membership.team = team
                max_order = TeamMember.objects.filter(team_id=team.pk).aggregate(
                    m=Max('sort_order'),
                )['m']
                membership.sort_order = 0 if max_order is None else max_order + 1
                membership.save()
                messages.success(request, 'Participant ajouté à l’équipe.')
                return redirect_target
            messages.error(request, ERROR_PREFIX + form.errors.as_text())
            memberships = list(
                team.memberships.select_related('participant').order_by(
                    'sort_order',
                    'pk',
                ),
            )
            return render(
                request,
                'myapp/setup_team_members.html',
                {
                    'team': team,
                    'memberships': memberships,
                    'add_form': form,
                    'can_add_member': form.fields['participant'].queryset.exists(),
                },
            )

        elif action == ACTION_REMOVE_TEAM_MEMBER:
            try:
                mid = int(request.POST.get('membership_id', ''))
            except (TypeError, ValueError):
                messages.error(request, 'Membre invalide.')
                return redirect_target
            deleted, _ = TeamMember.objects.filter(
                pk=mid,
                team_id=team.pk,
            ).delete()
            if deleted:
                messages.success(request, 'Participant retiré de l’équipe.')
            else:
                messages.error(request, 'Impossible de retirer ce membre.')

        elif action == ACTION_MOVE_MEMBER_UP:
            try:
                mid = int(request.POST.get('membership_id', ''))
            except (TypeError, ValueError):
                messages.error(request, 'Membre invalide.')
                return redirect_target
            if _move_membership(team.pk, mid, -1):
                messages.success(request, 'Ordre mis à jour.')
            else:
                messages.error(request, 'Déplacement impossible.')

        elif action == ACTION_MOVE_MEMBER_DOWN:
            try:
                mid = int(request.POST.get('membership_id', ''))
            except (TypeError, ValueError):
                messages.error(request, 'Membre invalide.')
                return redirect_target
            if _move_membership(team.pk, mid, +1):
                messages.success(request, 'Ordre mis à jour.')
            else:
                messages.error(request, 'Déplacement impossible.')

        else:
            messages.error(request, 'Action non reconnue.')

        return redirect_target

    memberships = list(
        team.memberships.select_related('participant').order_by('sort_order', 'pk'),
    )
    add_form = TeamMemberAddForm(team=team)
    can_add_member = add_form.fields['participant'].queryset.exists()
    return render(
        request,
        'myapp/setup_team_members.html',
        {
            'team': team,
            'memberships': memberships,
            'add_form': add_form,
            'can_add_member': can_add_member,
        },
    )


def _parse_participant_id_list(raw: str) -> list[int]:
    out: list[int] = []
    for part in (raw or '').split(','):
        s = part.strip()
        if not s:
            continue
        try:
            out.append(int(s))
        except ValueError as e:
            raise ValueError('id invalide') from e
    return out


@staff_member_required(login_url='/admin/login/')
def compose_game(request, pk: int):
    game = get_object_or_404(
        Game.objects.select_related('team_a', 'team_b'),
        pk=pk,
    )
    if game.status != GameStatus.PREPARATION:
        messages.error(
            request,
            'Cette partie n’est plus en préparation : composition impossible.',
        )
        return redirect('setup')

    if request.method == 'POST':
        if request.POST.get('action') != ACTION_COMPOSE_SAVE_START:
            messages.error(request, 'Action non reconnue.')
            return redirect('compose_game', pk=game.pk)

        ta_name = (request.POST.get('team_a_name') or '').strip()
        tb_name = (request.POST.get('team_b_name') or '').strip()
        if not ta_name or not tb_name:
            messages.error(request, 'Indiquez un nom pour chaque équipe.')
            return redirect('compose_game', pk=game.pk)

        try:
            a_ids = _parse_participant_id_list(request.POST.get('team_a_order', ''))
            b_ids = _parse_participant_id_list(request.POST.get('team_b_order', ''))
        except ValueError:
            messages.error(request, 'Liste de participants invalide.')
            return redirect('compose_game', pk=game.pk)

        if set(a_ids) & set(b_ids):
            messages.error(
                request,
                'Un participant ne peut pas être dans les deux équipes.',
            )
            return redirect('compose_game', pk=game.pk)

        if not a_ids or not b_ids:
            messages.error(
                request,
                'Glissez au moins un joueur dans chaque équipe.',
            )
            return redirect('compose_game', pk=game.pk)

        all_assigned = set(a_ids) | set(b_ids)
        existing = set(
            Participant.objects.filter(pk__in=all_assigned).values_list(
                'pk',
                flat=True,
            ),
        )
        if existing != all_assigned:
            messages.error(request, 'Participant inconnu.')
            return redirect('compose_game', pk=game.pk)

        all_participant_pks = set(
            Participant.objects.values_list('pk', flat=True),
        )
        if all_assigned != all_participant_pks:
            messages.error(
                request,
                'Répartissez tous les participants dans les équipes avant de commencer.',
            )
            return redirect('compose_game', pk=game.pk)

        for pid in all_assigned:
            raw_name = (request.POST.get(f'participant_name_{pid}') or '').strip()
            if not raw_name:
                messages.error(
                    request,
                    'Chaque participant doit avoir un nom (vérifiez les champs).',
                )
                return redirect('compose_game', pk=game.pk)

        try:
            with transaction.atomic():
                team_a = Team.objects.select_for_update().get(pk=game.team_a_id)
                team_b = Team.objects.select_for_update().get(pk=game.team_b_id)
                team_a.name = ta_name
                team_a.save()
                team_b.name = tb_name
                team_b.save()

                for pid in all_assigned:
                    name = (request.POST.get(f'participant_name_{pid}') or '').strip()
                    participant = Participant.objects.select_for_update().get(pk=pid)
                    if participant.name != name:
                        participant.name = name
                        participant.save()

                TeamMember.objects.filter(
                    team_id__in=[game.team_a_id, game.team_b_id],
                ).delete()

                TeamMember.objects.bulk_create(
                    [
                        TeamMember(
                            team_id=game.team_a_id,
                            participant_id=pid,
                            sort_order=i,
                        )
                        for i, pid in enumerate(a_ids)
                    ]
                    + [
                        TeamMember(
                            team_id=game.team_b_id,
                            participant_id=pid,
                            sort_order=i,
                        )
                        for i, pid in enumerate(b_ids)
                    ],
                )

                game.refresh_from_db()
                game = Game.objects.select_related('team_a', 'team_b').get(pk=game.pk)
                game.start()
        except ValidationError as e:
            messages.error(request, _format_validation_error(e))
            return redirect('compose_game', pk=game.pk)

        return redirect('play_game', pk=game.pk)

    participants = list(Participant.objects.all().order_by('name'))

    return render(
        request,
        'myapp/game_compose.html',
        {
            'game': game,
            'pool': participants,
            'team_a_members': [],
            'team_b_members': [],
            'has_participants': bool(participants),
        },
    )


@staff_member_required(login_url='/admin/login/')
def play_game(request, pk: int):
    game = _game_for_play(pk)
    questions = play_helpers.load_play_questions()
    n_questions = len(questions)

    def _finished_payload(msg=None):
        game.refresh_from_db()
        ctx = {
            'game': game,
            'play_finished': True,
            'play_no_questions': False,
            'question_total': n_questions,
            **play_helpers.play_team_columns_progress(
                n_questions,
                n_questions,
                finished=True,
            ),
            **_play_scores_context(game),
            **play_helpers.play_drink_template_context(game),
        }
        if msg:
            ctx['play_message'] = msg
        return ctx

    def _active_page():
        loaded = _game_for_play(pk)
        return {
            **_play_assemble_active_context(
                request,
                loaded,
                questions,
                n_questions,
                pk,
            ),
            **_play_scores_context(loaded),
            **play_helpers.play_drink_template_context(loaded),
        }

    if n_questions == 0:
        game.refresh_from_db()
        ctx = {
            'game': game,
            'play_no_questions': True,
            'play_finished': False,
            'question_total': 0,
            **play_helpers.play_team_columns_progress(0, 0),
            **_play_scores_context(game),
            **play_helpers.play_drink_template_context(game),
        }
        return _play_render(request, ctx)

    if game.status == GameStatus.FINISHED or game.play_question_index >= n_questions:
        return _play_render(request, _finished_payload())

    if game.status != GameStatus.IN_PROGRESS:
        messages.error(
            request,
            'Cette partie n’est pas en cours. Démarrez-la depuis la préparation.',
        )
        if _play_wants_partial(request):
            return JsonResponse({'redirect': reverse('setup')})
        return redirect('setup')

    mode_key = play_helpers.play_mode_session_key(pk)
    duo_key = play_helpers.play_duo_order_session_key(pk)

    if request.method == 'POST':
        post_action = request.POST.get('action')
        if post_action == 'choose_mode':
            mode = request.POST.get('mode')
            if mode not in AnswerMode.values:
                messages.error(request, 'Mode de jeu invalide.')
                return _play_render(request, _active_page())
            request.session[mode_key] = mode
            question = questions[game.play_question_index]
            if mode == AnswerMode.DUO:
                request.session[duo_key] = play_helpers.duo_display_order(
                    game,
                    question,
                    game.play_question_index,
                )
            else:
                request.session.pop(duo_key, None)
            return _play_render(request, _active_page())

        if post_action == 'answer':
            mode = request.session.get(mode_key)
            if not mode:
                messages.error(
                    request,
                    'Choisissez d’abord duo / carré / cash.',
                )
                return _play_render(request, _active_page())

            question = questions[game.play_question_index]
            team = game.team_for_turn

            if mode == AnswerMode.CASH:
                verdict_raw = (request.POST.get('cash_verdict') or '').strip().lower()
                if verdict_raw == 'correct':
                    is_correct = True
                elif verdict_raw == 'wrong':
                    is_correct = False
                else:
                    messages.error(
                        request,
                        'Indiquez si la réponse est correcte (Vrai ou Faux).',
                    )
                    return _play_render(request, _active_page())
                answer_was_correct = is_correct
                try:
                    if is_correct:
                        game.register_correct_answer(team, mode)
                    else:
                        game.register_wrong_answer(team, mode)
                except ValidationError as e:
                    messages.error(request, _format_validation_error(e))
                    return _play_render(request, _active_page())
            else:
                try:
                    choice = int(request.POST.get('choice_index', ''))
                except (TypeError, ValueError):
                    messages.error(request, 'Réponse invalide.')
                    return _play_render(request, _active_page())

                if mode == AnswerMode.DUO:
                    allowed = request.session.get(duo_key)
                    if not allowed or choice not in allowed:
                        messages.error(
                            request,
                            'Cette option n’était pas proposée.',
                        )
                        return _play_render(request, _active_page())
                elif choice not in (0, 1, 2, 3):
                    messages.error(request, 'Réponse invalide.')
                    return _play_render(request, _active_page())

                answer_was_correct = choice == question.correct_index
                try:
                    if answer_was_correct:
                        game.register_correct_answer(team, mode)
                    else:
                        game.register_wrong_answer(team, mode)
                except ValidationError as e:
                    messages.error(request, _format_validation_error(e))
                    return _play_render(request, _active_page())

            request.session.pop(mode_key, None)
            request.session.pop(duo_key, None)

            Game.objects.filter(pk=game.pk).update(
                play_question_index=F('play_question_index') + 1,
            )
            game.refresh_from_db(
                fields=(
                    'play_question_index',
                    'next_turn_side',
                ),
            )

            if game.play_question_index >= n_questions:
                try:
                    game.refresh_from_db()
                    game.finish()
                except ValidationError:
                    pass
                finished_game = _game_for_play(pk)
                ctx = {
                    'game': finished_game,
                    'play_finished': True,
                    'play_no_questions': False,
                    'question_total': n_questions,
                    **play_helpers.play_team_columns_progress(
                        n_questions,
                        n_questions,
                        finished=True,
                    ),
                    **_play_scores_context(finished_game),
                    **play_helpers.play_drink_template_context(finished_game),
                    'play_message': 'Manche terminée.',
                }
                v = 'correct' if answer_was_correct else 'wrong'
                return _play_render(request, ctx, answer_verdict=v)

            v = 'correct' if answer_was_correct else 'wrong'
            return _play_render(request, _active_page(), answer_verdict=v)

        return _play_render(request, _active_page())

    return _play_render(request, _active_page())
