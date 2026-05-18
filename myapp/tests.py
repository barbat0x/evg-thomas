from django.test import TestCase

from myapp import play_helpers
from myapp.models import Question


class CashAnswerMatchTests(TestCase):
    def _question(
        self,
        correct_text: str,
        *,
        correct_index: int = 0,
        distractor: int = 1,
    ) -> Question:
        choices = ['a', 'b', 'c', 'd']
        choices[correct_index] = correct_text
        other = next(i for i in range(4) if i != correct_index)
        choices[other] = 'autre'
        return Question(
            text='Q',
            choice_0=choices[0],
            choice_1=choices[1],
            choice_2=choices[2],
            choice_3=choices[3],
            correct_index=correct_index,
            duo_distractor_index=distractor if distractor != correct_index else 1,
        )

    def test_cash_matches_ignore_case_accents_spaces(self):
        q = self._question('Noël à Paris')
        self.assertTrue(play_helpers.cash_answer_matches(q, '  NOEL A PARIS  '))
        self.assertTrue(play_helpers.cash_answer_matches(q, 'Noel a paris'))

    def test_cash_hyphens_vs_spaces(self):
        q = self._question('Saint-Étienne')
        self.assertTrue(play_helpers.cash_answer_matches(q, 'saint etienne'))

    def test_cash_wrong_answer(self):
        q = self._question('Lyon')
        self.assertFalse(play_helpers.cash_answer_matches(q, 'Marseille'))
