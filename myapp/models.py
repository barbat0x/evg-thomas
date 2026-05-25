from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Question(models.Model):
    """Question à choix multiples : 4 propositions, une seule correcte."""

    text = models.TextField(verbose_name='intitulé')
    choice_0 = models.CharField(max_length=500)
    choice_1 = models.CharField(max_length=500)
    choice_2 = models.CharField(max_length=500)
    choice_3 = models.CharField(max_length=500)
    correct_index = models.PositiveSmallIntegerField(
        verbose_name='index de la bonne réponse',
        help_text='Entier entre 0 et 3 (inclus).',
    )
    duo_distractor_index = models.PositiveSmallIntegerField(
        verbose_name='index de la fausse réponse (mode duo)',
        help_text=(
            'En mode duo, l’interface n’affiche que deux propositions : la bonne '
            '(ci-dessus) et celle-ci. Entier entre 0 et 3, distinct de la bonne réponse.'
        ),
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(correct_index__gte=0) & Q(correct_index__lte=3),
                name='question_correct_index_between_0_and_3',
            ),
            models.CheckConstraint(
                condition=Q(duo_distractor_index__gte=0)
                & Q(duo_distractor_index__lte=3),
                name='question_duo_distractor_between_0_and_3',
            ),
            models.CheckConstraint(
                condition=Q(duo_distractor_index__lt=F('correct_index'))
                | Q(duo_distractor_index__gt=F('correct_index')),
                name='question_duo_distractor_not_correct',
            ),
        ]

    def clean(self):
        super().clean()
        self.text = (self.text or '').strip()
        for name in ('choice_0', 'choice_1', 'choice_2', 'choice_3'):
            setattr(self, name, (getattr(self, name) or '').strip())

        if not self.text:
            raise ValidationError({'text': 'L’intitulé ne peut pas être vide.'})
        for name in ('choice_0', 'choice_1', 'choice_2', 'choice_3'):
            if not getattr(self, name):
                raise ValidationError({name: 'Cette proposition ne peut pas être vide.'})

        if self.correct_index not in (0, 1, 2, 3):
            raise ValidationError(
                {'correct_index': 'La bonne réponse doit être l’index 0, 1, 2 ou 3.'}
            )
        if self.duo_distractor_index not in (0, 1, 2, 3):
            raise ValidationError(
                {
                    'duo_distractor_index': (
                        'La fausse réponse duo doit être l’index 0, 1, 2 ou 3.'
                    )
                }
            )
        if self.duo_distractor_index == self.correct_index:
            raise ValidationError(
                {
                    'duo_distractor_index': (
                        'La fausse réponse duo doit être différente de la bonne réponse.'
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text[:80] + ('…' if len(self.text) > 80 else '')


class Participant(models.Model):
    """Personne pouvant être rattachée à une ou plusieurs équipes."""

    name = models.CharField(max_length=200, verbose_name='nom')
    photo = models.ImageField(
        upload_to='participants/',
        blank=True,
        null=True,
        verbose_name='photo',
        help_text='Image de profil (facultatif pour les fiches déjà créées).',
    )

    class Meta:
        ordering = ['name']

    def clean(self):
        super().clean()
        self.name = (self.name or '').strip()
        if not self.name:
            raise ValidationError({'name': 'Le nom ne peut pas être vide.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Team(models.Model):
    """Équipe : regroupe des participants (définis en amont ou réutilisés)."""

    name = models.CharField(max_length=200, verbose_name="nom de l'équipe")
    participants = models.ManyToManyField(
        Participant,
        through='TeamMember',
        related_name='teams',
        verbose_name='participants',
    )

    class Meta:
        ordering = ['name']

    def clean(self):
        super().clean()
        self.name = (self.name or '').strip()
        if not self.name:
            raise ValidationError({'name': 'Le nom de l’équipe ne peut pas être vide.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    """Lien équipe ↔ participant (ordre d’affichage optionnel)."""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='équipe',
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        verbose_name='participant',
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="ordre dans l'équipe",
    )

    class Meta:
        ordering = ['sort_order', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=('team', 'participant'),
                name='team_member_team_participant_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.team} — {self.participant}'


class GameStatus(models.TextChoices):
    PREPARATION = 'preparation', 'Préparation'
    IN_PROGRESS = 'in_progress', 'En cours'
    FINISHED = 'finished', 'Terminée'


class GameTurn(models.TextChoices):
    """Quelle équipe doit répondre à la prochaine question (alternance après chaque réponse)."""

    TEAM_A = 'a', 'Tour équipe A'
    TEAM_B = 'b', 'Tour équipe B'


class AnswerMode(models.TextChoices):
    """Mode de réponse ; détermine les points si la réponse est correcte."""

    DUO = 'duo', 'Duo (1 pt)'
    CARRE = 'carre', 'Carré (2 pts)'
    CASH = 'cash', 'Cash (4 pts)'


POINTS_BY_ANSWER_MODE: dict[str, int] = {
    AnswerMode.DUO: 1,
    AnswerMode.CARRE: 2,
    AnswerMode.CASH: 4,
}

DRINK_GORGEES_BY_MODE: dict[str, int] = {
    AnswerMode.DUO: 2,
    AnswerMode.CARRE: 4,
    AnswerMode.CASH: 0,
}
DRINK_SHOTS_BY_MODE: dict[str, int] = {
    AnswerMode.DUO: 0,
    AnswerMode.CARRE: 0,
    AnswerMode.CASH: 1,
}


class Game(models.Model):
    """Partie à deux équipes : chaque équipe joue une question à tour de rôle."""

    team_a = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='games_as_team_a',
        verbose_name='équipe A',
    )
    team_b = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='games_as_team_b',
        verbose_name='équipe B',
    )
    next_turn_side = models.CharField(
        max_length=1,
        choices=GameTurn.choices,
        default=GameTurn.TEAM_A,
        verbose_name='prochaine question pour',
        help_text='Passe à l’autre équipe après chaque réponse enregistrée.',
    )
    status = models.CharField(
        max_length=20,
        choices=GameStatus.choices,
        default=GameStatus.PREPARATION,
        verbose_name='état',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='créée le')
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='démarrée le',
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='terminée le',
    )
    play_question_index = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='indice question (écran de jeu)',
        help_text='Progrès dans la manche (0 = première question).',
    )
    drink_gorgees_team_a = models.PositiveIntegerField(
        default=0,
        verbose_name='gorgées équipe A (erreurs)',
    )
    drink_gorgees_team_b = models.PositiveIntegerField(
        default=0,
        verbose_name='gorgées équipe B (erreurs)',
    )
    drink_shots_team_a = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='shots équipe A (erreur au cash)',
    )
    drink_shots_team_b = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='shots équipe B (erreur au cash)',
    )
    drink_gorgees_thomas = models.PositiveIntegerField(
        default=0,
        verbose_name='gorgées Thomas (bonnes réponses duo/carré)',
    )
    drink_shots_thomas = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='shots Thomas (bonne réponse cash)',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=~Q(team_a=F('team_b')),
                name='game_team_a_distinct_from_team_b',
            ),
        ]

    @property
    def team_for_turn(self) -> Team:
        if self.next_turn_side == GameTurn.TEAM_A:
            return self.team_a
        return self.team_b

    def clean(self):
        super().clean()
        if self.team_a_id and self.team_b_id and self.team_a_id == self.team_b_id:
            raise ValidationError(
                'Les deux équipes d’une partie doivent être différentes.'
            )
        if self.status == GameStatus.IN_PROGRESS and self.started_at is None:
            raise ValidationError(
                {'started_at': 'Une partie en cours doit avoir une date de début.'}
            )
        if self.status == GameStatus.FINISHED:
            if self.started_at is None:
                raise ValidationError(
                    {'started_at': 'Une partie terminée doit avoir été démarrée.'}
                )
            if self.finished_at is None:
                raise ValidationError(
                    {'finished_at': 'Une partie terminée doit avoir une date de fin.'}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._ensure_score_rows()

    def _ensure_score_rows(self):
        if not self.team_a_id or not self.team_b_id:
            return
        for team in (self.team_a, self.team_b):
            GameTeamScore.objects.get_or_create(
                game=self,
                team=team,
                defaults={
                    'correct_answers_count': 0,
                    'wrong_answers_count': 0,
                    'correct_by_duo_count': 0,
                    'correct_by_carre_count': 0,
                    'correct_by_cash_count': 0,
                },
            )

    def start(self):
        """Passe la partie en « En cours » si les deux équipes ont au moins un participant."""
        if self.status != GameStatus.PREPARATION:
            raise ValidationError(
                'La partie ne peut être démarrée que depuis l’état « Préparation ».'
            )
        if not self.team_a.memberships.exists():
            raise ValidationError(
                'Impossible de démarrer : l’équipe A n’a aucun participant.'
            )
        if not self.team_b.memberships.exists():
            raise ValidationError(
                'Impossible de démarrer : l’équipe B n’a aucun participant.'
            )
        self.status = GameStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.next_turn_side = GameTurn.TEAM_A
        self.play_question_index = 0
        self.save()
        GameTeamScore.objects.filter(game=self).update(
            correct_answers_count=0,
            wrong_answers_count=0,
            correct_by_duo_count=0,
            correct_by_carre_count=0,
            correct_by_cash_count=0,
        )
        Game.objects.filter(pk=self.pk).update(
            drink_gorgees_team_a=0,
            drink_gorgees_team_b=0,
            drink_shots_team_a=0,
            drink_shots_team_b=0,
            drink_gorgees_thomas=0,
            drink_shots_thomas=0,
        )

    def advance_turn(self) -> None:
        """Alterne le tour après une question jouée (bonne ou mauvaise réponse)."""
        nxt = (
            GameTurn.TEAM_B
            if self.next_turn_side == GameTurn.TEAM_A
            else GameTurn.TEAM_A
        )
        Game.objects.filter(pk=self.pk).update(next_turn_side=nxt)
        self.refresh_from_db(fields=('next_turn_side',))

    def _require_in_progress_turn(self, team: Team) -> GameTeamScore:
        if self.status != GameStatus.IN_PROGRESS:
            raise ValidationError(
                'Les réponses ne peuvent être enregistrées que pendant une partie en cours.'
            )
        if team not in (self.team_a, self.team_b):
            raise ValidationError(
                'Cette équipe ne fait pas partie de la partie.'
            )
        if team.pk != self.team_for_turn.pk:
            raise ValidationError(
                f'Ce n’est pas le tour de « {team.name} » (prochain tour : '
                f'« {self.team_for_turn.name} »).'
            )
        return GameTeamScore.objects.get(game=self, team=team)

    def register_correct_answer(self, team: Team, mode: str) -> None:
        """Compte une bonne réponse pour l’équipe dont c’est le tour, puis passe le tour."""
        if not self.pk:
            raise ValidationError('Enregistrez la partie avant de compter les réponses.')
        if mode not in AnswerMode.values:
            raise ValidationError(
                f'Mode de réponse invalide (attendu : {", ".join(AnswerMode.values)}).'
            )
        self._require_in_progress_turn(team)
        mode_counter = {
            AnswerMode.DUO: 'correct_by_duo_count',
            AnswerMode.CARRE: 'correct_by_carre_count',
            AnswerMode.CASH: 'correct_by_cash_count',
        }[mode]
        stats_qs = GameTeamScore.objects.filter(game=self, team=team)
        stats_qs.update(
            correct_answers_count=F('correct_answers_count') + 1,
            **{mode_counter: F(mode_counter) + 1},
        )
        g_inc = DRINK_GORGEES_BY_MODE[mode]
        s_inc = DRINK_SHOTS_BY_MODE[mode]
        if g_inc:
            Game.objects.filter(pk=self.pk).update(
                drink_gorgees_thomas=F('drink_gorgees_thomas') + g_inc,
            )
        if s_inc:
            Game.objects.filter(pk=self.pk).update(
                drink_shots_thomas=F('drink_shots_thomas') + s_inc,
            )
        self.advance_turn()

    def register_wrong_answer(self, team: Team, mode: str) -> None:
        if not self.pk:
            raise ValidationError('Enregistrez la partie avant de compter les réponses.')
        if mode not in AnswerMode.values:
            raise ValidationError(
                f'Mode de réponse invalide (attendu : {", ".join(AnswerMode.values)}).'
            )
        self._require_in_progress_turn(team)
        GameTeamScore.objects.filter(game=self, team=team).update(
            wrong_answers_count=F('wrong_answers_count') + 1,
        )
        g_inc = DRINK_GORGEES_BY_MODE[mode]
        s_inc = DRINK_SHOTS_BY_MODE[mode]
        if team.pk == self.team_a_id:
            u: dict = {}
            if g_inc:
                u['drink_gorgees_team_a'] = F('drink_gorgees_team_a') + g_inc
            if s_inc:
                u['drink_shots_team_a'] = F('drink_shots_team_a') + s_inc
            if u:
                Game.objects.filter(pk=self.pk).update(**u)
        elif team.pk == self.team_b_id:
            u = {}
            if g_inc:
                u['drink_gorgees_team_b'] = F('drink_gorgees_team_b') + g_inc
            if s_inc:
                u['drink_shots_team_b'] = F('drink_shots_team_b') + s_inc
            if u:
                Game.objects.filter(pk=self.pk).update(**u)
        else:
            raise ValidationError('Équipe inconnue pour cette partie.')
        self.advance_turn()

    def apply_anecdote_shot_split(self, team: Team) -> int:
        """
        Moitié des shots Thomas → équipe visée ; Thomas garde le reste.
        Retourne le nombre de shots transférés.
        """
        if not self.pk:
            raise ValidationError('Partie non enregistrée.')
        if team.pk not in (self.team_a_id, self.team_b_id):
            raise ValidationError('Équipe inconnue pour cette partie.')
        self.refresh_from_db(
            fields=(
                'drink_shots_thomas',
                'drink_shots_team_a',
                'drink_shots_team_b',
            ),
        )
        n = self.drink_shots_thomas
        if n <= 0:
            return 0
        transfer = n // 2
        if transfer <= 0:
            return 0
        thomas_keeps = n - transfer
        updates: dict = {'drink_shots_thomas': thomas_keeps}
        if team.pk == self.team_a_id:
            updates['drink_shots_team_a'] = F('drink_shots_team_a') + transfer
        else:
            updates['drink_shots_team_b'] = F('drink_shots_team_b') + transfer
        Game.objects.filter(pk=self.pk).update(**updates)
        return transfer

    def finish(self):
        """Termine une partie en cours."""
        if self.status != GameStatus.IN_PROGRESS:
            raise ValidationError(
                'Seule une partie en cours peut être terminée ainsi.'
            )
        self.status = GameStatus.FINISHED
        self.finished_at = timezone.now()
        self.save()

    def __str__(self):
        pk_bit = f'#{self.pk}' if self.pk else 'nouvelle'
        a = self.team_a.name if self.team_a_id else '…'
        b = self.team_b.name if self.team_b_id else '…'
        return f'Partie {pk_bit} — {a} vs {b} ({self.get_status_display()})'


class GameTeamScore(models.Model):
    """Scores et compteurs pour une équipe dans une partie."""

    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='scores_by_team',
        verbose_name='partie',
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='game_scores',
        verbose_name='équipe',
    )
    correct_answers_count = models.PositiveIntegerField(
        default=0,
        verbose_name='bonnes réponses',
    )
    wrong_answers_count = models.PositiveIntegerField(
        default=0,
        verbose_name='mauvaises réponses',
    )
    correct_by_duo_count = models.PositiveIntegerField(
        default=0,
        verbose_name='bonnes réponses (mode duo)',
    )
    correct_by_carre_count = models.PositiveIntegerField(
        default=0,
        verbose_name='bonnes réponses (mode carré)',
    )
    correct_by_cash_count = models.PositiveIntegerField(
        default=0,
        verbose_name='bonnes réponses (mode cash)',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('game', 'team'),
                name='gameteamscore_game_team_uniq',
            ),
        ]

    @property
    def score_total(self) -> int:
        return (
            self.correct_by_duo_count * POINTS_BY_ANSWER_MODE[AnswerMode.DUO]
            + self.correct_by_carre_count * POINTS_BY_ANSWER_MODE[AnswerMode.CARRE]
            + self.correct_by_cash_count * POINTS_BY_ANSWER_MODE[AnswerMode.CASH]
        )

    def __str__(self):
        return f'{self.game_id} — {self.team}: {self.score_total} pts'
