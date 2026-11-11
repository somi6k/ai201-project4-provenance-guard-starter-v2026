# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. **Submit.** A writer sends `{"text": ..., "creator_id": ...}` to `POST /submit` (`app.py::submit`). Before any scoring, the route rejects malformed input (missing, empty, non-string, or oversized `text`) with a clear error instead of crashing.
2. **Signal one: the model signal.** The text goes to `detector.py::model_signal`, which calls `detector.py::perplexity` to measure how predictable the text is to gpt2. Then it squashes that perplexity onto a 0–1 scale. Low perplexity (very predictable) → high score → more likely AI.
3. **Signal two: the style signal.** The text goes to `stylometry.py::style_signal`, which runs three shape measures: `sentence_length_spread` (do sentence lengths vary?), `type_token_ratio` (how much vocabulary repeats?) and `punctuation_density` (how much punctuation, and of what kind?). It flips each measure where needed so that higher means more AI-like, puts them on a common scale, and combines them into one 0–1 score.
4. **Combine.** Both scores go to `scoring.py::combine_signals`, which merges them into a single 0–1 score (higher = more likely AI).
5. **Label.** The combined score goes to `scoring.py::score_to_label`, which compares it against the thresholds in `config.py`. It returns a short guess (`ai` / `human` / `unsure`) and the plain-language sentence the writer actually sees.
6. **Log.** The route makes a `content_id` and records the decision with `audit.log_decision(...)`: both signal scores, the combined score, the guess and the label. That entry is what `/appeal` later looks up.
7. **Respond.** The writer gets back `content_id`, `guess`, `label`, `confidence`, `model_score` and `style_score`. They can use the `content_id` to contest the result through `POST /appeal`.



---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** The perplexity signal measures how predictable the text is, that is, how easy it is for the model to predict the next likely word.

**Why that might differ between human and AI writing:** AI produces predictable text, wheras human writing tends to meander more, with odd word choice and abrupt turns, producing a higher perplexity score.

**What it can't see:** A new writer, a younger writer, a second language writer or someone writing plainly on purpose may be scored lower on the perlexity signal, thus could be falsely flagged as AI. The signal rewards common words in short, simple sentences, which is typical of an llm writes. The reverse also happens: dense, ornate prose full of rare words can score as human.

### Signal two — the style signal

**What it measures:** The style signal measures sentence length variety, word choice repetitiveness and punctuation density. 

**Why that might differ between human and AI writing:** AI writing tends to use similar mid-length sentences with a relatively small vocabulary as the models write by choosing the most likely next word. Human writing has more variety, with varying sentence length, vocabulary usage and punctuation distribution.

**What it can't see:** Because this signal does not read the text, it can be easily fooled. Deliberate punctuation breaking up sentences, pasted quotes and typos all move the signal without actually changing the text's substance.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** Average the two scores equally. 

**The numbers:** Weights	model 0.5, style 0.5
                 Disagreement gap	> 0.4
                 Cap when split = 0.64 (just under AI_THRESHOLD = 0.65)

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**

If they disagree by more than 0.4, the combined score is capped just below the AI threshold, so a split can produce "unsure" or "human" but never "AI." Accusing a writer requires both signals to agree.

---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | We think this was written by a person. Nothing in our checks suggested otherwise. |
| unsure | 0.35 – 0.65 | We can't tell whether this was written by a person or with AI. This is not an accusation: a lot of genuine human writing lands here, especially writing that is plain and clear. If you'd like a person to take a look, you can ask for a review. |
| high-confidence AI | 0.65 – 1.00 | This writing has strong signs of being generated by AI. Two separate checks both pointed that way. These checks can be wrong. If you wrote this yourself, you can appeal and a person will review it. |

Ranges are from `scoring.label_ranges()`. At the edges, exactly 0.35 is labelled human and exactly 0.65 is labelled AI (`score_to_label` in `scoring.py`). Because of the combining rule's split cap, a score where the two signals disagree by more than 0.4 can reach at most 0.64, so it is never labelled AI.

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->

The person reading "unsure" may well have written every word themselves, so the label has to admit uncertainty without sounding like suspicion. It says plainly that it is not an accusation. It also explains *why* real writing ends up here: the model signal reads plain, clear writing as predictable, which is that signal's blind spot. That tells the writer the result says something about our checks, not about them. It ends with something they can do, asking for a person to review it, so the label doesn't leave them with a doubt and no way to answer it. It avoids "threshold", "model" and "confidence", because those words mean nothing to someone who just wants to know whether they're being accused.



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "I started volunteering at the food bank in March because my neighbor asked me to. The first day I mostly stacked cans. By the second week I was helping at the front desk, checking people in and handing out bags. Some people come every week and we know their names now. It is not hard work, but it is steady, and I like that I can see what it does.", "creator_id": "somi"}'
```

```json
{
  "combined_score": 0.5978,
  "confidence": 0.5978,
  "content_id": "47efb8e5-2c13-446d-b199-cacaba29e652",
  "guess": "unsure",
  "label": "We can't tell whether this was written by a person or with AI. This is not an accusation: a lot of genuine human writing lands here, especially writing that is plain and clear. If you'd like a person to take a look, you can ask for a review.",
  "model_score": 0.6178,
  "style_score": 0.5779
}
```

This is plain human writing, the kind signal one's blind spot is about. Both signals lean slightly AI (0.62 and 0.58), and it lands in "unsure" rather than being accused.

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "47efb8e5-2c13-446d-b199-cacaba29e652", "reasoning": "I wrote this myself about my own volunteering. I write in short, plain sentences on purpose."}'
```

```json
{
  "content_id": "47efb8e5-2c13-446d-b199-cacaba29e652",
  "message": "Thanks. Your appeal has been received, and a person will review this result. The original decision is on hold while that happens.",
  "status": "under_review"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json
{
  "count": 3,
  "entries": [
    {
      "content_id": "e1c4f78f-4a94-4d4c-bfed-77a0c0776e41",
      "creator_id": "somi",
      "event": "appeal",
      "reasoning": "I wrote this myself for a class.",
      "status": "under_review",
      "timestamp": "2026-11-11T07:12:03+00:00"
    },
    {
      "combined_score": 0.5978,
      "content_id": "47efb8e5-2c13-446d-b199-cacaba29e652",
      "creator_id": "somi",
      "guess": "unsure",
      "label": "We can't tell whether this was written by a person or with AI. This is not an accusation: a lot of genuine human writing lands here, especially writing that is plain and clear. If you'd like a person to take a look, you can ask for a review.",
      "model_score": 0.6178,
      "status": "decided",
      "style_score": 0.5779,
      "timestamp": "2026-11-11T07:16:50+00:00"
    },
    {
      "content_id": "47efb8e5-2c13-446d-b199-cacaba29e652",
      "creator_id": "somi",
      "event": "appeal",
      "reasoning": "I wrote this myself about my own volunteering. I write in short, plain sentences on purpose.",
      "status": "under_review",
      "timestamp": "2026-11-11T07:16:51+00:00"
    }
  ]
}
```

The first entry is an appeal from an earlier test. The last two are this run: the original decision stays in the log unchanged (`status: decided`), and the appeal is added after it (`status: under_review`).

---

## How I Used AI

**Moment 1**

- *What I asked for:* An implementation of `stylometry.py::sentence_length_spread` on a 0–100 scale, with 100 meaning more human, and 50 for a one-sentence submission.
- *What came back:* A version using the coefficient of variation of sentence lengths (stdev ÷ mean), scaled so a variation of 0.8 or more scores 100. It pointed out that this scale and direction didn't match `style_signal`, which runs 0–1 with higher = more AI.
- *What I changed:* I moved it to a 0–1 scale to match `style_signal`. I then tried flipping it so higher = more AI, and reverted that: the function is called "spread", so a high score meaning *low* spread would be misleading. I kept all three measures as "higher = more human" and flip them in one place, inside `style_signal`.

**Moment 2**

- *What I asked for:* An implementation of `type_token_ratio` on a 0–1 scale, higher = more human.
- *What came back:* A moving-window type-token ratio (average unique/total over every 50-word window) so long and short texts are comparable, with plain unique/total as a fallback for texts under 50 words. Testing `style_signal` showed a problem: a 30-word AI-like sample scored 0.90 on this measure (very human), because short texts have few chances to repeat words, and that dragged the style score down to 0.67. It offered two fixes: stretch the measure's range, or skip it on short texts.
- *What I changed:* I chose to skip it under 50 words and return 0.5 (neutral), the same "not enough to measure → unsure" rule I'd already used for one-sentence texts in `sentence_length_spread`. Stretching would have made the wrong answer louder. With the change, the style score for that sample rose from 0.67 to 0.80.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 5 per minute, 100 per day

**Why those numbers and not others:** A real writer would be unlikely to be making submissions at a rate faster than 1 per 12 seconds, let alone 100 per day. These rates allow even an aggressive rate of posts without allowing an automated script to flood the server.

<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** Each `creator_id` is counted separately (`app.py::rate_limit_key`). If a request doesn't include a usable `creator_id`, it counts against the caller's IP address instead. Counting per creator means people sharing one network, like a household or a classroom, don't use up each other's limit. The weakness is that `creator_id` is whatever the caller sends, so a script can rotate through made-up IDs and get a fresh limit for each one. Counting by IP address would fail the other way: one script sending from many addresses would look like many callers, and a whole household behind one address would look like one caller.

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```
$ python run_attacks.py --flood 15
15 submissions as 'flood_tester' against http://127.0.0.1:5000

  [ 1/15] 200
  [ 2/15] 200
  [ 3/15] 200
  [ 4/15] 200
  [ 5/15] 200
  [ 6/15] 429
  [ 7/15] 429
  [ 8/15] 429
  [ 9/15] 429
  [10/15] 429
  [11/15] 429
  [12/15] 429
  [13/15] 429
  [14/15] 429
  [15/15] 429

200 200 200 200 200 429 429 429 429 429 429 429 429 429 429
10 of 15 were rate limited.
```

The first five requests got through, and every request after that was rejected, which matches the 5-per-minute limit. Each rejection is also written to the audit log. Here is one from `GET /log`:

```json
{
  "creator_id": "flood_tester",
  "event": "rejected",
  "limit": "5 per 1 minute",
  "reason": "rate_limited",
  "status": "rejected",
  "timestamp": "2026-11-11T20:58:21+00:00"
}
```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
