# SJSU Agentic AI Coworkers

**Assignment:** Build two personalized AI coworkers: a DailyTechUpgradeAgent and a nextLevelPersonalCoachForCareerLevel. The career coworker covers jobs, internships and research roles on public boards, plus personalized **entrepreneurship hypotheses** with founder interviews.

This repository contains a Streamlit front end, LangGraph workflows, public information retrieval tools, SQLite long-term memory, sample results, and evaluation checks.

## Quick start

Python 3.11 or 3.12 is recommended.

```bash
# From the folder containing this README:
python -m venv .venv

# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell, instead:
# .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
streamlit run app.py
```

The application opens in your browser. Start in **Demo mode**: **Discover top 3**, then **Find job matches**, **Practice interview**, and answer three questions. Open the **Progress** and **Evaluation** tabs to show your professor the memory and metrics.

**Convenience scripts:** on macOS/Linux, run `./start.sh`; on Windows, double-click `start.bat` to create the venv, install requirements, and start Streamlit. They need internet access on the first install.

**No OpenAI API key is needed for Demo mode.** Demo is an end-to-end prototype with an offline sequential-runner fallback when LangGraph is not installed; with requirements installed, it uses actual LangGraph orchestration. Article examples are real, source-linked historical October 2026 publications. The demo job postings are invented and prominently labeled as synthetic.

## Enable Live mode

1. Change the sidebar Data mode to **Live**.
2. Article discovery downloads posts from selected reputable RSS feeds (AWS, Microsoft, Google, LangChain, IEEE and ACM). Feeds can be unavailable; errors are reported.
3. Job discovery queries public Greenhouse Job Board API endpoints using configurable company board tokens. Results link back to actual source listings. Some tokens may no longer work; use **Paste a job description** to assess a custom role.
4. To enable model-generated explanations and technical interview scoring:

```bash
cp .env.example .env    # On Windows, copy .env.example .env
# Edit .env and set OPENAI_API_KEY=... and optionally OPENAI_MODEL=...
streamlit run app.py
```

The OpenAI API is a separately billed service and is not automatically included with a ChatGPT subscription. Use the sidebar checkbox **Use OpenAI for analysis** once configured. AI feedback is based on supplied excerpts and answers; no claim of independent paper comprehension is made. With no key, live mode still uses actual feeds and job descriptions but produces extractive article summaries and simple keyword-rubric interview grades.

**Privacy:** Data is saved locally to `outputs/coworkers.sqlite3`. Avoid entering sensitive personal data. If you enable OpenAI analysis, relevant article excerpt and interview text are sent to the model API. No job applications are submitted.

## CLI demonstrations / testing

```bash
python demo_cli.py              # Offline full workflow, persists sample results
python -m pytest -q            # Deterministic test suite
python run_daily.py --mode demo # Writes dated JSON sample to outputs/
python run_daily.py --mode live # Live RSS mode; needs network access
python run_daily.py --mode live --ai # AI summaries; requires API key
```

## Daily scheduling

Schedule the **one-shot** `run_daily.py` command using your OS. The app does **not** claim to run daily when your computer is off.

macOS / Linux cron example (adjust paths and interpreter):

```cron
0 8 * * * cd /ABSOLUTE/PATH/agentic_ai_coworkers && /ABSOLUTE/PATH/agentic_ai_coworkers/.venv/bin/python run_daily.py --mode live
```

Windows: open Task Scheduler, create a Daily trigger, and use the virtual environment's `python.exe` as Program and the absolute path to `run_daily.py --mode live` as arguments (or create a small `.bat` script). Set Start in to the project folder.

## Demonstration sequence (3–5 minutes)

1. Show the two LangGraph workflows and shared SQLite storage in `docs/architecture.png`.
2. Run the **Daily Tech Brief** in Demo mode and show the three verified article URLs, dates, source summaries, and 18-minute plan.
3. Run **Career Coach**, find three synthetic openings, inspect match scores and missing skills, and start an interview.
4. Give an incomplete first answer and demonstrate an adaptive follow-up question; complete the coding exercise. The Startup Idea Lab also offers a founder coaching scenario.
5. Open **Progress**, note the saved weakness; return to Daily Tech Brief and explain that priority terms raise matching article ranks.
6. Open **Evaluation** and explain what has actually been measured and what still needs manual labels.

## Evaluation and claims

Automatically measured: three-article completeness, nonduplicate URLs, metadata completeness, question counts, interview completion, topic-level rubric scores, and local history.

Requires additional human ground truth: summary factuality, link reachability over time, true job relevance, conceptual grading accuracy, and student learning progress. `evaluation/metrics.py` includes a `labeled_relevance_precision` helper for manual relevance labeling. Do **not** cite the demo rubric as proven career readiness.

## Directory map

- `app.py` — four-tab Streamlit interface
- `agents/` — actual LangGraph workflow definitions
- `tools/` — RSS fetching, Greenhouse API, venture idea lab, optional OpenAI and test-only compatibility runner
- `memory/store.py` — SQLite tables and persistence
- `evaluation/metrics.py` — evaluation checks with explicit limits
- `examples/` — source-verified article fixture and **fictional** job fixtures
- `tests/` — no-network tests for workflow, memory, parsing, scoring and founder scenarios
- `docs/` — diagrams and assignment architecture explanation
- `outputs/` — sample reports and saved local runtime state

## Submission checklist

- [x] Agent goals and outcomes: `docs/ARCHITECTURE.md`
- [x] Architecture diagram: `docs/architecture.png`, plus Mermaid diagrams
- [x] Working prototype source: `app.py`, `agents/`, `tools/`, `memory/`
- [x] Sample results: `outputs/sample_daily_brief.json`, `outputs/sample_career_report.json`
- [x] Evaluation framework: `evaluation/metrics.py`, `tests/`, Evaluation tab
- [ ] Student-provided screenshots / recorded demo after running the app
- [ ] Human-labeled evaluation results and written reflection (optional for further rigor)

## Verified public references for the architecture

- [LangGraph StateGraph reference](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)
- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board)
- [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
