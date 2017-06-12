import pytest
import diffutils
from diffutils.engine import DiffEngine

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


def do_test_engine(engine):
    patch = engine.diff(original_text, changed_text)
    assert patch is not None, "Could not generate patch!"
    patched_text = diffutils.patch(original_text, patch)
    assert patched_text == changed_text, "Patching the original didn't create the changed"
    unified_diff = diffutils.generate_unified_diff("a", "b", original_text, patch, 1)
    assert unified_diff is not None, "Could not generate unified diff"
    parsed_patch = diffutils.parse_unified_diff(unified_diff)
    patched_text = diffutils.patch(original_text, parsed_patch)
    assert patched_text == changed_text, "Patching the original with the parsed unified diff didn't create the chagned"

def test_engine():
    do_test_engine(DiffEngine.create())
