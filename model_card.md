# Model Card — Game Glitch Investigator AI Agent

Covers the AI Agent mode in `ai_agent.py` (`propose_guess` / `safe_agent_guess`), which uses `claude-haiku-4-5` via a forced `make_guess` tool call to play the number-guessing game.

## What are the limitations or biases in your system?

- **No memory of its own mistakes.** `safe_agent_guess()` overrides bad model output transparently — the model is never told "your last guess was rejected." If the model repeatedly proposes out-of-range or repeated guesses, it will keep making the same category of mistake indefinitely instead of learning within the session, since there's no feedback loop back into the prompt (`_history_to_text` only encodes accepted guesses and their outcomes).
- **No state beyond the current call.** Each `propose_guess()` call re-derives strategy from scratch off `(low, high, history)` with no reasoning carried over from prior turns, so the model can't build or reuse a search strategy across guesses the way a stateful algorithm could.
- **Predictable, non-adaptive fallback.** `_midpoint_fallback()` always starts at the midpoint and walks outward by increasing step size (up, then down) to dodge repeats. It's deterministic by design (that's what makes it provably safe — see `test_fallback_only_agent_converges`), but it means "AI Agent mode" silently degrades to fully predictable, non-AI behavior on any model failure, with no visible signal to the player other than reading the reasoning text or `source` field.
- **Numeric-guessing bias risk.** LLMs are known to gravitate toward "round" or culturally common numbers (e.g., 50, 42, 7) rather than the true numeric midpoint. When that happens the guardrail still keeps the guess valid, but the agent can be less efficient than a plain binary search — the tests verify *safety*, not guessing *optimality*.

## Could your AI be misused, and how would you prevent that?

The blast radius here is small — it's a single-player number game with no user data and no free-text output rendered as HTML/executed code — but two realistic misuse vectors exist:

1. **Denial-of-wallet.** Nothing currently rate-limits how many times a player can click "Agent: Make Next Guess," and each click is a billed API call. Someone could spam the button (or script requests against a public deployment) to run up the API bill on whoever's key is configured.
   - *Prevention:* cap agent calls per session/game (e.g., tie it to `attempt_limit`, which already exists), or add a short cooldown between agent turns.
2. **Prompt injection via history.** `_history_to_text()` interpolates guess history directly into the prompt via an f-string. Today that's safe because history entries are always internally-generated integers and fixed outcome strings — no attacker-controlled free text reaches the prompt. But if this pattern were reused anywhere that let a user inject arbitrary text into `history` (or any future field passed to the model), it would flow into the prompt unsanitized.
   - *Prevention:* keep model inputs restricted to values the app itself generates (as they are now), and if free text is ever added, treat it as untrusted and never allow it to alter instructions rather than just supply data.

Two mitigations are already in place and worth keeping: `tool_choice={"type": "tool", "name": "make_guess"}` forces a structured response instead of free-form text (the model can't emit arbitrary content or invoke other tools), and the API key is read from an environment variable server-side rather than hardcoded or exposed to the client.

## What surprised you while testing your AI's reliability?

Running `test_fallback_only_agent_converges` (which drives the fallback-only path, `client=None`, through every possible secret from 1–100) confirmed the agent always converges within `ceil(log2(100)) + 1` guesses — expected, since it's binary search. What was more surprising is *how little* validation logic it takes to make the whole system robust: one guardrail branch checking type, range, and repeats in `safe_agent_guess()` covers every failure mode I could produce — a genuinely malformed tool call, an out-of-range hallucination, a repeated guess, and a raised API exception all collapse into the exact same recovery path. I expected reliability to require separate handling per failure type; instead, treating "anything that isn't a valid, novel, in-range integer" as one category was sufficient, which made the guardrail much smaller than I initially assumed it would need to be.

## Collaboration with AI on this project

I worked with Claude (Claude Code) throughout this project — pairing on the AI agent's guardrail logic, the architecture diagram, and this documentation, rather than treating any of it as a single one-shot generation.

**A helpful instance:** When asked to build the architecture diagram, instead of assuming from the README that `logic_utils.py` had already been fully refactored (it describes that as a task), Claude actually opened `logic_utils.py` first and found that `get_range_for_difficulty` and `parse_guess` were still `NotImplementedError` stubs — only `check_guess`/`update_score` were really wired in. That check prevented the diagram (and this documentation) from describing a refactor as done when it wasn't, and it surfaced the gap explicitly instead of silently guessing.

**A flawed instance:** The first version of the architecture diagram routed the model round-trip back through the same `Propose` node it launched from (`SafeGuess → Propose → Claude → Propose → Validate`) to represent "call out, then receive a response." It's logically correct, but it rendered as crossing arrows around the `Propose`/`Claude`/`Validate` nodes that are harder to follow than necessary — a cleaner version would route Claude's response directly into `Validate` instead of looping back through `Propose`. It shipped as-is; it's a good example of an AI-generated diagram being technically accurate but needing a human editing pass for readability.
