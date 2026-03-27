import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# 1. Die kugelsichere Bremse (finally block) einbauen
func_pattern = re.compile(r"async def _bounded_query.*?return LLMResponse.*?\)\s*success=False,\s*\)", re.DOTALL)
new_func = """async def _bounded_query(req: LLMRequest) -> LLMResponse:
            async with semaphore:
                try:
                    return await client.query(req)
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
                finally:
                    import asyncio
                    await asyncio.sleep(4.1) # Diese Bremse greift IMMER, auch bei Fehlern!"""
data = func_pattern.sub(new_func, data)

# 2. Saubere Modell-Liste (Gemma aktiviert, OpenRouter als Fallback)
targets_pattern = re.compile(r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]", re.DOTALL)
new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    # --- ALTERNATIVE A: Google Gemma 2 (Extrem hohes Tageslimit, Open-Source) ---
    (Provider.GEMINI, "gemma-2-9b-it"),
    
    # --- ALTERNATIVE C: OpenRouter (Llama 3.1 Kostenlos - für später) ---
    # (Provider.OPENROUTER, "meta-llama/llama-3.1-8b-instruct:free"),
]"""
data = targets_pattern.sub(new_targets, data)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Kugelsichere Bremse aktiv & Google Gemma-2 ist als Ziel konfiguriert!")
