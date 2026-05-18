# Generated manually for two-team games with per-team scores.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


def forwards_migrate_games(apps, schema_editor):
    Game = apps.get_model('myapp', 'Game')
    Team = apps.get_model('myapp', 'Team')
    GameTeamScore = apps.get_model('myapp', 'GameTeamScore')
    for game in Game.objects.all():
        old_team_id = game.team_id
        game.team_a_id = old_team_id
        other = Team.objects.exclude(pk=old_team_id).first()
        if other is None:
            other = Team.objects.create(name='Équipe B (à renommer)')
        game.team_b_id = other.pk
        game.save(update_fields=['team_a_id', 'team_b_id'])

        GameTeamScore.objects.create(
            game=game,
            team_id=old_team_id,
            correct_answers_count=game.correct_answers_count,
            wrong_answers_count=game.wrong_answers_count,
            correct_by_duo_count=game.correct_by_duo_count,
            correct_by_carre_count=game.correct_by_carre_count,
            correct_by_cash_count=game.correct_by_cash_count,
        )
        GameTeamScore.objects.create(
            game=game,
            team_id=other.pk,
            correct_answers_count=0,
            wrong_answers_count=0,
            correct_by_duo_count=0,
            correct_by_carre_count=0,
            correct_by_cash_count=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_game_answer_mode_points'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameTeamScore',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'correct_answers_count',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='bonnes réponses',
                    ),
                ),
                (
                    'wrong_answers_count',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='mauvaises réponses',
                    ),
                ),
                (
                    'correct_by_duo_count',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='bonnes réponses (mode duo)',
                    ),
                ),
                (
                    'correct_by_carre_count',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='bonnes réponses (mode carré)',
                    ),
                ),
                (
                    'correct_by_cash_count',
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name='bonnes réponses (mode cash)',
                    ),
                ),
                (
                    'game',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='scores_by_team',
                        to='myapp.game',
                        verbose_name='partie',
                    ),
                ),
                (
                    'team',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='game_scores',
                        to='myapp.team',
                        verbose_name='équipe',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(
                        fields=('game', 'team'),
                        name='gameteamscore_game_team_uniq',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='game',
            name='team_a',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='games_as_team_a',
                to='myapp.team',
                verbose_name='équipe A',
            ),
        ),
        migrations.AddField(
            model_name='game',
            name='team_b',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='games_as_team_b',
                to='myapp.team',
                verbose_name='équipe B',
            ),
        ),
        migrations.AddField(
            model_name='game',
            name='next_turn_side',
            field=models.CharField(
                choices=[('a', 'Tour équipe A'), ('b', 'Tour équipe B')],
                default='a',
                help_text='Passe à l’autre équipe après chaque réponse enregistrée.',
                max_length=1,
                verbose_name='prochaine question pour',
            ),
        ),
        migrations.RunPython(forwards_migrate_games, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='game',
            name='correct_by_cash_count',
        ),
        migrations.RemoveField(
            model_name='game',
            name='correct_by_carre_count',
        ),
        migrations.RemoveField(
            model_name='game',
            name='correct_by_duo_count',
        ),
        migrations.RemoveField(
            model_name='game',
            name='wrong_answers_count',
        ),
        migrations.RemoveField(
            model_name='game',
            name='correct_answers_count',
        ),
        migrations.RemoveField(
            model_name='game',
            name='team',
        ),
        migrations.AlterField(
            model_name='game',
            name='team_a',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='games_as_team_a',
                to='myapp.team',
                verbose_name='équipe A',
            ),
        ),
        migrations.AlterField(
            model_name='game',
            name='team_b',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='games_as_team_b',
                to='myapp.team',
                verbose_name='équipe B',
            ),
        ),
        migrations.AddConstraint(
            model_name='game',
            constraint=models.CheckConstraint(
                condition=~Q(team_a=F('team_b')),
                name='game_team_a_distinct_from_team_b',
            ),
        ),
    ]
