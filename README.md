<div align="center">

# CodeQuizCLI

**The quiz side of Code's lessons, in your terminal - multiple-choice, predict-the-output, fill-in-the-blank and line-reordering questions, fetched once and then answered offline, with no dependencies beyond Python itself.**

[![Python](https://img.shields.io/badge/python-3.8+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen?style=flat-square)](https://docs.python.org/3/library/)
[![Code](https://img.shields.io/badge/code-drew--gnr.xyz-ff4d2e?style=flat-square)](https://drew-gnr.xyz/code/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Overview

**Run it with one command: `codequiz <course>`.** Code already exists as a
website with lessons across five languages; this puts the quiz-style
questions from those lessons behind a terminal command, with the same
lesson-locking progression as the website, so you can drill a language
without a browser open.

It reads the exact same generated lesson files the website uses
(`content/<course>.json`), so there is no second copy of the content to
keep in step. Each course is fetched once, cached locally, and everything
after that works offline.

One file, standard library only, no build step, no account, no login -
this only ever reads public lesson content, never writes anything back to
the website.

## Requirements

- Python 3.8+
- Nothing else. No pip install, no virtualenv, no `requirements.txt`.

A network connection is needed the first time each course is used, to
fetch its lessons.

## Setup

```bash
chmod +x codequiz.py
cp codequiz.py ~/.local/bin/codequiz
```

Anywhere on `PATH` works. To run it without installing:

```bash
./codequiz.py python
```

## Usage

```bash
codequiz                       # list courses
codequiz python                # list a course's lessons and lock status
codequiz python py-print       # take the quiz for one lesson
codequiz --update              # refresh cached content for every course
codequiz python --continue     # resume where you left off, or start the next unlocked lesson
codequiz python loops --restart  # retake a lesson from question 1
codequiz python --reset        # clear local progress for one course
codequiz python py-print --no-color   # plain output, no ANSI colour
```

Lessons unlock in order, same as the website - the first lesson in a
course is always open, and each one after that unlocks once the previous
one is complete. Already-completed lessons stay open and can be retaken
any time; retaking one does not lock it again or affect anything else.

Only question-style exercises are included: multiple-choice, predict the
output, fill in the blank, and reorder the lines. Teaching cards and
write-your-own-code exercises are left out, since those need a real
language runtime rather than a terminal quiz. The Terminal course is left
out entirely for the same reason - it is simulated shell commands, not
questions.

A wrong answer shows the correct one and the explanation, then comes back
around once more at the end of the lesson so you see it again before
moving on. Reaching the end of a lesson's questions completes it and
unlocks the next one, whatever the accuracy was.

Exit codes: `0` the quiz ran (or the listing printed), `1` a bad course,
an unknown lesson id, or a locked lesson - so it composes properly in
scripts.

## Configuration

| Variable | Description |
|---|---|
| `CODEQUIZ_CONTENT_BASE` | Content source, a URL or a `file://` path. Default `https://drew-gnr.xyz/code/content`. |
| `NO_COLOR` | Set to anything to disable colour output. |
| `XDG_CACHE_HOME` | Cache location. Defaults to `~/.cache`, giving `~/.cache/codequiz/`. |

Point it at a local checkout while working on Code's lesson content itself:

```bash
export CODEQUIZ_CONTENT_BASE=file:///path/to/code-learner/content
```

Each course's cache is refetched when it is more than a week old, or on
`--update`. If the network is unreachable but a cache exists, it warns and
uses the cache rather than failing.

Progress is stored separately from the content cache, at
`~/.cache/codequiz/progress.json` (or under `$XDG_CACHE_HOME` if set) -
which lessons are complete per course, and a small history of attempts and
scores per lesson.

## Tech

- Single file, standard library only - `argparse`, `json`, `random`, `re`,
  `urllib`.
- Reads `content/<course>.json` exactly as the website's own
  `content.js` does, so questions can never drift from what is actually on
  the site.
- A custom User-Agent is sent on requests, since Cloudflare returns a 403
  to Python's default `urllib` one.
- Colour is suppressed automatically when stdout is not a TTY, or when
  `NO_COLOR` is set, or with `--no-color`.

## License

MIT

---
