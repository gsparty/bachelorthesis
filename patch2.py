with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

old_func = """            async def _bounded_query(req: LLMRequest) -> LLMResponse:
                async with semaphore:
                    try:
                        return await client.query(req)
                    except Exception as exc:"""

new_func = """            async def _bounded_query(req: LLMRequest) -> LLMResponse:
                async with semaphore:
                    try:
                        resp = await client.query(req)
                        if req.provider.value == "gemini":
                            import asyncio
                            await asyncio.sleep(4.1)
                        return resp
                    except Exception as exc:"""

data = data.replace(old_func, new_func)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Drosselung für Gemini erfolgreich eingebaut!")
