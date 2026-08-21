import requests

from config import API_URL


def chat(
    thread_id: str,
    message: str,
    interrupted: bool,
) -> dict:

    response = requests.post(
        f"{API_URL}/travel/chat",
        json={
            "thread_id": thread_id,
            "message": message,
            "interrupted": interrupted,
        },
        timeout=3000,
    )

    response.raise_for_status()

    return response.json()