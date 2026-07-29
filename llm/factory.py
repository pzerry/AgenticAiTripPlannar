import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from Config.loader import load_config
from Exceptions import ConfigurationError

load_dotenv()

config = load_config()

provider = config["llm"]["provider"]

if provider == "groq":

    groq_key = os.getenv("GROQ_API_KEY")

    if not groq_key:
        raise ConfigurationError("GROQ_API_KEY not found.")

    llm = ChatGroq(
        model=config["providers"]["groq"]["model"],
        api_key=groq_key,
        temperature=config["providers"]["groq"]["temperature"],
    )

elif provider == "openrouter":

    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not openrouter_key:
        raise ConfigurationError("OPENROUTER_API_KEY not found.")

    llm = ChatOpenAI(
        model=config["providers"]["openrouter"]["model"],
        api_key=openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=config["providers"]["openrouter"]["temperature"],
    )

else:
    raise ConfigurationError(
        f"Unsupported provider: {provider}"
    )