from langchain_google_genai import ChatGoogleGenerativeAI
from openai import base_url

from Backend.Config.env import env

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from Backend.Config.loader import load_config
from Backend.Exceptions import ConfigurationError

config = load_config()


def get_llm(provider: str | None = None):
    provider = (
        provider
        or config["llm"].get("provider")
        or config["llm"].get("default_provider")
    )

    providers = config["llm"]["providers"]

    
    if provider == "ollama_qwen3":
        cfg = providers["ollama_qwen3"]

        return ChatOllama(
            model=cfg["model"],
            base_url=cfg["base_url"],
            temperature=cfg.get("temperature", 0.0),
            num_ctx=cfg.get("num_ctx", 8192),
            keep_alive=cfg.get("keep_alive", "30m"),
        )



    elif provider == "groq":
            cfg = providers["groq"]
    
            return ChatGroq(
                model=cfg["model"],
                api_key=env.GROQ_API_KEY,
                temperature=cfg.get("temperature", 0.0),
                max_tokens=cfg.get("max_tokens"),
                timeout=cfg.get("timeout", 60),
                max_retries=cfg.get("max_retries", 2),
            )


    elif provider in ("openrouter_analyzer", "openrouter_minimax"):
        cfg = providers[provider]

        return ChatOpenAI(
            model=cfg["model"],
            api_key=env.OPENROUTERNIT_API_KEY,
            base_url=cfg.get(
                "base_url",
                "https://openrouter.ai/api/v1",
            ),
            temperature=cfg.get(
                "temperature",
                0.1,
            ),
            max_tokens=cfg.get(
                "max_tokens",
                4098,
            ),
            timeout=cfg.get(
                "timeout",
                60,
            ),
            max_retries=cfg.get(
                "max_retries",
                2,
            ),
            extra_body={
                            "reasoning": {
                                "effort": cfg.get(
                                    "reasoning_effort",
                                    "low",
                                )
                            }
                        },
            default_headers={
                "HTTP-Referer": cfg.get(
                    "referer",
                    "http://localhost",
                ),
                "X-Title": cfg.get(
                    "title",
                    "Travel Planner Analyzer",
                ),
            },
        )
        
    raise ConfigurationError(f"Unsupported provider: {provider}")
