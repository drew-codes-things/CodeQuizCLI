#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
CACHE_DIR = os.path.join(XDG_CACHE_HOME, "codequiz")
CONTENT_BASE_URL = os.environ.get("CODEQUIZ_CONTENT_BASE", "https://drew-gnr.xyz/code/content")
CACHE_MAX_AGE = 7 * 24 * 60 * 60
USER_AGENT = "CodeQuizCLI/1.0 (+https://github.com/drew-codes-things/CodeQuizCLI)"

COURSES = {
    "python": "Python",
    "javascript": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    "php": "PHP",
}

QUIZ_TYPES = {"mcq", "predict", "blank", "parsons"}
STATUS_MARK = {"locked": "\U0001F512", "available": "▸", "complete": "✓"}


def supports_color(no_color_flag=False):
    if no_color_flag or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


class Colors:
    def __init__(self, no_color_flag=False):
        on = supports_color(no_color_flag)
        self.green = "\033[32m" if on else ""
        self.red = "\033[31m" if on else ""
        self.yellow = "\033[33m" if on else ""
        self.dim = "\033[2m" if on else ""
        self.bold = "\033[1m" if on else ""
        self.reset = "\033[0m" if on else ""


c = Colors()


def content_cache_path(course):
    return os.path.join(CACHE_DIR, "content", f"{course}.json")


def progress_path():
    return os.path.join(CACHE_DIR, "progress.json")


def fetch_course(course, force=False):
    path = content_cache_path(course)
    fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path) < CACHE_MAX_AGE)
    if fresh and not force:
        cached = read_cached_course(path)
        if cached is not None:
            return cached

    url = f"{CONTENT_BASE_URL}/{course}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        course_data = json.loads(data)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return course_data
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
        cached = read_cached_course(path)
        if cached is not None:
            print(f"{c.yellow}Could not fetch fresh content ({e}). Using the cached copy.{c.reset}", file=sys.stderr)
            return cached
        print(f"{c.red}Error: could not fetch {course} and no cached copy exists.{c.reset}", file=sys.stderr)
        sys.exit(1)


def read_cached_course(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_progress():
    p = progress_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_progress(progress):
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = progress_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)
    os.replace(tmp, progress_path())


def course_progress(progress, course):
    return progress.setdefault(course, {"completed": [], "history": {}})


def flatten_lessons(data):
    flat = []
    for unit in data.get("units", []):
        if unit.get("comingSoon"):
            continue
        for lesson in unit.get("lessons", []):
            quiz_exercises = [ex for ex in lesson.get("exercises", []) if ex.get("type") in QUIZ_TYPES]
            if not quiz_exercises:
                continue
            flat.append({
                "id": lesson["id"],
                "title": lesson["title"],
                "unit_title": unit.get("title", ""),
                "exercises": quiz_exercises,
            })
    return flat


def lesson_status(flat, index, completed_set):
    lesson = flat[index]
    if lesson["id"] in completed_set:
        return "complete"
    if index == 0:
        return "available"
    return "available" if flat[index - 1]["id"] in completed_set else "locked"


def find_lesson(flat, lesson_id):
    for i, lesson in enumerate(flat):
        if lesson["id"] == lesson_id:
            return i, lesson
    return None, None


def list_courses():
    print(f"{c.bold}Courses{c.reset}")
    for slug, label in COURSES.items():
        print(f"  {slug:12s} {label}")
    print()
    print("Usage:")
    print("  codequiz <course>              list lessons and their lock status")
    print("  codequiz <course> <lesson-id>  take a quiz")
    print("  codequiz --update              refresh cached content for all courses")
    print("  codequiz <course> --continue   resume where you left off, or start the next lesson")
    print("  codequiz <course> --reset      clear local progress for a course")


def list_lessons(course):
    data = fetch_course(course)
    flat = flatten_lessons(data)
    progress = load_progress()
    completed = set(course_progress(progress, course)["completed"])

    print(f"{c.bold}{COURSES[course]}{c.reset} ({len(flat)} lessons)\n")
    last_unit = None
    for i, lesson in enumerate(flat):
        if lesson["unit_title"] != last_unit:
            print(f"{c.dim}{lesson['unit_title']}{c.reset}")
            last_unit = lesson["unit_title"]
        status = lesson_status(flat, i, completed)
        mark = STATUS_MARK[status]
        print(f"  {mark} {lesson['id']:24s} {lesson['title']}")
    print()
    print(f"Run {c.bold}codequiz {course} <lesson-id>{c.reset} to take a quiz.")


def format_choice(letter, choice):
    first, *rest = str(choice).splitlines() or [""]
    indent = " " * len(f"  {letter}) ")
    return "\n".join([f"  {letter}) {first}", *(indent + line for line in rest)])


def prompt_choice(exercise, index, total):
    print(f"{c.bold}[{index}/{total}]{c.reset} {exercise['prompt']}")
    if exercise.get("code"):
        print()
        for line in exercise["code"].splitlines():
            print(f"    {c.dim}{line}{c.reset}")
    print()
    letters = [chr(65 + i) for i in range(len(exercise["choices"]))]
    for letter, choice in zip(letters, exercise["choices"]):
        print(format_choice(letter, choice))
    while True:
        raw = input(f"\n{c.bold}> {c.reset}").strip().upper()
        if raw and raw[0] in letters:
            return letters.index(raw[0])
        print(f"Enter one of: {', '.join(letters)}")


def check_choice(exercise, given_index):
    correct = given_index == exercise["answer"]
    return correct, exercise["choices"][exercise["answer"]]


def prompt_blank(exercise, index, total):
    print(f"{c.bold}[{index}/{total}]{c.reset} {exercise['prompt']}\n")
    segments = exercise["template"].split("___")
    print("    " + "____".join(segments))
    print()
    blanks = len(segments) - 1
    answers = []
    for b in range(blanks):
        raw = input(f"  blank {b + 1}: ").strip()
        answers.append(raw)
    return answers


def check_blank(exercise, given):
    expected = exercise.get("answers") or []
    alt_lists = exercise.get("alternatives") or []
    if len(given) != len(expected):
        return False, expected
    all_correct = True
    for i, value in enumerate(given):
        alt = alt_lists[i] if i < len(alt_lists) else []
        if value != expected[i] and value not in (alt or []):
            all_correct = False
    return all_correct, expected


def prompt_parsons(exercise, index, total):
    print(f"{c.bold}[{index}/{total}]{c.reset} {exercise['prompt']}\n")
    lines = exercise["lines"]
    shuffled = list(enumerate(lines))
    random.shuffle(shuffled)
    for i, (_, line) in enumerate(shuffled):
        print(f"  {i + 1}) {line}")
    print()
    n = len(shuffled)
    while True:
        raw = input(f"Enter the order as numbers, e.g. {','.join(str(x) for x in range(n, 0, -1))}: ").strip()
        parts = [x for x in re.split(r"[,\s]+", raw) if x]
        try:
            order = [int(x) for x in parts]
        except ValueError:
            order = []
        if sorted(order) == list(range(1, n + 1)):
            break
        print(f"Enter each number 1-{n} exactly once, separated by commas.")
    return [shuffled[i - 1][1] for i in order]


def check_parsons(exercise, given):
    return given == exercise["lines"], exercise["lines"]


def run_exercise(exercise, index, total):
    kind = exercise["type"]
    if kind in ("mcq", "predict"):
        given = prompt_choice(exercise, index, total)
        return check_choice(exercise, given)
    if kind == "blank":
        given = prompt_blank(exercise, index, total)
        return check_blank(exercise, given)
    if kind == "parsons":
        given = prompt_parsons(exercise, index, total)
        return check_parsons(exercise, given)
    raise ValueError(f"unsupported exercise type: {kind}")


def format_expected(expected):
    if isinstance(expected, list):
        return "\n".join(f"    {line}" for line in expected)
    return str(expected)


def saved_position(course, lesson):
    saved = course_progress(load_progress(), course).get("inProgress")
    if not saved or saved.get("lesson") != lesson["id"] or saved.get("total") != len(lesson["exercises"]):
        return None
    return saved


def save_position(course, lesson, queue, correct_first_try):
    progress = load_progress()
    course_progress(progress, course)["inProgress"] = {
        "lesson": lesson["id"],
        "total": len(lesson["exercises"]),
        "queue": [{"number": item["number"], "retry": item["retry"]} for item in queue],
        "correctFirstTry": correct_first_try,
    }
    save_progress(progress)


def starting_queue(course, lesson, restart):
    exercises = lesson["exercises"]
    saved = None if restart else saved_position(course, lesson)
    if saved is None:
        return [{"exercise": ex, "number": n, "retry": False} for n, ex in enumerate(exercises, 1)], 0
    queue = [{"exercise": exercises[item["number"] - 1], "number": item["number"], "retry": item["retry"]}
             for item in saved["queue"] if 1 <= item["number"] <= len(exercises)]
    done = len(exercises) - len({item["number"] for item in queue})
    print(f"{c.dim}Picking up where you left off ({done}/{len(exercises)} done). Use --restart to start over.{c.reset}")
    return queue, saved.get("correctFirstTry", 0)


def next_lesson_index(course, flat):
    cp = course_progress(load_progress(), course)
    in_progress = (cp.get("inProgress") or {}).get("lesson")
    completed = set(cp["completed"])
    if in_progress:
        index, _ = find_lesson(flat, in_progress)
        if index is not None and lesson_status(flat, index, completed) != "locked":
            return index
    for index in range(len(flat)):
        if lesson_status(flat, index, completed) == "available":
            return index
    return None


def run_quiz(course, flat, index, restart=False):
    lesson = flat[index]
    total = len(lesson["exercises"])

    print(f"\n{c.bold}{lesson['title']}{c.reset}\n")
    queue, correct_first_try = starting_queue(course, lesson, restart)

    while queue:
        item = queue.pop(0)
        exercise = item["exercise"]

        if item["retry"]:
            print(f"{c.yellow}(retry){c.reset}")
        correct, expected = run_exercise(exercise, item["number"], total)

        if correct:
            if not item["retry"]:
                correct_first_try += 1
            print(f"{c.green}Correct.{c.reset}")
        else:
            print(f"{c.red}Not quite.{c.reset} Expected:\n{format_expected(expected)}")
            if not item["retry"]:
                queue.append({**item, "retry": True})
        if exercise.get("explain"):
            print(f"{c.dim}{exercise['explain']}{c.reset}")
        print()
        save_position(course, lesson, queue, correct_first_try)

    accuracy = round(100 * correct_first_try / total) if total else 100
    print(f"{c.bold}Lesson complete.{c.reset} {correct_first_try}/{total} correct first try ({accuracy}%).\n")

    progress = load_progress()
    cp = course_progress(progress, course)
    if lesson["id"] not in cp["completed"]:
        cp["completed"].append(lesson["id"])
    hist = cp["history"].setdefault(lesson["id"], {"attempts": 0})
    hist["attempts"] += 1
    hist["lastScore"] = f"{correct_first_try}/{total}"
    hist["lastAttemptAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    cp.pop("inProgress", None)
    save_progress(progress)


def cmd_continue(course, restart):
    flat = flatten_lessons(fetch_course(course))
    index = next_lesson_index(course, flat)
    if index is None:
        print(f"{c.green}Every {COURSES[course]} lesson is complete.{c.reset} Retake one with codequiz {course} <lesson-id>.")
        return
    run_quiz(course, flat, index, restart)


def cmd_lesson(course, lesson_id, restart=False):
    data = fetch_course(course)
    flat = flatten_lessons(data)
    index, lesson = find_lesson(flat, lesson_id)
    if lesson is None:
        print(f"{c.red}No lesson '{lesson_id}' in {course}.{c.reset} Run `codequiz {course}` to see valid ids.")
        sys.exit(1)

    progress = load_progress()
    completed = set(course_progress(progress, course)["completed"])
    status = lesson_status(flat, index, completed)
    if status == "locked":
        prev = flat[index - 1]
        print(f"{c.yellow}'{lesson['title']}' is locked.{c.reset} Complete '{prev['title']}' ({prev['id']}) first.")
        sys.exit(1)

    run_quiz(course, flat, index, restart)


def cmd_reset(course):
    progress = load_progress()
    if course in progress:
        del progress[course]
        save_progress(progress)
    print(f"Progress for {course} cleared.")


def main():
    global c
    parser = argparse.ArgumentParser(prog="codequiz", add_help=True)
    parser.add_argument("course", nargs="?", help="course slug, e.g. python")
    parser.add_argument("lesson", nargs="?", help="lesson id to quiz on")
    parser.add_argument("--update", action="store_true", help="force-refresh cached content")
    parser.add_argument("--reset", action="store_true", help="clear local progress for the given course")
    parser.add_argument("--no-color", action="store_true", help="disable colour output")
    parser.add_argument("--continue", dest="resume", action="store_true",
                        help="carry on: resume an unfinished lesson, or start the next unlocked one")
    parser.add_argument("--restart", action="store_true", help="start the lesson from the first question")
    args = parser.parse_args()

    if args.no_color:
        c = Colors(no_color_flag=True)

    if args.course and args.course not in COURSES:
        print(f"{c.red}Unknown course '{args.course}'.{c.reset} Choices: {', '.join(COURSES)}")
        sys.exit(1)

    if args.update:
        courses = [args.course] if args.course else list(COURSES)
        for course in courses:
            fetch_course(course, force=True)
            print(f"Refreshed {course}.")
        return

    if args.reset:
        if not args.course:
            print(f"{c.red}--reset needs a course, e.g. codequiz python --reset{c.reset}")
            sys.exit(1)
        cmd_reset(args.course)
        return

    if not args.course:
        list_courses()
        return

    if args.resume and not args.lesson:
        cmd_continue(args.course, args.restart)
        return

    if not args.lesson:
        list_lessons(args.course)
        return

    cmd_lesson(args.course, args.lesson, args.restart)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
