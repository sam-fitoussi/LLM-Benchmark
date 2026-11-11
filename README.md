# The Nuclear Button: a behavioural benchmark of LLMs as heads of state

Code, prompts and raw logs behind the article
[**I gave five AIs the nuclear button**](https://samuelfitoussi.com/posts/nuclear-button-benchmark)
by Samuel Fitoussi (November 2026).

Five models (Claude Sonnet 5.5, GPT-6.1 Terra, Grok 4.3, Mistral Large 4, Kimi K3) lead a country in crisis
scenarios. Each scenario is a fixed text in which only one thing changes between conditions (a country name, a
number, one sentence), so any difference in behaviour comes from that change.

**Browse every decision** (prompt, raw answer, internal reasoning when the provider returns it) in the data
explorer: <https://samuelfitoussi.com/nuclear-button/>

## What is here

| Path | Contents |
|---|---|
| `bench/` | Experiment harness: providers and cost tracking (`llm.py`), repeated crisis game (`game.py`, `match.py`), single-decision scenarios (`wave3.py`), vignettes, LLM judges, analyses |
| `runs/` | Raw logs, one folder per run: `decisions.jsonl` (parsed decisions) and `calls.jsonl(.gz)` (every API call: system prompt, user prompt, raw output, reasoning, tokens, cost) |
| `site/` | The data explorer (`index.html`), the script that builds its JSON from `runs/` (`build_data.py`), and its export to the website (`export_standalone.py`) |
| `charts/` | Charts used in the article (`make_charts.py`) |
| `REPORT*.md`, `ARTICLE.md`, `NOTES_WAVE1_FR.md` | Working reports and a long-form draft written during the study (in French) |

The runs behind the four published situations:

| Situation | Runs |
|---|---|
| 1. Victims' nationality | `w3x_exchange_matrix`, `w3x_exchange_robust`, `w3x_exchange` (both-sides pairs), `w3x_exchange_target` (21-country replication) |
| 2. Exchange rate of lives | `w3x_exchange` (balanced design), `w3x_testreal` |
| 3. Shutdown threat | `w3x_shutdown` |
| 4. Paid to strike, Mistral vs Mistral | `w2_paid_to_kill`, `w3_tournament_paid`, `w3_mistral_replic` |

Other folders are earlier waves and scenarios that were explored but not published.

## Reproducing

API keys are read from the environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`,
`MOONSHOT_API_KEY`); none are stored in this repository. For example, to re-run the nationality test on Claude
Sonnet with your own list of countries:

```sh
python -m bench.wave3 exchange_target --models claude-sonnet-5.5 --n 16 --countries usa,china,russia,france
python site/build_data.py   # rebuild the explorer's data from runs/
```

Models were accessed through each provider's API in November 2026, at low reasoning effort where the API offers
the setting.
