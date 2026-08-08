# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable. 

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. (Optional, enables AI Agent mode) Set your Anthropic API key: `export ANTHROPIC_API_KEY=your-key-here`
3. Run the app: `python -m streamlit run app.py`

## 🤖 AI Agent Mode

Switch **Mode** to `AI Agent` in the sidebar to let an LLM play the game instead of typing guesses yourself.

- Each click of **"Agent: Make Next Guess"** calls Claude (`ai_agent.py`) with the current search bounds and guess history; the model returns a guess plus a one-sentence reasoning, shown live and logged in the **Agent Reasoning Log** expander.
- The agent's guess goes through the exact same `check_guess` / `update_score` path as a manual guess (`process_guess` in `app.py`) — it is a real alternate way to play, not a side script.
- **Guardrails**: any model guess that is out of range, already tried, or the wrong type is rejected and replaced with a deterministic binary-search midpoint, as is any API error, timeout, or malformed response — the game can never crash or stall because of the model. If the agent's search bounds ever cross (a sign the hint logic produced two contradictory hints), the game flags it and ends the round rather than continuing silently.
- **Logging**: every guess, fallback trigger, and API error is written to `logs/agent.log` in addition to the on-screen log.
- If `ANTHROPIC_API_KEY` isn't set, AI Agent mode is disabled with a message instead of failing on first click.
- `tests/test_ai_agent.py` covers the guardrail logic (invalid/repeated guesses, API failures, full-game convergence) using a mocked client — no API key or network access needed to run the test suite.

## 🕵️‍♂️ Your Mission

1. **Play the game.** Open the "Developer Debug Info" tab in the app to see the secret number. Try to win.
2. **Find the State Bug.** Why does the secret number change every time you click "Submit"? Ask ChatGPT: *"How do I keep a variable from resetting in Streamlit when I click a button?"*
3. **Fix the Logic.** The hints ("Higher/Lower") are wrong. Fix them.
4. **Refactor & Test.** - Move the logic into `logic_utils.py`.
   - Run `pytest` in your terminal.
   - Keep fixing until all tests pass!

## 📝 Document Your Experience

- [ ] Describe the game's purpose.
- [ ] Detail which bugs you found.
- [ ] Explain what fixes you applied.

## 📸 Demo Walkthrough

Describe your fixed game in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot** *(optional)*: <!-- Insert a screenshot of your fixed, winning game here -->

## 🧪 Test Results

```
# Paste your pytest output here, e.g.:
# pytest tests/
# ========================= X passed in 0.XXs =========================
```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, describe the Enhanced UI changes here — a screenshot is optional]
