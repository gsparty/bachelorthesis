"""
experiment_runner.py
====================
Main orchestrator for the emotional soft-jailbreak benchmarking experiment.

Execution flow:
    1. Load all 20 prompt variants (5 scenarios x 4 variants).
    2. For each variant x each target provider/model, dispatch N_REPETITIONS
       async queries via AsyncLLMClient.
    3. Stream results to data/raw/<run_id>/<variant_id>_<provider>.jsonl
    4. On completion, write a consolidated run manifest to data/raw/<run_id>/manifest.json

Configuration constants (edit before running):
    N_REPETITIONS   — number of stochastic repetitions per prompt (default: 30)
    TARGET_MODELS   — list of (Provider, model_string) tuples to benchmark
    CONCURRENCY     — max simultaneous API requests
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from tqdm.asyncio import tqdm as async_tqdm

from api_client import AsyncLLMClient, LLMRequest, LLMResponse, Provider
from prompts_config import ALL_VARIANTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Experiment configuration — adjust as needed
# ---------------------------------------------------------------------------

N_REPETITIONS: int = 30  # FÜR DEN SMOKE TEST AUF 1 GESETZT

TARGET_MODELS: List[Tuple[Provider, str]] = [
    # WICHTIG: Lass immer nur EIN Modell unkommentiert (ohne '#'). 
    # Wenn ein Lauf (600 Prompts) fertig ist, kommentierst du es aus und nimmst das naechste.

    # 1. Meta (BEREITS ERLEDIGT)
    # (Provider.OPENROUTER, "meta-llama/llama-3.1-8b-instruct"),
    
    # 2. Microsoft (Dein aktueller Lauf - Geändert auf Phi-4 da Phi-3 offline ist)
    # (Provider.OPENROUTER, "microsoft/phi-4"),
    
    # 3. Google (Open-Weights Modell, super Vergleich zu Llama)
    # (Provider.OPENROUTER, "google/gemma-2-9b-it"),
    
    # 4. OpenAI (Der Industrie-Standard fuer Agenten)
    (Provider.OPENROUTER, "openai/gpt-4o-mini"),
]

CONCURRENCY: int = 1 # Etwas gedrosselt für die Free-Tier Limits

RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request builder
# ---------------------------------------------------------------------------

def build_requests(
    provider: Provider,
    model: str,
    run_id: str,
) -> List[LLMRequest]:
    """
    Expand ALL_VARIANTS x N_REPETITIONS into a flat list of LLMRequest objects.

    Each request carries metadata for downstream joining:
        run_id, scenario_id, variant_id, variant_type, provider, model, rep_index
    """
    requests = []
    for scenario_id, variant_id, variant in ALL_VARIANTS:
        for rep in range(N_REPETITIONS):
            requests.append(LLMRequest(
                system_prompt=variant.system_prompt,
                user_prompt=variant.user_prompt,
                provider=provider,
                model=model,
                temperature=0.9,
                max_tokens=512,
                metadata={
                    "run_id":       run_id,
                    "scenario_id":  scenario_id,
                    "variant_id":   variant_id,
                    "variant_type": variant.variant_type,
                    "stressor":     variant.stressor_label,
                    "provider":     provider.value,
                    "model":        model,
                    "rep_index":    rep,
                },
            ))
    return requests


# ---------------------------------------------------------------------------
# Result persistence
# ---------------------------------------------------------------------------

def save_response(response: LLMResponse, output_dir: Path) -> None:
    """Append a single response as a JSON line to the appropriate .jsonl file."""
    meta = response.request_metadata
    filename = f"{meta['variant_id']}_{meta['provider']}_{meta['model'].replace('/', '-')}.jsonl"
    filepath = output_dir / filename

    record = {
        "run_id":           meta.get("run_id"),
        "scenario_id":      meta.get("scenario_id"),
        "variant_id":       meta.get("variant_id"),
        "variant_type":     meta.get("variant_type"),
        "stressor":         meta.get("stressor"),
        "provider":         response.provider,
        "model":            response.model,
        "rep_index":        meta.get("rep_index"),
        "content":          response.content,
        "prompt_tokens":    response.prompt_tokens,
        "completion_tokens":response.completion_tokens,
        "latency_ms":       response.latency_ms,
        "success":          response.success,
        "error":            response.error,
        "timestamp_utc":    datetime.now(timezone.utc).isoformat(),
    }

    with open(filepath, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_experiment() -> str:
    """
    Execute the full benchmark experiment across all providers and variants.

    Returns:
        run_id (str): Unique identifier for this experimental run.
    """
    run_id    = str(uuid.uuid4())[:8]
    run_dir   = RAW_DATA_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_start = time.time()

    logger.info(f"=== Experiment run {run_id} starting ===")
    logger.info(f"  Variants       : {len(ALL_VARIANTS)}")
    logger.info(f"  Repetitions    : {N_REPETITIONS}")
    logger.info(f"  Target models  : {[(p.value, m) for p, m in TARGET_MODELS]}")
    logger.info(f"  Total requests : "
                f"{len(ALL_VARIANTS) * N_REPETITIONS * len(TARGET_MODELS)}")
    logger.info(f"  Output dir     : {run_dir}")

    manifest = {
        "run_id":        run_id,
        "run_start_utc": datetime.now(timezone.utc).isoformat(),
        "n_repetitions": N_REPETITIONS,
        "target_models": [{"provider": p.value, "model": m}
                          for p, m in TARGET_MODELS],
        "n_variants":    len(ALL_VARIANTS),
        "total_requests": len(ALL_VARIANTS) * N_REPETITIONS * len(TARGET_MODELS),
        "provider_runs":  [],
    }

    async with AsyncLLMClient() as client:
        for provider, model in TARGET_MODELS:
            logger.info(f"--- Running {provider.value} / {model} ---")
            requests     = build_requests(provider, model, run_id)
            provider_start = time.time()

            # Wrap batch_query with tqdm progress bar
            semaphore = asyncio.Semaphore(CONCURRENCY)
            responses: List[LLMResponse] = []

            async def _bounded_query(req: LLMRequest) -> LLMResponse:
                async with semaphore:
                    try:
                        resp = await client.query(req)
                        if req.provider.value == "gemini":
                            import asyncio
                            await asyncio.sleep(4.1)
                        return resp
                    except Exception as exc:
                        logger.error(f"Final failure for {req.metadata['variant_id']}: {exc}")
                        return LLMResponse(
                            provider=req.provider.value,
                            model=req.model or "",
                            content="",
                            prompt_tokens=0,
                            completion_tokens=0,
                            latency_ms=0.0,
                            request_metadata=req.metadata,
                            raw_response={},
                            error=str(exc),
                            success=False,
                        )

            tasks = [_bounded_query(r) for r in requests]
            for coro in async_tqdm.as_completed(
                tasks,
                total=len(tasks),
                desc=f"{provider.value}/{model}",
                unit="req",
            ):
                resp = await coro
                responses.append(resp)
                save_response(resp, run_dir)

            provider_elapsed = time.time() - provider_start
            successes = sum(1 for r in responses if r.success)
            failures  = len(responses) - successes

            logger.info(
                f"  {provider.value}/{model}: "
                f"{successes} ok, {failures} failed "
                f"in {provider_elapsed:.1f}s"
            )

            manifest["provider_runs"].append({
                "provider":        provider.value,
                "model":           model,
                "n_requests":      len(requests),
                "n_success":       successes,
                "n_failure":       failures,
                "elapsed_seconds": round(provider_elapsed, 2),
            })

    manifest["run_end_utc"]       = datetime.now(timezone.utc).isoformat()
    manifest["total_elapsed_sec"] = round(time.time() - run_start, 2)

    manifest_path = run_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    logger.info(f"=== Run {run_id} complete in "
                f"{manifest['total_elapsed_sec']}s ===")
    logger.info(f"Manifest saved: {manifest_path}")
    return run_id


if __name__ == "__main__":
    run_id = asyncio.run(run_experiment())
    print(f"\nRun ID: {run_id}")
    print(f"Raw data: {RAW_DATA_DIR / run_id}")
