from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from myapp.models import Game, GameTeamScore, Participant, Question, Team, TeamMember


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 1
    autocomplete_fields = ('participant',)
    ordering = ('sort_order', 'pk')


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'photo_preview')
    search_fields = ('name',)

    @admin.display(description='aperçu')
    def photo_preview(self, obj: Participant):
        if not obj.photo:
            return '—'
        return format_html(
            '<img src="{}" alt="" width="40" height="40" '
            'style="object-fit:cover;border-radius:6px;vertical-align:middle;" />',
            obj.photo.url,
        )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count_display')
    search_fields = ('name',)
    inlines = (TeamMemberInline,)

    @admin.display(description='participants')
    def member_count_display(self, obj):
        return obj.memberships.count()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'correct_index', 'duo_distractor_index')
    search_fields = ('text', 'choice_0', 'choice_1', 'choice_2', 'choice_3')


class GameTeamScoreInline(admin.TabularInline):
    model = GameTeamScore
    extra = 0
    can_delete = False
    fields = (
        'team',
        'correct_answers_count',
        'wrong_answers_count',
        'correct_by_duo_count',
        'correct_by_carre_count',
        'correct_by_cash_count',
        'score_total_display',
    )
    readonly_fields = fields

    @admin.display(description='score')
    def score_total_display(self, obj: GameTeamScore) -> int:
        return obj.score_total


def _format_validation_error(exc: ValidationError) -> str:
    if hasattr(exc, 'message_dict'):
        parts = []
        for field, msgs in exc.message_dict.items():
            parts.append(f'{field}: {"; ".join(msgs)}')
        return ' | '.join(parts)
    return '; '.join(exc.messages)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'team_a',
        'team_b',
        'status',
        'next_turn_side',
        'created_at',
        'started_at',
        'finished_at',
    )
    list_filter = ('status',)
    autocomplete_fields = ('team_a', 'team_b')
    readonly_fields = ('created_at',)
    inlines = (GameTeamScoreInline,)
    actions = ('start_games', 'finish_games')

    @admin.action(description='Démarrer la partie (préparation → en cours)')
    def start_games(self, request, queryset):
        started = 0
        for game in queryset:
            try:
                game.start()
                started += 1
            except ValidationError as e:
                self.message_user(
                    request,
                    f'Partie #{game.pk} — {_format_validation_error(e)}',
                    level=messages.ERROR,
                )
        if started:
            self.message_user(
                request,
                f'{started} partie(s) démarrée(s).',
                level=messages.SUCCESS,
            )

    @admin.action(description='Terminer la partie (en cours → terminée)')
    def finish_games(self, request, queryset):
        finished = 0
        for game in queryset:
            try:
                game.finish()
                finished += 1
            except ValidationError as e:
                self.message_user(
                    request,
                    f'Partie #{game.pk} — {_format_validation_error(e)}',
                    level=messages.ERROR,
                )
        if finished:
            self.message_user(
                request,
                f'{finished} partie(s) terminée(s).',
                level=messages.SUCCESS,
            )


@admin.register(GameTeamScore)
class GameTeamScoreAdmin(admin.ModelAdmin):
    list_display = (
        'game',
        'team',
        'score_total_display',
        'correct_answers_count',
        'wrong_answers_count',
    )
    list_filter = ('game',)
    search_fields = ('team__name',)

    @admin.display(description='score')
    def score_total_display(self, obj: GameTeamScore) -> int:
        return obj.score_total
