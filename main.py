"""Start the local API; chat must pass through authentication and memory capture."""

import uvicorn


if __name__ == "__main__":
    # Calling the graph directly would bypass ownership and memory capture.
    # Use POST /travel/chat to run an authenticated conversation.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
