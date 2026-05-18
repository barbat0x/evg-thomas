# Add play progress index for the play screen.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_participant_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='play_question_index',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Progrès dans la manche (0 = première question).',
                verbose_name='indice question (écran de jeu)',
            ),
        ),
    ]
