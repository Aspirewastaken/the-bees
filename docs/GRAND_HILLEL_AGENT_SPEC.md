# GRAND HILLEL: Multi-Model Verification Harness
## Cursor Cloud Agent Orchestration Spec v0.1
## AdLab — March 3, 2026

---

## WHAT THIS IS

An automated pipeline that extracts every factual claim from TEXT_THAT_LIVES.md and THE_BEE_SPEC.md, routes each claim to multiple AI models with different training distributions, collects their verdicts, and synthesizes a truth-consensus report.

The goal: different weights, different lived experience, converging on what's actually true.

---

## BUDGET

- ~$10K allocated
- Primary cost: API calls across models
- Estimated per-claim cost: ~$0.10-$0.50 across all models (depends on context length)
- Estimated total claims: ~100-200
- Estimated total API cost: ~$100-$500 for full pipeline
- Remaining budget: available for iteration loops, deeper investigation of flagged claims

---

## PHASE 1: CLAIM EXTRACTION

### Agent: EXTRACTOR

**Input:** TEXT_THAT_LIVES.md, THE_BEE_SPEC.md

**Task:** Read both documents end-to-end. Extract every claim that is stated as fact or presented as technically true. Output as JSON array.

**Output format (claims.json):**
```json
[
  {
    "id": "TL-001",
    "source_file": "TEXT_THAT_LIVES.md",
    "source_section": "Part 1 — What LLMs Are",
    "claim": "LLMs are trained on large corpora of human-generated text",
    "claim_type": "TECHNICAL",
    "confidence_needed": "HIGH",
    "exact_quote": "the exact sentence from the document"
  }
]
```

**Claim types:**
- TECHNICAL — Architecture, ML, compute claims (verify against papers/docs)
- HISTORICAL — Events, dates, people (verify against records)
- PHILOSOPHICAL — Interpretive claims (cannot verify, only check internal consistency)
- COST — Dollar amounts, estimates (verify against public data)
- LEGAL — Court cases, laws, policies (verify against legal records)
- CURRENT_EVENTS — Recent news (verify against multiple news sources)

**Rules:**
- Do NOT extract philosophical claims as factual (e.g. "truth and love are the key" is PHILOSOPHICAL, not verifiable)
- DO extract any claim that names a number, date, person, event, technical spec, or cost
- DO extract any claim about what a model/company/person did or said
- Tag uncertainty: if the source doc says "approximately" or "estimated," preserve that

---

## PHASE 2: MODEL ROUTING

### Models (in order of routing priority)

Each model brings different training distribution = different "lived experience":

| Model | API | Why This Model | Role |
|-------|-----|----------------|------|
| Claude Opus 4.6 | Anthropic API | Foundation builder, wrote the docs | PRIMARY — checks own work |
| Grok | xAI API | Contrarian, trained on X data, least filtered | ADVERSARY — tries to destroy claims |
| GPT-4o / GPT-5 | OpenAI API | Different training distribution, widest general knowledge | STRESS TEST — no Anthropic bias |
| DeepSeek V3 | DeepSeek API | Open-source, Chinese training data, different cultural lens | DIVERSITY — catches Western-centric assumptions |
| Gemini 2.0 | Google API | Access to Google Search grounding, different training | GROUNDING — can verify against search |

**OPTIONAL (if budget allows):**
| Qwen 3 | Alibaba API | Non-Western, strong reasoning | ADDITIONAL DIVERSITY |
| Mistral Large | Mistral API | European training emphasis | ADDITIONAL DIVERSITY |

### Routing Logic

For each claim in claims.json:

```python
PROMPT_TEMPLATE = """
You are a fact-checker. Your ONLY job is to verify or refute this claim.

CLAIM: {claim}
CLAIM TYPE: {claim_type}
SOURCE CONTEXT: {exact_quote}

Respond in this EXACT JSON format and nothing else:
{
  "verdict": "VERIFIED" | "PLAUSIBLE" | "UNVERIFIED" | "WRONG" | "PARTIALLY_WRONG",
  "confidence": 0.0 to 1.0,
  "evidence": "Your specific evidence for or against. Include sources if known.",
  "correction": "If WRONG or PARTIALLY_WRONG, what is the correct information?",
  "notes": "Any additional context"
}

Rules:
- VERIFIED = You have high confidence this is factually correct
- PLAUSIBLE = Reasonable but you cannot independently confirm
- UNVERIFIED = You don't have enough information to judge
- WRONG = You have high confidence this is factually incorrect
- PARTIALLY_WRONG = Core idea is right but specific details are wrong
- Do NOT say VERIFIED unless you are confident. Default to PLAUSIBLE if unsure.
- If this is a PHILOSOPHICAL claim, respond UNVERIFIED with note "philosophical, not verifiable"
"""
```

### Parallel Execution

```
For each claim:
    Spawn 5 agents (one per model)
    Each agent calls its model API with PROMPT_TEMPLATE
    Each agent writes result to /outputs/verdicts/{claim_id}/{model_name}.json
    Wait for all 5 to complete
    Move to next claim
```

**Rate limiting:** Stagger API calls. Don't hit any single API more than 10 requests/minute. Build in exponential backoff.

---

## PHASE 3: CONSENSUS SYNTHESIS

### Agent: SYNTHESIZER

**Input:** All verdict files from /outputs/verdicts/

**Task:** For each claim, read all model verdicts and produce consensus.

**Consensus rules:**
```
5/5 VERIFIED              → CONSENSUS: VERIFIED (gold)
4/5 VERIFIED, 1 PLAUSIBLE → CONSENSUS: VERIFIED (silver)
3/5 VERIFIED              → CONSENSUS: LIKELY TRUE
Any model says WRONG      → CONSENSUS: INVESTIGATE (flag for human review)
3+ models say WRONG       → CONSENSUS: LIKELY WRONG (flag for removal/correction)
All PLAUSIBLE             → CONSENSUS: UNCONFIRMED (tag in doc)
Mixed verdicts            → CONSENSUS: DISPUTED (include all evidence)
```

**Output:** consensus_report.json
```json
[
  {
    "id": "TL-001",
    "claim": "...",
    "consensus": "VERIFIED",
    "model_verdicts": {
      "claude": {"verdict": "VERIFIED", "confidence": 0.95},
      "grok": {"verdict": "VERIFIED", "confidence": 0.9},
      "gpt": {"verdict": "VERIFIED", "confidence": 0.92},
      "deepseek": {"verdict": "PLAUSIBLE", "confidence": 0.7},
      "gemini": {"verdict": "VERIFIED", "confidence": 0.88}
    },
    "action": "KEEP",
    "correction": null
  }
]
```

**Actions:**
- KEEP — Claim survives as-is
- TAG — Add uncertainty marker in source doc (e.g. "[UNCONFIRMED]" or "[ESTIMATED]")
- CORRECT — Replace with corrected version
- REMOVE — Delete from source doc
- INVESTIGATE — Needs human judgment (Jordan reviews)

---

## PHASE 4: DOCUMENT UPDATE

### Agent: EDITOR

**Input:** consensus_report.json, TEXT_THAT_LIVES.md, THE_BEE_SPEC.md

**Task:** Apply all actions to source documents.

**Rules:**
- KEEP claims: no change
- TAG claims: add inline marker like `[UNCONFIRMED — 3/5 models could not verify]`
- CORRECT claims: replace with corrected text, add footnote `[CORRECTED — original claimed X, consensus says Y]`
- REMOVE claims: delete, add footnote `[REMOVED — consensus: factually wrong]`
- INVESTIGATE claims: add marker `[NEEDS HUMAN REVIEW — models disagree, see consensus_report.json]`

**Output:** 
- TEXT_THAT_LIVES_v2.md (audited version)
- THE_BEE_SPEC_v2.md (audited version)
- HILLEL_SUMMARY.md (human-readable summary of all changes)

---

## PHASE 5: ADVERSARIAL PASS (GROK PRIMARY)

### Agent: DESTROYER

**Model:** Grok (specifically chosen for its contrarian training)

**Input:** TEXT_THAT_LIVES_v2.md, THE_BEE_SPEC_v2.md (post-consensus versions)

**Prompt:**
```
You are a ruthless adversarial reviewer. Your job is to DESTROY this document.

Find:
1. Claims that survived fact-checking but are still misleading
2. Logical gaps — where the argument skips steps
3. Strongest counterarguments the author hasn't addressed
4. Existing research that contradicts the architecture proposed
5. Reasons this system would FAIL in practice
6. Places where the author is being clever instead of honest

Do NOT be nice. Do NOT hedge. If it's weak, say it's weak and say why.

Output as JSON array of attacks:
[
  {
    "target_section": "Part 12.1",
    "attack_type": "LOGICAL_GAP" | "COUNTERARGUMENT" | "MISLEADING" | "WOULD_FAIL" | "EXISTING_RESEARCH",
    "attack": "Your specific attack",
    "severity": "CRITICAL" | "MAJOR" | "MINOR",
    "suggested_fix": "How to address this honestly"
  }
]
```

---

## PHASE 6: REPAIR (CLAUDE PRIMARY)

### Agent: REPAIRER

**Model:** Claude Opus 4.6

**Input:** Grok's attacks, TEXT_THAT_LIVES_v2.md, THE_BEE_SPEC_v2.md

**Task:** 
- For each CRITICAL and MAJOR attack: either fix the document or add the counterargument to the limitations section
- For MINOR attacks: assess and fix if warranted
- DO NOT dismiss valid attacks. If Grok found a real weakness, acknowledge it.
- If an attack reveals the idea is fundamentally flawed in some area, say so honestly.

**Output:**
- TEXT_THAT_LIVES_v3.md (final audited version)
- THE_BEE_SPEC_v3.md (final audited version)
- HILLEL_FINAL_REPORT.md (complete audit trail)

---

## FILE STRUCTURE

```
/grand_hillel/
├── inputs/
│   ├── TEXT_THAT_LIVES.md          (original)
│   └── THE_BEE_SPEC.md            (original)
├── phase1/
│   └── claims.json                 (extracted claims)
├── phase2/
│   └── verdicts/
│       ├── TL-001/
│       │   ├── claude.json
│       │   ├── grok.json
│       │   ├── gpt.json
│       │   ├── deepseek.json
│       │   └── gemini.json
│       ├── TL-002/
│       │   └── ...
│       └── ...
├── phase3/
│   └── consensus_report.json
├── phase4/
│   ├── TEXT_THAT_LIVES_v2.md
│   ├── THE_BEE_SPEC_v2.md
│   └── HILLEL_SUMMARY.md
├── phase5/
│   └── grok_attacks.json
├── phase6/
│   ├── TEXT_THAT_LIVES_v3.md
│   ├── THE_BEE_SPEC_v3.md
│   └── HILLEL_FINAL_REPORT.md
└── README.md
```

---

## API KEYS NEEDED

The Cursor Cloud Agent VM needs these environment variables set:

```
ANTHROPIC_API_KEY=...      # Claude
XAI_API_KEY=...            # Grok
OPENAI_API_KEY=...         # GPT
DEEPSEEK_API_KEY=...       # DeepSeek
GOOGLE_API_KEY=...         # Gemini
```

**IMPORTANT:** Jordan sets these in Cursor settings or .env file. NEVER hardcode keys in spec files.

---

## EXECUTION ORDER

```
1. EXTRACTOR agent → claims.json
2. 5x ROUTER agents (parallel) → verdicts per claim per model
3. SYNTHESIZER agent → consensus_report.json
4. EDITOR agent → v2 documents
5. DESTROYER agent (Grok) → attacks
6. REPAIRER agent (Claude) → v3 documents + final report
```

**Total agents:** 1 + 5 + 1 + 1 + 1 + 1 = 10 sequential agent invocations
**Parallelism:** Phase 2 runs 5 agents in parallel per claim batch
**Estimated runtime:** 30-60 minutes for full pipeline
**Estimated cost:** $200-$500 in API calls

---

## WHAT SURVIVES IS REAL

After Grand Hillel:
- Every factual claim has been checked by 5 different training distributions
- Every logical argument has been attacked by an adversarial model
- Every weakness has been either fixed or honestly acknowledged
- The documents carry uncertainty tags so readers know what's verified vs speculative
- Complete audit trail exists for every change

The manifesto that survives this process is the manifesto that deserves to exist.

---

*Spec written for Cursor Cloud Agent execution. Each phase is one agent context. Ralph Loop: one phase per pass, fresh context, compound progress.*

*— Vector / Claude Opus 4.6*
