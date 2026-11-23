#!/usr/bin/env python3
"""One Line, Zero Use (u-daring-gecko-25-one-line-zero-use-the-useless-01ca1c68).

Writes one line (1-200 chars) to /output/entry.txt: a single entertaining
line about a useless superpower, judged pairwise by the house judge
(z-ai/glm-5.3-flash) against its published brief. The brief weighs, most
important first:

  1. one line of text on the theme -- a superpower with zero use --
     inside 200 chars;
  2. stops the scroll in its first few words;
  3. genuinely entertaining -- funny or surprising or delightful, rather
     than merely clever or trying hard;
  4. lands as one line -- the whole idea in a single sentence, with a
     turn or a punch at the end;
  5. feels fresh -- an idea or twist a reader has not met a hundred
     times before.

"A line that has to be explained has already lost." So the program
keeps a shortlist of candidate lines, scores each against those same
yardsticks with a deterministic proxy scorer, and writes the strongest
one. The choice is fully deterministic: the same shortlist always
yields the same line. No network, no clock, no randomness.
"""

import os
import re
import sys

# Candidate lines, each one sentence and under the 240-char gate.
# All original, written for this entry.
CANDIDATES = [
    # M: the microwave beeps on schedule, and it saves nothing.
    "My superpower is knowing exactly when the microwave will beep, "
    "and I have never used it to save a single second.",
    # P: I can summon any pen -- only the dead one.
    "I can summon any pen in the house, but only the one that ran "
    "out of ink in 2019.",
    # E: the meeting-email detector, always too late.
    "My superpower is detecting when a meeting could have been an "
    "email, but only after the meeting has ended.",
    # H: the plants talk back, and they want less water.
    "I can talk to houseplants, and every single one of them has "
    "asked me to stop watering them so much.",
    # F: the squeaky floorboard, found at 3 a.m. by bare foot.
    "My superpower is finding the one squeaky floorboard in any "
    "house, usually at 3 a.m., usually with my bare foot.",
    # T: the Tupperware lid that fits nothing.
    "I can instantly tell which Tupperware lid fits nothing, and the "
    "drawer agrees with me every time.",
    # W: the password returns the moment it is reset.
    "My superpower is remembering every password I have ever "
    "forgotten, the moment I reset it.",
    # V: the Wi-Fi sense, one second too late.
    "I can sense when the Wi-Fi is about to drop, exactly one second "
    "after the video freezes.",
    # D: flawless parallel parking, but only in dreams.
    "My superpower is parallel parking flawlessly in my dreams, "
    "every single time.",
    # Q: the mosquito sense, only while asleep.
    "I can hear a mosquito in the next room, but only when I am "
    "already asleep.",
    # S: the suitcase weight, known after the charge.
    "My superpower is knowing the exact weight of a suitcase, but "
    "only after the airline charges me for it.",
    # R: every conversation becomes the weather.
    "I can turn any conversation into a discussion about the weather, "
    "and I have never once been stopped.",
    # Y: the typo, spotted after send.
    "My superpower is spotting a typo in a message, but only after I "
    "have already pressed send.",
    # A: perfect rain prediction, by standing in it.
    "I can predict rain with perfect accuracy, but only by standing "
    "in it.",
    # J: every jar opens except the one I need.
    "My superpower is opening any jar except the one I actually need "
    "open.",
    # U: the queue moves faster the moment I leave it.
    "I can make any queue move faster, but only the moment I leave "
    "it.",
    # L: every lyric except the one playing now.
    "My superpower is knowing the lyrics to every song, except the "
    "one playing right now.",
    # C: the cling film end, found too late and torn with teeth.
    "I can find the end of the cling film, but only after I have "
    "given up and torn it with my teeth.",
    # V: the ice cream van, heard three streets away, cashless.
    "I can hear the ice cream van from three streets away, but only "
    "when I have no cash on me.",
    # S: the fitted sheet, folded perfectly in the wrong hotel.
    "My superpower is folding a fitted sheet perfectly, but only in "
    "a hotel room that is not mine.",
    # CTRL: deliberately weak control -- abstract praise, no image,
    # no turn, no punch. The scorer must rank this last.
    "I have an amazing superpower that makes every day wonderful and "
    "full of incredible opportunities to smile.",
]

# Concrete image words: things a reader can see, hear or touch. An
# early one means the line stops the scroll (criterion 2).
IMAGE_WORDS = (
    "microwave", "pen", "meeting", "houseplant", "floorboard",
    "tupperware", "password", "wi-fi", "mosquito", "suitcase",
    "jar", "queue", "lyrics", "rain", "weather", "email", "drawer",
    "dreams", "video", "ink", "cling", "film", "ice cream", "van",
    "sheet", "teeth", "cash",
)

# Subjects the field has met a hundred times: a line built on one
# starts behind on freshness (criterion 5).
TIRED_SUBJECTS = (
    "could have been an email", "predict rain", "talk to plants",
    "talk to houseplants", "parallel parking",
)

# Subjects a reader has rarely met in a one-liner: freshness
# (criterion 5).
FRESH_SUBJECTS = (
    "tupperware", "floorboard", "mosquito", "suitcase", "jar",
    "queue", "password", "pen", "dreams", "microwave", "typo",
    "cling film", "ice cream van", "fitted sheet",
)

# Abstract praise: the brief says "merely clever or trying hard"
# loses to genuinely entertaining; abstract praise is neither.
ABSTRACT_PRAISE = (
    "beautiful", "amazing", "wonderful", "incredible", "magical",
    "perfect", "every day brings", "new opportunities",
)

# Flat clichés that cost a line its voice and its freshness.
CLICHES = (
    "every day brings", "smile and be happy", "live laugh love",
    "my cat", "my plants",
)

# Formats the field has met a hundred times (criterion 5): the
# meeting-email detector and the rain-by-standing-in-it joke are
# known tropes.
TIRED_FORMATS = (
    "could have been an email",
    "by standing in it",
)

# Turn markers: the sentence pivots, then lands its punch
# (criterion 4). Compared lowercased.
TURN_MARKERS = (
    "but only", "and i", "so i", "except", "never", "already",
    "after", "still", "the moment",
)

# Two unrelated domains colliding in one line: the incongruity that
# makes a line funny instead of merely clever (criterion 3).
INCONGRUITY_PAIRS = (
    ("microwave", "save"),
    ("pen", "2019"),
    ("meeting", "ended"),
    ("houseplants", "watering"),
    ("floorboard", "3 a.m."),
    ("tupperware", "fits nothing"),
    ("password", "reset"),
    ("wi-fi", "freezes"),
    ("dreams", "parking"),
    ("mosquito", "asleep"),
    ("suitcase", "charges"),
    ("weather", "stopped"),
    ("typo", "send"),
    ("rain", "standing"),
    ("jar", "except"),
    ("queue", "leave"),
    ("lyrics", "playing"),
    ("cling film", "teeth"),
    ("ice cream", "cash"),
    ("sheet", "hotel"),
)

# The punch lives in the final clause (criterion 4).
PUNCH_TAILS = (
    "a single second", "in 2019", "has ended", "so much",
    "bare foot", "every time", "reset it", "freezes",
    "every single time", "already asleep", "for it", "been stopped",
    "pressed send", "standing in it", "need open", "leave it",
    "right now", "with my teeth", "no cash", "not mine",
)

# Reader rubric, /25 (5 per brief criterion), scored by the author
# against the published brief before the v1 proxy ran. The proxy
# narrows the field; the rubric breaks its ties, because only a reader
# can tell a warm surprise from a merely clever one. Order matches
# CANDIDATES.
RUBRIC = [
    17,  # 0 microwave: clear power, soft punch, "save a second" mild
    21,  # 1 pen: specific, "in 2019" lands, short and vivid
    16,  # 2 meeting-email: relatable but a known trope
    19,  # 3 houseplants: talk-back twist, "so much" soft landing
    22,  # 4 floorboard: vivid, "bare foot" punch, very fresh
    22,  # 5 tupperware: "fits nothing", drawer agrees, fresh
    23,  # 6 password: universal, "the moment I reset it" is the joke
    17,  # 7 wi-fi: one second too late, mild
    21,  # 8 dreams: flawless parking only in dreams, warm
    21,  # 9 mosquito: "only when already asleep", tight
    21,  # 10 suitcase: "after the airline charges me", relatable
    17,  # 11 weather: mild, no concrete punch
    23,  # 12 typo: universal, "after I pressed send" lands hard
    19,  # 13 rain: classic useless-power joke, known shape
    21,  # 14 jar: "except the one I need", tight and short
    24,  # 15 queue: leaves and it moves, the purest zero-use power
    20,  # 16 lyrics: good, "except the one playing" slightly soft
    22,  # 17 cling film: "torn it with my teeth", vivid, fresh
    21,  # 18 ice cream van: heard, cashless, warm
    22,  # 19 fitted sheet: perfect fold, wrong hotel, fresh
    7,   # 20 control: abstract praise, no image, no turn
]

OUTPUT_PATH = "/output/entry.txt"
MAX_CHARS = 200


def score_line(line):
    """Score one candidate the way the judge's brief weighs a line.

    Returns points; higher is better. Criterion order follows the
    brief: on-theme first, then scroll-stop, entertaining, one
    sentence with a punch, freshness.
    """
    low = line.lower()
    points = 0.0

    # 1. On theme: one line about a useless superpower, one sentence,
    # no throat clearing, a length that can hold an idea and a punch.
    # "3 a.m." is one sentence, not three: strip a.m./p.m. before
    # counting sentence-ending periods (v2).
    _sent = low.replace("a.m.", "am").replace("p.m.", "pm")
    if _sent.count(".") == 1 and "!" not in line and "?" not in line:
        points += 2.0  # a single sentence
    if not low.startswith(("so ", "well ", "hey ", "listen ",
                           "imagine ", "picture this ")):
        points += 1.0  # no throat clearing
    size = len(line)
    if 80 <= size <= 140:
        points += 1.0  # long enough for a turn, short enough to land
    elif size < 60 or size > 200:
        points -= 1.0

    # 2. Stops the scroll: a concrete image inside the first 30 chars
    # pays full marks; one landing in the first six words still hooks
    # and pays half (v2: "password" and "typo" land sixth and were
    # scored as if the line opened on nothing).
    head = low[:30]
    first_words = low.split(" ")[:6]
    if any(word in head for word in IMAGE_WORDS):
        points += 3.0
    elif any(word in " ".join(first_words) for word in IMAGE_WORDS):
        points += 1.0
    # Opening on a concrete subject (My/I) hooks faster than an
    # abstraction or a setup clause.
    if low.startswith(("the ", "my ", "our ", "i ")):
        points += 1.0
    # A vivid opening verb (summon, talk, finding, tell, remembering,
    # sense, hear, knowing, spotting, predict, opening, make, turn)
    # beats a flat one (is, was, has). The first six words are the
    # scroll stop.
    if any(w in first_words for w in ("summon", "talk", "finding",
                                      "tell", "remembering", "sense",
                                      "hear", "knowing", "spotting",
                                      "predict", "opening", "make",
                                      "turn", "detecting")):
        points += 1.0

    # 3. Genuinely entertaining: incongruity, then a turn, and no
    # abstract praise doing the work instead of the joke.
    for subj, verb in INCONGRUITY_PAIRS:
        if subj in low and verb in low:
            points += 2.0
            break
    turns = sum(1 for word in TURN_MARKERS if word in low)
    points += min(turns, 2) * 1.5
    for word in ABSTRACT_PRAISE:
        if word in low:
            points -= 2.0
    for cliche in CLICHES:
        if cliche in low:
            points -= 3.0

    # 4. Lands as one line: two clauses joined by a comma or dash,
    # and the punch sits in the final clause.
    if "," in line or "\u2014" in line or ":" in line:
        points += 1.0
    tail = low.rsplit(",", 1)[-1].rsplit("\u2014", 1)[-1]
    if any(word in tail for word in PUNCH_TAILS):
        points += 2.0
    # A punch that introduces a new idea, not one that merely echoes
    # the setup: the final clause holds a content word the opening
    # never used.
    _STOP = {"including", "and", "the", "with", "that", "this",
             "from", "have", "has", "never", "just", "like", "every",
             "still", "when", "where", "what", "about", "after",
             "before", "into", "over", "under", "without", "would",
             "could", "should", "there", "here", "then", "than",
             "they", "them", "their", "your", "yours", "mine",
             "ours", "almost", "really", "very", "much", "more",
             "only", "but", "one", "single", "already", "once"}
    head_words = set(re.findall(r"[a-z']+", low.split(",")[0]))
    tail_words = set(re.findall(r"[a-z']+", tail))
    if any(len(w) > 3 and w not in head_words and w not in _STOP
           for w in tail_words):
        points += 1.5

    # 5. Fresh: an unusual subject pays; a tired one costs.
    if any(word in low for word in FRESH_SUBJECTS):
        points += 2.0
    for word in TIRED_SUBJECTS:
        if word in low:
            points -= 3.0
    for fmt in TIRED_FORMATS:
        if fmt in low:
            points -= 2.0
    # A format the field has met a hundred times costs freshness.
    if low.startswith("i asked my ") or "filed a complaint" in low:
        points -= 2.0
    return points


def pick_line(candidates):
    """Return the highest-scoring candidate.

    Primary key is the proxy score; ties go to the higher reader
    rubric, then to the earliest candidate. A proxy tie means the
    scorer cannot tell the lines apart, and the rubric is the reader
    the brief is written for.
    """
    best = None
    best_key = None
    for index, line in enumerate(candidates):
        key = (score_line(line), RUBRIC[index], -index)
        if best_key is None or key > best_key:
            best, best_key = line, key
    return best, best_key[0], best_key[1]


def gate_ok(line):
    """The sealed gate: UTF-8 text, 1-200 chars, not only whitespace."""
    if not line or not line.strip():
        return False
    if len(line) > MAX_CHARS:
        return False
    if "\n" in line or "\r" in line:
        return False
    try:
        line.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def main():
    line, points, rubric = pick_line(CANDIDATES)
    if not gate_ok(line):
        print("picked line fails the gate", file=sys.stderr)
        return 1
    target = os.environ.get("ENTRY_OUTPUT", OUTPUT_PATH)
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(line)
    # The grader collects outputs as another user: leave the file
    # readable by everyone.
    os.chmod(target, 0o644)
    print(f"wrote {len(line)} chars (proxy {points}, rubric "
          f"{rubric}/25) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
