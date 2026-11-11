"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

# Coefficient of variation (stdev / mean of sentence lengths) that maps to 100.
# Generated prose tends to sit around 0.2–0.4; human prose often 0.5 and up.
# Anything at or above this cap is "as varied as it gets" for scoring purposes.
SPREAD_CV_CAP = 0.8


def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies.

    Returns:
        A float from 0 to 1. **Higher means more human** (lumpier sentence
        lengths); lower means more AI-like (sentences marching in step).
        Same 0–1 scale as style_signal, but the opposite direction, so
        style_signal flips it with `1 - spread`.

    How: the coefficient of variation of sentence lengths in words —
    stdev / mean, so a long text and a short one are comparable — scaled
    linearly so CV 0 → 0 and CV ≥ SPREAD_CV_CAP → 1.

    Edge case: fewer than two sentences has no spread to measure, so it
    returns 0.5 — "unsure", pulling neither way — instead of raising.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]   # drop "sentences" with no words, e.g. "!!!"

    if len(lengths) < 2:
        return 0.5

    cv = statistics.stdev(lengths) / statistics.mean(lengths)
    return round(min(cv / SPREAD_CV_CAP, 1.0), 4)


# Window size, in words, for the moving-average type-token ratio.
TTR_WINDOW = 50


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words, averaged over a sliding window.

    Returns:
        A float from 0 to 1. **Higher means more human** (more varied
        vocabulary); lower means more AI-like (words repeat more).
        Opposite direction to style_signal, so style_signal flips it with
        `1 - ttr`.

    How: plain unique/total falls as text gets longer, because common words
    repeat — so a long text would look "more AI" just for being long. Instead
    this is the moving-average TTR (MATTR): the unique/total ratio of every
    run of TTR_WINDOW consecutive words, averaged. Every window is the same
    length, so texts of different lengths are comparable.

    Edge case: fewer than TTR_WINDOW words (including none) → 0.5 ("unsure",
    pulls neither way). Short texts have few chances to repeat a word, so
    plain unique/total reads almost any short text as human. Same rule as
    sentence_length_spread: not enough to measure → neutral.
    """
    tokens = words(text)
    if len(tokens) < TTR_WINDOW:
        return 0.5

    ratios = [
        len(set(tokens[i:i + TTR_WINDOW])) / TTR_WINDOW
        for i in range(len(tokens) - TTR_WINDOW + 1)
    ]
    return round(statistics.mean(ratios), 4)


# "Expressive" punctuation, grouped into kinds. Full stops, commas and hyphens
# are left out on purpose: every writer uses them, so they say little.
PUNCT_KINDS = {
    ";": "semicolon",
    ":": "colon",
    "—": "dash", "–": "dash",
    "(": "paren",
    "!": "exclamation",
    "?": "question",
    '"': "quote", "“": "quote", "”": "quote",
    "'": "apostrophe", "’": "apostrophe",
    "…": "ellipsis",
}

# One expressive mark per this many words scores full marks on density.
PUNCT_PER_WORD_CAP = 0.10
# Using this many different kinds scores full marks on variety.
PUNCT_VARIETY_CAP = 4


def punctuation_density(text: str) -> float:
    """
    How much expressive punctuation, and how varied.

    Returns:
        A float from 0 to 1. **Higher means more human** (more, and more
        varied, punctuation); lower means more AI-like (plain full stops and
        commas). Opposite direction to style_signal, so style_signal flips it
        with `1 - density`.

    How: only "expressive" marks count (PUNCT_KINDS) — semicolons, colons,
    dashes, brackets, ! and ?, quotes, apostrophes, ellipses. Full stops,
    commas and hyphens are ignored because everyone uses them. Two parts,
    averaged equally:
      - density: expressive marks per word, scaled so PUNCT_PER_WORD_CAP → 1
      - variety: how many different kinds appear, scaled so
        PUNCT_VARIETY_CAP kinds → 1

    Edge case: no words at all → 0.5 ("unsure", pulls neither way).

    Blind spot: modern chatbots are fond of em dashes and colons, so this can
    read some AI text as human. Adding punctuation is also the cheapest way
    to move this score on purpose.
    """
    n_words = len(words(text))
    if n_words == 0:
        return 0.5

    # Normalise multi-character forms to their single-character equivalents.
    normalised = text.replace("...", "…").replace("--", "—")

    found = [PUNCT_KINDS[ch] for ch in normalised if ch in PUNCT_KINDS]

    density = min((len(found) / n_words) / PUNCT_PER_WORD_CAP, 1.0)
    variety = min(len(set(found)) / PUNCT_VARIETY_CAP, 1.0)
    return round((density + variety) / 2, 4)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.**

    Same direction as `detector.model_signal`, so `scoring.combine_signals`
    can treat the two signals the same way.

    The rule — an equal average, as in the README's combining rule:

      1. Direction: all three measures return 0–1 with higher = more human,
         so each is flipped (`1 - measure`) to make higher = more AI.
      2. Scale: all three are already on 0–1, so no rescaling is needed
         before averaging.
      3. Weights: equal, 1/3 each. No measure is trusted over another yet.

    No disagreement cap here — that lives in `scoring.combine_signals`, so it
    acts once, between the two signals.
    """
    measures = [
        sentence_length_spread(text),
        type_token_ratio(text),
        punctuation_density(text),
    ]
    flipped = [1.0 - m for m in measures]
    return round(sum(flipped) / len(flipped), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
    print("\nAll zeros? These are stubs — Milestone 4 is where you build them.")
