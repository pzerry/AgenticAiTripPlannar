import asyncio

from Backend.LLM.factory import get_llm


PROVIDER = "openrouter_analyzer"
# PROVIDER = "ollama_qwen3"


async def main():
    llm = get_llm(PROVIDER)

    prompt = "Explain in 2 sentences why nonstop flights can be convenient."

    try:
        response = await llm.ainvoke(prompt)

        print("Provider:", PROVIDER)
        print("\nPrompt:")
        print(prompt)

        print("\nAnswer:")
        print(response.content)

    except Exception as exc:
        print("FAILED")
        print("Provider:", PROVIDER)
        print("Error type:", type(exc).__name__)
        print("Error:", exc)


asyncio.run(main())