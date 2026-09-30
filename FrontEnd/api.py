"""HTTP client for the Streamlit UI; retry IDs are created by the caller."""

import requests

from config import API_URL


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def current_user(token: str) -> dict:
    response = requests.get(f"{API_URL}/travel/me", headers=headers(token), timeout=15)
    response.raise_for_status()
    return response.json()


def chat(*, token: str, thread_id: str, message: str, message_id: str) -> dict:
    # Reuse message_id after a timeout. The server may already have completed
    # the turn even though the browser did not receive its response.
    response = requests.post(
        f"{API_URL}/travel/chat", headers=headers(token),
        json={"thread_id": thread_id, "message": message, "message_id": message_id},
        # Allow up to ten minutes while debugging long-running planner turns.
        # A timeout still retries the same message ID to recover its result.
        timeout=600,
    )
    response.raise_for_status()
    return response.json()


def saved_memories(token: str) -> list:
    response = requests.get(f"{API_URL}/travel/memories", headers=headers(token), timeout=15)
    response.raise_for_status()
    return response.json()["memories"]


def forget_memory(token: str, memory_key: str, request_id: str) -> None:
    response = requests.delete(f"{API_URL}/travel/memories/{memory_key}",
        headers=headers(token) | {"Idempotency-Key": request_id}, timeout=15)
    response.raise_for_status()
