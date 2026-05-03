# Vera Pro — magicpin AI Challenge Submission

## Approach

**Core architecture**: Claude claude-sonnet-4-20250514 as the composition engine, wrapped in a stateful Flask HTTP server exposing all 5 required endpoints.

### Composition strategy

Every message is composed by passing all 4 context layers to Claude with a tightly constrained system prompt that enforces:
- **Specificity-first**: anchoring on concrete numbers/dates/sources from the contexts
- **Voice matching**: category-specific tone enforcement (peer-clinical for dentists, etc.)
- **Language detection**: Hindi-English code-mix when merchant language is `hi` or `hi-en`
- **Anti-pattern avoidance**: explicit prohibition of generic "% off" framing, long preambles, multi-CTA

### Routing layer

- **Research/digest triggers**: surface the top digest item with trial_n + source citation
- **Performance triggers**: lead with the merchant's exact delta (CTR, views, calls) vs. peer median
- **Recall/customer triggers**: use customer's actual visit history + preferred slot timing
- **Dormancy triggers**: curiosity-first hook, not a reminder

### Multi-turn handling

- **Auto-reply detection**: same message text repeated 2+ times from merchant → attempt once then graceful exit
- **Intent transition**: regex on YES/confirm variants → immediately switch to action mode without re-qualifying
- **Hostile/off-topic**: polite redirection, then exit if persists

### What additional context would have helped most

1. **Real merchant reply patterns** — knowing which phrasing merchants actually use to confirm/decline would sharpen intent detection
2. **Suppression history** — knowing what Vera already sent this week would let us diversify the conversation portfolio
3. **Slot availability** — for recall/appointment triggers, knowing actual open calendar slots would let us make concrete booking offers instead of open-ended CTAs

## Tradeoffs made

- Used `temperature=0` (default for claude-sonnet-4-20250514 deterministic mode) per challenge requirements
- In-memory state only — fine for a 60-minute test window
- Single LLM call per composition rather than retrieval + generation — faster, within 30s budget

## Running locally

```bash
pip install -r requirements.txt
export PORT=8080
python bot.py
```

Test with:
```bash
curl http://localhost:8080/v1/healthz
```
