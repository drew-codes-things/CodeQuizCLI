import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import codequiz

LESSONS = [
    {"id": "intro", "title": "Intro", "unit_title": "Basics", "exercises": [{"q": 1}, {"q": 2}, {"q": 3}]},
    {"id": "loops", "title": "Loops", "unit_title": "Basics", "exercises": [{"q": 4}]},
]


@pytest.fixture(autouse=True)
def private_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(codequiz, "CACHE_DIR", str(tmp_path))


def answer_with(monkeypatch, answers):
    asked = []

    def fake_exercise(exercise, number, total):
        asked.append(exercise["q"])
        outcome = answers.pop(0)
        if outcome == "quit":
            raise KeyboardInterrupt
        return outcome, "x"

    monkeypatch.setattr(codequiz, "run_exercise", fake_exercise)
    return asked


def test_an_interrupted_lesson_picks_up_where_it_stopped(monkeypatch):
    asked = answer_with(monkeypatch, [True, False, "quit"])
    with pytest.raises(KeyboardInterrupt):
        codequiz.run_quiz("python", LESSONS, 0)
    assert asked == [1, 2, 3]

    asked = answer_with(monkeypatch, [True, True])
    codequiz.run_quiz("python", LESSONS, 0)
    assert asked == [3, 2]
    progress = codequiz.course_progress(codequiz.load_progress(), "python")
    assert progress["completed"] == ["intro"] and "inProgress" not in progress
    assert progress["history"]["intro"]["lastScore"] == "2/3"


def test_restart_ignores_the_saved_position(monkeypatch):
    answer_with(monkeypatch, [True, "quit"])
    with pytest.raises(KeyboardInterrupt):
        codequiz.run_quiz("python", LESSONS, 0)
    asked = answer_with(monkeypatch, [True, True, True])
    codequiz.run_quiz("python", LESSONS, 0, restart=True)
    assert asked == [1, 2, 3]


def test_continue_prefers_the_unfinished_lesson_then_the_next_unlocked_one(monkeypatch):
    assert codequiz.next_lesson_index("python", LESSONS) == 0
    answer_with(monkeypatch, [True, True, True])
    codequiz.run_quiz("python", LESSONS, 0)
    assert codequiz.next_lesson_index("python", LESSONS) == 1
    answer_with(monkeypatch, [True])
    codequiz.run_quiz("python", LESSONS, 1)
    assert codequiz.next_lesson_index("python", LESSONS) is None


def test_a_changed_lesson_starts_fresh(monkeypatch):
    answer_with(monkeypatch, [True, "quit"])
    with pytest.raises(KeyboardInterrupt):
        codequiz.run_quiz("python", LESSONS, 0)
    changed = [{**LESSONS[0], "exercises": [{"q": 9}, {"q": 8}]}]
    asked = answer_with(monkeypatch, [True, True])
    codequiz.run_quiz("python", changed, 0)
    assert asked == [9, 8]
