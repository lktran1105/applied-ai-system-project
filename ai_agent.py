"""AI Agent for the Number Guessing Game.

Provides an LLM-driven "next guess" proposer, wrapped in a guardrail
(`safe_agent_guess`) that never trusts the model's output blindly: any
out-of-range guess, repeated guess, malformed response, or API failure is
caught and replaced with a deterministic binary-search midpoint. Callers
should only ever use `safe_agent_guess` — `propose_guess` is the raw,
unguarded call and can raise.
"""

import logging

logger = logging.getLogger("ai_agent")

MODEL = "claude-haiku-4-5-20251001"

GUESS_TOOL = {
    "name": "make_guess",
    "description": (
        "Propose the next guess for a number-guessing game, plus a short "
        "reasoning for why that number was chosen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "guess": {
                "type": "integer",
                "description": "The next number to guess.",
            },
            "reasoning": {
                "type": "string",
                "description": "One short sentence explaining why this guess was chosen.",
            },
        },
        "required": ["guess", "reasoning"],
    },
}


def _history_to_text(history):
    if not history:
        return "No guesses yet."
    return "\n".join(f"Guessed {h['guess']} -> {h['outcome']}" for h in history)


def propose_guess(low, high, history, client, model=MODEL):
    """Ask the model for the next guess.

    Raises on any API or parsing failure — callers must go through
    `safe_agent_guess` rather than calling this directly.
    """
    prompt = (
        f"You are playing a number-guessing game. The secret number is an "
        f"integer between {low} and {high} inclusive. Guess history so far:\n"
        f"{_history_to_text(history)}\n\n"
        f"Call make_guess with your next guess and a one-sentence reasoning."
    )

    response = client.messages.create(
        model=model,
        max_tokens=256,
        tools=[GUESS_TOOL],
        tool_choice={"type": "tool", "name": "make_guess"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "make_guess":
            data = block.input
            return int(data["guess"]), str(data["reasoning"])

    raise ValueError("Model did not return a make_guess tool call.")


def _midpoint_fallback(low, high, already_tried):
    guess = (low + high) // 2
    step = 1
    while guess in already_tried and low <= high:
        up = guess + step
        down = guess - step
        if up <= high and up not in already_tried:
            guess = up
            break
        if down >= low and down not in already_tried:
            guess = down
            break
        step += 1
        if step > (high - low + 1):
            break
    return guess


def safe_agent_guess(low, high, history, client, model=MODEL):
    """Guarded wrapper around `propose_guess`.

    Never raises; always returns (guess: int, reasoning: str, source),
    where source is "llm" or "fallback". Any invalid model output (out of
    range, already tried, wrong type) or any exception from the API call
    is caught and replaced with a deterministic binary-search midpoint.
    """
    already_tried = {h["guess"] for h in history}
    fallback_guess = _midpoint_fallback(low, high, already_tried)

    if client is None:
        logger.info("No API client configured; using fallback guess %s", fallback_guess)
        return (
            fallback_guess,
            "No API client configured — used binary search midpoint.",
            "fallback",
        )

    try:
        guess, reasoning = propose_guess(low, high, history, client, model=model)
    except Exception as exc:
        logger.warning(
            "Agent LLM call failed (%s); falling back to midpoint %s", exc, fallback_guess
        )
        return (
            fallback_guess,
            f"Model call failed ({exc}); used binary search midpoint instead.",
            "fallback",
        )

    if not isinstance(guess, int) or guess < low or guess > high or guess in already_tried:
        logger.warning(
            "Agent proposed invalid guess %r (bounds %s-%s, already tried %s); "
            "falling back to %s",
            guess,
            low,
            high,
            already_tried,
            fallback_guess,
        )
        return (
            fallback_guess,
            f"Model guess {guess!r} was invalid; used binary search midpoint instead.",
            "fallback",
        )

    logger.info("Agent guessed %s via LLM: %s", guess, reasoning)
    return guess, reasoning, "llm"
