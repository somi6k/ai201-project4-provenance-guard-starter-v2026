# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. False Positives

Of 10 pieces of human writing (at least 4 written plainly: short sentences, common words), at most 1 is labelled high-confidence AI, in each of three trials.


**Why this target:** Falsely accusing a human writer of being AI carries a huge penalty for the website, thus no more than 10% false accusations are tolerated.



---

## 2. Score spread

The average combined score of 5 clearly-AI pieces is at least 0.40 higher than the average of 5 clearly-human pieces, in each of three trials.



**Why this target:** If the gap is small, the thresholds have nothing to separate, and every label becomes a coin flip.



---

## 3. Label coverage

Each of the three labels is produced by at least one named test input (listed in the README), in each of three trials.



**Why this target:** The scoring rules and logic account for all potential scenarios so submissions should fit into one of the three labels.



---

## 4. The appeal path

Of 10 appeals with a valid content_id, 10 return a confirmation, add an appeal entry to log and move the item's status to under_review. Of 3 appeals with a made-up content_id, 3 return an error and add nothing to the log.



**Why this target:** Falsely accusing a human of AI creates a bad experience for the user, thus every appeal with valid content_id shall be logged and given under_review status. Appeals with erroneous content_ids return an error.



---

## 5. Bad input

Each of these 7 inputs to `POST /submit` returns a 400 with a JSON `error` field and a plain-English `message`, and none returns a 500, in each of three trials:

1. `text` missing from the body
2. `text` is an empty string
3. `text` is whitespace only
4. `text` is not a string (e.g. `123`)
5. the body is not valid JSON
6. `text` is over 10,000 characters
7. `text` is too short to score (e.g. `"hi"`)

**Why this target:** Bad input is the cheapest attack there is and one of the most common real failures. A crash (500) tells the writer nothing and hides the cause, and the "too short" case is easy to miss: `detector.perplexity` raises an error on fewer than 3 tokens, so without a check a one-word submission would crash the route. I chose 10,000 characters because that's well above a typical post, while the detector only reads the first 400 tokens (`DETECTOR_MAX_TOKENS` in `config.py`) anyway, so longer text costs processing time without adding information. Every case must pass every time, because a single 500 means the route has an input it doesn't handle.



---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
