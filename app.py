import logging
import os
import random

import streamlit as st
from logic_utils import check_guess, update_score
from ai_agent import safe_agent_guess

try:
    import anthropic
except ImportError:
    anthropic = None

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/agent.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def get_range_for_difficulty(difficulty: str):
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100


def parse_guess(raw: str):
    if raw is None:
        return False, None, "Enter a guess."

    if raw == "":
        return False, None, "Enter a guess."

    try:
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."

    return True, value, None


@st.cache_resource
def get_agent_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        return None
    return anthropic.Anthropic(api_key=api_key)


st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit_map = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 5,
}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

st.sidebar.divider()
mode = st.sidebar.radio("Mode", ["Manual", "AI Agent"], index=0)

agent_client = get_agent_client()
if mode == "AI Agent" and agent_client is None:
    st.sidebar.warning(
        "Set the ANTHROPIC_API_KEY environment variable to enable AI Agent mode. "
        "Using Manual mode instead."
    )
    mode = "Manual"

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)

if "attempts" not in st.session_state:
    st.session_state.attempts = 1

if "score" not in st.session_state:
    st.session_state.score = 0

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []

if "agent_low" not in st.session_state:
    st.session_state.agent_low = low

if "agent_high" not in st.session_state:
    st.session_state.agent_high = high

if "agent_log" not in st.session_state:
    st.session_state.agent_log = []

st.subheader("Make a guess")

st.info(
    f"Guess a number between 1 and 100. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)
    st.write("Agent bounds:", (st.session_state.agent_low, st.session_state.agent_high))


def process_guess(guess_int, attempt_source="manual", reasoning=None):
    """Run one guess through the shared scoring/win-loss path.

    Used by both the manual Submit button and the AI Agent button so both
    modes play through identical game logic (same check_guess/update_score
    calls, same win/loss detection).
    """
    st.session_state.attempts += 1
    st.session_state.history.append(guess_int)

    if st.session_state.attempts % 2 == 0:
        secret = str(st.session_state.secret)
    else:
        secret = st.session_state.secret

    outcome, message = check_guess(guess_int, secret)

    if show_hint:
        st.warning(message)

    st.session_state.score = update_score(
        current_score=st.session_state.score,
        outcome=outcome,
        attempt_number=st.session_state.attempts,
    )

    if outcome == "Win":
        st.balloons()
        st.session_state.status = "won"
        st.success(
            f"You won! The secret was {st.session_state.secret}. "
            f"Final score: {st.session_state.score}"
        )
    else:
        if st.session_state.attempts >= attempt_limit:
            st.session_state.status = "lost"
            st.error(
                f"Out of attempts! "
                f"The secret was {st.session_state.secret}. "
                f"Score: {st.session_state.score}"
            )

    if attempt_source == "agent":
        if outcome == "Too High":
            st.session_state.agent_high = min(st.session_state.agent_high, guess_int - 1)
        elif outcome == "Too Low":
            st.session_state.agent_low = max(st.session_state.agent_low, guess_int + 1)

        st.session_state.agent_log.append(
            {
                "guess": guess_int,
                "reasoning": reasoning,
                "outcome": outcome,
                "message": message,
            }
        )

        if (
            st.session_state.status == "playing"
            and st.session_state.agent_low > st.session_state.agent_high
        ):
            logging.getLogger("ai_agent").error(
                "Agent bounds crossed (low=%s > high=%s) after guessing %s — "
                "check_guess returned a hint inconsistent with earlier hints.",
                st.session_state.agent_low,
                st.session_state.agent_high,
                guess_int,
            )
            st.session_state.status = "lost"
            st.error(
                "🚨 The agent's hint history became contradictory (its search "
                "bounds crossed). That means the hint logic gave two inconsistent "
                "hints — start a new game."
            )

    return outcome


if mode == "Manual":
    raw_guess = st.text_input(
        "Enter your guess:",
        key=f"guess_input_{difficulty}"
    )
else:
    raw_guess = None
    st.info(
        f"🤖 AI Agent mode — the agent is narrowing its search between "
        f"{st.session_state.agent_low} and {st.session_state.agent_high}."
    )

col1, col2, col3 = st.columns(3)
with col1:
    if mode == "Manual":
        submit = st.button("Submit Guess 🚀")
        agent_turn = False
    else:
        submit = False
        agent_turn = st.button("🤖 Agent: Make Next Guess")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

if new_game:
    st.session_state.attempts = 0
    st.session_state.secret = random.randint(low, high)
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.agent_low = low
    st.session_state.agent_high = high
    st.session_state.agent_log = []
    st.success("New game started.")
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won. Start a new game to play again.")
    else:
        st.error("Game over. Start a new game to try again.")
    st.stop()

if submit:
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.attempts += 1
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        process_guess(guess_int, attempt_source="manual")

if agent_turn:
    guess_int, reasoning, source = safe_agent_guess(
        st.session_state.agent_low,
        st.session_state.agent_high,
        st.session_state.agent_log,
        agent_client,
    )
    st.info(f"🤖 Agent guesses **{guess_int}** — {reasoning}")
    process_guess(guess_int, attempt_source="agent", reasoning=f"[{source}] {reasoning}")

if st.session_state.agent_log:
    with st.expander("🤖 Agent Reasoning Log"):
        st.table(st.session_state.agent_log)

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
