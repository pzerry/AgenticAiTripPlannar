import os

# Separate UI/API containers reach each other by service name. Local usage
# keeps the existing localhost default.
API_URL = os.environ.get("TRAVEL_API_URL", "http://localhost:8000").rstrip("/")
