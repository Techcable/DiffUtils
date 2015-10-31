import unittest
import diffutils

original_text = ["Once upon a time there was a snail named Bob",
                 "Bob the snail was stupid",
                 "Bob's dad was a cow farmer",
                 "Bob liked to eat cows",
                 "This didn't work out so well for bob.",
                 "",
                 "Bob liked cows, but he ate them anyway",
                 "He decided to see a therapist.",
                 "Bob's dad didn't like therapists, so Bob's dad beat the therapist up",
                 "Before the therapist died, he called the police who shot Bob and his dad.",
                 "This made the towns people very happy.",
                 "",
                 "======",
                 "======",
                 "The End"]

changed_text = ["Once upon a time there was a snail named Bob",
                "Bob the snail was smart",
                "Bob's dad was a cow farmer",
                "Bob liked to eat cows",
                "This worked out very well for bob.",
                "",
                "Bob liked money, so he decided to sell cows and not eat them.",
                "He decided to see a trader.",
                "Bob's dad didn't like traders, so Bob's dad beat the trader up",
                "Before the trader died, he called the police who shot Bob and his dad.",
                "This made the towns people very happy.",
                "",
                "The police officer flew to the moon.",
                "Then the moon police shot the earth police officer.",
                "======",
                "======"]


class PatchTest(unittest.TestCase):
    def setUp(self):
        self.patch = diffutils.diff(original_text, changed_text)

    def test_patch_creation(self):
        self.assertIsNotNone(self.patch, "Could not generate patch")

    def test_diff_application(self):
        recreated_from_patch = diffutils.patch(original_text, self.patch)
        self.assertEqual(recreated_from_patch, changed_text, "Patching the original did not create the original text")


class UnifiedDiffTest(unittest.TestCase):
    def setUp(self):
        self.patch = diffutils.diff(original_text, changed_text)
        self.unified_diff = diffutils.generate_unified_diff("a", "b", original_text, self.patch, 1)

    def test_unified_diff_creation(self):
        self.assertIsNotNone(self.unified_diff, "Could not generate unified diff")

    def test_unified_diff_parsing(self):
        parsed_patch = diffutils.parse_unified_diff(self.unified_diff)



if __name__ == '__main__':
    unittest.main()
