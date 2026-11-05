import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import codequiz


def test_a_one_line_choice_sits_after_its_letter():
    assert codequiz.format_choice("B", "HelloWorld") == "  B) HelloWorld"


def test_every_line_of_a_multi_line_choice_lines_up_under_the_first():
    assert codequiz.format_choice("A", "Hello\nWorld") == "  A) Hello\n     World"
