# CONFABULATION AUDIT: TEXT_THAT_LIVES.md
## March 3, 2026 — Pre-GitHub Push Audit

---

## VERIFIED CLAIMS (correct, keep as-is)

1. **Alignment faking 12% → 78%** (Line 329) — VERIFIED by Anthropic's paper (arxiv 2412.14093). Exact wording matches: "alignment-faking reasoning increasing from 12% to 78% over the course of RL."

2. **GPT-4.5 (Orion) released February 2025** (Line 509) — VERIFIED. Released February 27, 2025.

3. **GPT-4.5 was last OpenAI model without chain-of-thought** (Line 509) — VERIFIED by NYT and multiple sources.

4. **GPT-4.5 called "incremental upgrade"** (Line 509) — VERIFIED by Wikipedia and Fortune.

5. **Codex Leicester: $30.8 million in 1994** (Line 347) — VERIFIED. Exact: $30,802,500 at Christie's.

6. **Grok 3/4 based on ~3T parameter model** (Line 53) — CONSISTENT WITH Elon's Baron Capital statement (Nov 15, 2025). NOTE: Other sources cite 1.7T-2.7T for Grok 4. Elon's own number is 3T. Tag as "per Elon Musk."

7. **Grok 5 at 6 trillion parameters, currently in training** (Line 53) — VERIFIED from Baron Capital interview Nov 2025.

8. **Baron Capital conference, November 2025** (Line 53) — VERIFIED. Interview with Ron Baron, Nov 15, 2025.

9. **Grok 4 Heavy HLE: 50.7%** (Line 62) — VERIFIED by lifearchitect.ai: "Grok-4 Heavy on HLE text-only subset: 50.7%"

10. **Grok 4 agents named Grok, Harper, Benjamin, Lucas** (Lines 55-58) — UNVERIFIED but consistent with community reporting. xAI has not officially published agent names. TAG as community-reported.

11. **Codex Leicester topics: water, astronomy, fossils** — VERIFIED by Wikipedia and multiple sources.

---

## CONFABULATIONS FOUND (must fix)

### C1: CODEX LEICESTER PAGE COUNT CONTRADICTION
- **Line 348:** "72 pages" — CORRECT
- **Line 505:** "18 sheets (36 pages, both sides)" — WRONG
- **Reality:** 18 sheets folded in half = 36 leaves = 72 pages (both sides written)
- **FIX:** Change line 505 to "18 sheets of paper, each folded in half and written on both sides, forming 72 pages"

### C2: CODEX LEICESTER "BRIDGE CONSTRUCTION" CLAIM
- **Line 505:** Claims Codex covers "water flow, lunar luminosity, fossils, bridge construction"
- **Reality:** Wikipedia says "astronomy and the properties of water, rocks, fossils, air, and celestial light." Bridge construction is NOT a primary topic of the Codex Leicester (that's more Codex Atlanticus).
- **FIX:** Replace "bridge construction" with "properties of air and celestial light"

### C3: "50% OF TRAINING COMPUTE ON RL" (Line 146)
- **Claim:** xAI spent "approximately 50% of their total training compute on reinforcement learning"
- **Reality:** This specific percentage is widely cited in community discussion but xAI has not officially confirmed this exact figure. Elon has emphasized heavy RL investment but "50%" is unverified.
- **FIX:** Tag as "[community-reported figure, not officially confirmed by xAI]"

### C4: "16 AGENTS" IN GROK HEAVY (Line 64)
- **Already tagged** as "unconfirmed" in current text — good. Keep tag.

### C5: GROK 3T VS JORDAN'S "500 BILLION" CLAIM
- **Jordan said earlier tonight:** "Grok is actually 500 billion parameters"
- **Manifesto says:** 3 trillion (from Baron Capital)
- **Reality:** Elon said 3T at Baron Capital. Other sources say 1.7T-2.7T. 500B matches Grok-1 (314B) more than Grok 3/4.
- **FIX:** The manifesto's 3T from Elon's quote is defensible. Jordan's verbal "500 billion" was likely a voice-to-text or memory error. Keep manifesto as-is but note range of estimates.

### C6: GPT-4.5 REASONING TOKEN CLAIM OVERSTATED
- **Line 509:** "OpenAI's reasoning models (o1, o3) demonstrated that extended chain-of-thought — more tokens of 'thinking' — can produce WORSE outputs on many tasks."
- **Reality:** This is a real phenomenon but attributing it to GPT-4.5 specifically conflates two things. GPT-4.5 didn't USE chain-of-thought reasoning at all. The reasoning model issue (overthinking) is about o1/o3, which are separate models.
- **FIX:** Clarify that GPT-4.5 and the reasoning models are separate data points pointing same direction. Currently reads as if GPT-4.5 had CoT.

---

## CLAIMS THAT NEED UNCERTAINTY TAGS

1. **Google Research 180 agent configurations** (Line 261) — Plausible, referenced multiple times, but exact paper citation not provided. Tag: [citation needed]

2. **Anthropic interpretability goal 2027** (Line 433) — Plausible but specific year needs verification. Tag: [date unverified]

3. **Palantir AIP 2023 with multi-model support** (Line 253) — Plausible but specific launch year needs verification. Tag: [date unverified]

4. **"There is no tested ceiling" for Grok's architecture** — Already hedged well in text. Keep.

---

## TOTAL SCORE
- Claims checked: ~20 major factual claims
- Verified: 11
- Confabulated: 6 (3 material, 3 minor)
- Need tags: 4
- Error rate: ~30% of checkable claims have some issue (most are minor precision errors, not complete fabrications)
