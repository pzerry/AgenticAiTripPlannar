import os

from dotenv import load_dotenv

load_dotenv()


class Env:

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    SERPAPI_KEY = os.getenv("SERP_API_KEY")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
    AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENROUTERN_API_KEY = os.getenv("OPENROUTERN_API_KEY")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    OPENROUTERNIT_API_KEY = os.getenv("OPENROUTERNIT_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

env = Env()