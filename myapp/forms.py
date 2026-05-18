from __future__ import annotations

from django import forms

from myapp.models import Game, Participant, Team, TeamMember


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ('name', 'photo')
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'class': 'input-file'}),
        }


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ('name',)


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ('team', 'participant')


class TeamMemberAddForm(forms.ModelForm):
    """Ajout d’un membre à une équipe donnée (hors de la liste déjà dans l’équipe)."""

    class Meta:
        model = TeamMember
        fields = ('participant',)

    def __init__(self, *args, team: Team | None = None, **kwargs):
        self._team = team
        super().__init__(*args, **kwargs)
        if team is not None:
            taken = TeamMember.objects.filter(team=team).values_list(
                'participant_id',
                flat=True,
            )
            self.fields['participant'].queryset = Participant.objects.exclude(
                pk__in=taken,
            ).order_by('name')


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ('team_a', 'team_b')

    def clean(self):
        cleaned = super().clean()
        ta = cleaned.get('team_a')
        tb = cleaned.get('team_b')
        if ta and tb and ta.pk == tb.pk:
            raise forms.ValidationError(
                'Choisissez deux équipes différentes pour la même partie.'
            )
        return cleaned
