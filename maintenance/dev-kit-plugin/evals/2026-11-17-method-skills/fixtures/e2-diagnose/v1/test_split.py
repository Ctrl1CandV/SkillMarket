import unittest

from split import split


class SplitTest(unittest.TestCase):
    def test_even(self):
        self.assertEqual(split(100.0, 4), [25.0, 25.0, 25.0, 25.0])

    def test_remainder_goes_to_first(self):
        self.assertEqual(split(10.0, 3), [3.34, 3.33, 3.33])

    def test_half(self):
        self.assertEqual(split(12.5, 2), [6.25, 6.25])

    def test_bad_n(self):
        with self.assertRaises(ValueError):
            split(10.0, 0)


if __name__ == "__main__":
    unittest.main()
