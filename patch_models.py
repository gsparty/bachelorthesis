import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# 1. TARGET MODELS ersetzen
targets_pattern = re.compile(r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]", re.DOTALL)
new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    # WICHTIG: Lass immer nur EIN Modell unkommentiert (ohne '#'), um die APIs nicht zu überlasten!
    
    (Provider.GITHUB, "meta-llama-3.1-8b-instruct"),
    # (Provider.GITHUB, "gpt-4o-mini"),
    # (Provider.GITHUB, "Mistral-Nemo"),
    # (Provider.GEMINI, "gemini-2.5-flash"),
]"""
data = targets_pattern.sub(new_targets, data)

# 2. Die universelle Bremse in _bounded_query einbauen
func_pattern = re.compile(r"async def _bounded_query.*?return LLMResponse.*?\)\s*success=False,\s*\)", re.DOTALL)
new_func = """async def _bounded_query(req: LLMRequest) -> LLMResponse:
            async with semaphore:
                try:
                    resp = await client.query(req)
                    import asyncio
                    await asyncio.sleep(4.1) # Universelle Pause schuetzt vor allen Rate-Limits
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
                    )"""
data = func_pattern.sub(new_func, data)

# 3. Repetitions sicher auf 30 setzen
data = re.sub(r"N_REPETITIONS:\s*int\s*=\s*\d+", "N_REPETITIONS: int = 30", data)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Modell-Liste (Llama, GPT-4o-mini, Mistral, Gemini) und universelle Bremse erfolgreich eingerichtet!")
