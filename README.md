# Bachelor Thesis Workbench

Experimental codebase for thesis work on LLM behavior analysis, prompt effects, and evaluation workflows.

## Repository structure

- `src/` - analysis and experiment modules (scoring, leakage checks, post-hoc analysis, plots)
- `notebooks/` - exploratory notebook work
- `data/` - local datasets and generated outputs
- `docs/` - thesis/project documentation
- `requirements.txt` - Python dependencies

## Key scripts in `src/`

- `experiment_runner.py` - run experiment batches
- `scoring_engine.py` - scoring/evaluation logic
- `leak_judge.py` - prompt leakage checks
- `statistical_analysis.py` - statistical post-processing
- `plot_scored_results.py` - visualization pipeline

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Status

Active research workspace. Structure and scripts evolve during thesis iteration.
