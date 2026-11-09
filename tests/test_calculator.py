import unittest

from pria.core.calculator import answer_simple_math


class CalculatorTests(unittest.TestCase):
    def test_natural_portuguese_arithmetic(self):
        self.assertEqual(answer_simple_math("Quanto é 2 mais 2?"), "4")
        self.assertEqual(answer_simple_math("Calcule (15 vezes 3) menos 5"), "40")
        self.assertEqual(answer_simple_math("Quanto e 1,5 + 2?"), "3.5")

    def test_rejects_code_and_bounds_large_exponents(self):
        self.assertIsNone(answer_simple_math("calcule __import__('os').system('whoami')"))
        self.assertIn("expoente limitado", answer_simple_math("calcule 2 elevado a 99") or "")

    def test_general_question_is_left_for_model(self):
        self.assertIsNone(answer_simple_math("Explique a gravidade"))


if __name__ == "__main__":
    unittest.main()
