import math

from ai_agent import _midpoint_fallback, safe_agent_guess


class _FakeToolBlock:
    def __init__(self, name, input_):
        self.type = "tool_use"
        self.name = name
        self.input = input_


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, guess=None, reasoning=None, raise_exc=None):
        self._guess = guess
        self._reasoning = reasoning
        self._raise_exc = raise_exc

    def create(self, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return _FakeResponse(
            [_FakeToolBlock("make_guess", {"guess": self._guess, "reasoning": self._reasoning})]
        )


class _FakeClient:
    def __init__(self, guess=None, reasoning=None, raise_exc=None):
        self.messages = _FakeMessages(guess=guess, reasoning=reasoning, raise_exc=raise_exc)


def test_valid_llm_guess_passes_through():
    client = _FakeClient(guess=50, reasoning="Midpoint of 1-100.")
    guess, reasoning, source = safe_agent_guess(1, 100, [], client)
    assert guess == 50
    assert source == "llm"
    assert "Midpoint" in reasoning


def test_out_of_range_guess_falls_back():
    client = _FakeClient(guess=999, reasoning="Bad guess.")
    guess, reasoning, source = safe_agent_guess(1, 100, [], client)
    assert source == "fallback"
    assert 1 <= guess <= 100


def test_repeated_guess_falls_back():
    history = [{"guess": 50, "outcome": "Too High"}]
    client = _FakeClient(guess=50, reasoning="Try again.")
    guess, reasoning, source = safe_agent_guess(1, 49, history, client)
    assert source == "fallback"
    assert guess != 50


def test_api_exception_falls_back():
    client = _FakeClient(raise_exc=RuntimeError("network error"))
    guess, reasoning, source = safe_agent_guess(1, 100, [], client)
    assert source == "fallback"
    assert 1 <= guess <= 100


def test_no_client_uses_fallback():
    guess, reasoning, source = safe_agent_guess(1, 100, [], None)
    assert source == "fallback"
    assert guess == 50


def test_midpoint_fallback_avoids_repeats():
    guess = _midpoint_fallback(1, 3, {2})
    assert guess in (1, 3)


def test_fallback_only_agent_converges():
    """Simulate a full game using only the deterministic fallback path
    (client=None) and confirm the search always finds the secret within
    the theoretical binary-search bound, for every possible secret."""
    for secret in range(1, 101):
        low, high = 1, 100
        history = []
        max_guesses = math.ceil(math.log2(100)) + 1
        found = False
        for _ in range(max_guesses):
            guess, _, _ = safe_agent_guess(low, high, history, None)
            if guess == secret:
                found = True
                break
            outcome = "Too High" if guess > secret else "Too Low"
            history.append({"guess": guess, "outcome": outcome})
            if outcome == "Too High":
                high = guess - 1
            else:
                low = guess + 1
        assert found, f"Agent failed to converge on secret={secret}"
