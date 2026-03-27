import re

# 1. Update api_client.py
with open("src/api_client.py", "r", encoding="utf-8") as f:
    data = f.read()

data = data.replace("\"requests_per_minute\": 15", "\"requests_per_minute\": 10")

with open("src/api_client.py", "w", encoding="utf-8") as f:
    f.write(data)

# 2. Update experiment_runner.py
with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

data = re.sub(r"CONCURRENCY:\s*int\s*=\s*\d+", "CONCURRENCY: int = 1", data)

old_func = """            async def _bounded_query(req: LLMRequest) -> LLMResponse:
                async with semaphore:
                    return await client.query(req)"""

new_func = """            async def _bounded_query(req: LLMRequest) -> LLMResponse:
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
                        )"""

data = data.replace(old_func, new_func)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Die Dateien wurden erfolgreich gepatcht! Crash-Schutz ist aktiv.")
