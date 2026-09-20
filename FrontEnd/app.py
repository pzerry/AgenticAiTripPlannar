import re
import uuid

import requests
import streamlit as st

from api import chat, current_user, forget_memory, saved_memories

# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================
# STYLING
# ==========================================================

st.markdown(
    """
    <style>
        /* ---------- App ---------- */
        .stApp { background-color: #212121; }

        header[data-testid="stHeader"] {
            height: 2.5rem;
            background: transparent;
            visibility: visible !important;
        }

        button[data-testid="stSidebarCollapsedControl"] {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .block-container {
            max-width: 100%;
            padding-top: 0.2rem;
            padding-bottom: 5rem;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background-color: #171717;
            border-right: 1px solid #303030;
        }

        section[data-testid="stSidebar"] > div {
            padding: 1rem 0.8rem;
        }

        section[data-testid="stSidebar"] button {
            border-radius: 8px;
        }

        /* ---------- Chat ---------- */
        div[data-testid="stChatMessage"] {
            background: transparent;
            border: none;
        }

        /* ---------- Chat input ---------- */
        div[data-testid="stChatInput"] {
            max-width: 900px;
            margin: 0 auto;
        }

        div[data-testid="stChatInput"] textarea {
            background-color: #303030;
            color: white;
            border: 1px solid #444;
            border-radius: 14px;
        }

        /* ---------- Welcome ---------- */
        .welcome-box {
            text-align: center;
            padding-top: 16vh;
            padding-bottom: 8vh;
        }

        .welcome-icon {
            font-size: 58px;
            line-height: 1;
            margin-bottom: 18px;
        }

        .welcome-title {
            color: white;
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .welcome-subtitle {
            color: #9ca3af;
            font-size: 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# USER ID
# ==========================================================

# A random UUID is not authentication. Verify a bearer token with the API and
# keep that identity across new chats so long-term memory belongs to one user.
# This token form is for the development UI; production needs an OIDC sign-in.
with st.sidebar.expander("Connect account", expanded="user_id" not in st.session_state):
    access_token = st.text_input("Access token", type="password", key="token_input")
    if st.button("Connect"):
        try:
            identity = current_user(access_token)
            if st.session_state.get("user_id") != identity["user_id"]:
                # Do not show the previous account's conversation or preferences.
                for key in ("conversations", "active_chat_id", "saved_memories", "pending_deletions"):
                    st.session_state.pop(key, None)
            st.session_state.user_id = identity["user_id"]
            st.session_state.access_token = access_token
            st.rerun()
        except requests.RequestException:
            st.error("Could not connect. Check your token and the API server.")
    if st.session_state.get("user_id"):
        st.caption("Account connected")

if "user_id" not in st.session_state:
    st.info("Connect your account in the sidebar to start planning.")
    st.stop()

# ==========================================================
# SESSION STATE
# ==========================================================

if "conversations" not in st.session_state:
    st.session_state.conversations = {}

if "active_chat_id" not in st.session_state:
    chat_id = str(uuid.uuid4())

    st.session_state.conversations[chat_id] = {
        "thread_id": chat_id,
        "title": "New chat",
        "messages": [],
        "waiting_for_clarification": False,
    }

    st.session_state.active_chat_id = chat_id

# ==========================================================
# HELPERS
# ==========================================================


def get_active_chat():
    """Return the active conversation."""
    return st.session_state.conversations[st.session_state.active_chat_id]


def create_new_chat():
    """Create and activate a new conversation."""
    chat_id = str(uuid.uuid4())

    st.session_state.conversations[chat_id] = {
        "thread_id": chat_id,
        "title": "New chat",
        "messages": [],
        "waiting_for_clarification": False,
    }

    st.session_state.active_chat_id = chat_id


def make_title(text: str) -> str:
    """Create a short sidebar conversation title."""
    text = " ".join(text.split())

    if len(text) <= 32:
        return text

    return f"{text[:32].rstrip()}..."


def clean_response(text: str) -> str:
    """Remove accidental model reasoning from the final response."""
    if not text:
        return ""

    text = text.strip()

    reasoning_patterns = [
        r"thinking process\s*:?",
        r"reasoning\s*:?",
        r"chain of thought\s*:?",
        r"analysis\s*:?",
    ]

    for pattern in reasoning_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            text = text[match.end():].strip()
            break

    headings = [
        "### Recommended Trip",
        "## Recommended Trip",
        "### Currency Conversion",
        "## Currency Conversion",
        "### Flight",
        "## Flight",
    ]

    positions = [
        text.find(heading)
        for heading in headings
        if text.find(heading) >= 0
    ]

    if positions:
        first_heading = min(positions)
        prefix = text[:first_heading].lower()

        bad_prefixes = (
            "let's",
            "i will",
            "i'll",
            "thinking",
            "reasoning",
            "analysis",
            "i need to",
            "i should",
        )

        if any(phrase in prefix for phrase in bad_prefixes):
            text = text[first_heading:]

    return text.strip()


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.markdown("## ✈️ AI Travel Planner")
    st.caption("Your personal agentic travel assistant")

    with st.expander("Saved preferences"):
        st.caption("Preferences appear after background processing finishes.")
        if st.button("Refresh preferences"):
            try:
                st.session_state.saved_memories = saved_memories(st.session_state.access_token)
            except requests.RequestException:
                st.error("Could not load preferences. Check your connection or reconnect your account.")
        for memory in st.session_state.get("saved_memories", []):
            key = memory["memory_key"]
            st.write(f"{key.removeprefix('preferred_').replace('_', ' ').title()}: "
                     f"{memory['memory_value'].replace('_', ' ')}")
            if st.button("Forget", key=f"forget_{key}"):
                # Keep a failed deletion's ID too, so retry cannot accidentally
                # delete a newer preference the user supplied in another chat.
                pending = st.session_state.setdefault("pending_deletions", {})
                deletion_id = pending.setdefault(key, str(uuid.uuid4()))
                try:
                    forget_memory(st.session_state.access_token, key, deletion_id)
                    pending.pop(key)
                    st.session_state.saved_memories = saved_memories(st.session_state.access_token)
                    st.rerun()
                except requests.RequestException:
                    st.error("Deletion was not confirmed. Click Forget again to retry.")

    if st.button(
        "＋  New chat",
        use_container_width=True,
        type="primary",
    ):
        create_new_chat()
        st.rerun()

    st.markdown("---")
    st.caption("CONVERSATIONS")

    conversation_items = list(
        st.session_state.conversations.items()
    )

    conversation_items.reverse()

    for chat_id, conversation in conversation_items:
        title = conversation["title"]

        if chat_id == st.session_state.active_chat_id:
            title = f"● {title}"

        if st.button(
            title,
            key=f"conversation_{chat_id}",
            use_container_width=True,
        ):
            st.session_state.active_chat_id = chat_id
            st.rerun()


# ==========================================================
# ACTIVE CONVERSATION
# ==========================================================

conversation = get_active_chat()

# ==========================================================
# HEADER
# ==========================================================

st.markdown(f"### {conversation['title']}")

# ==========================================================
# CHAT HISTORY
# ==========================================================

messages = conversation["messages"]

if not messages:
    st.markdown(
        """
        <div class="welcome-box">
            <div class="welcome-icon">🌍</div>
            <div class="welcome-title">Where are you going?</div>
            <div class="welcome-subtitle">
                Plan a trip, find flights, hotels, activities,
                weather, or currency rates.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(
                message["content"],
                unsafe_allow_html=False,
            )

# ==========================================================
# CHAT INPUT
# ==========================================================

# Keep a pending message until the server confirms its response. Browser
# timeouts do not tell us whether the graph finished, so retries reuse the ID.
pending = conversation.get("pending_message")
prompt = st.chat_input("Message AI Travel Planner...", disabled=pending is not None)
retry = False
send_requested = False
if pending:
    st.info(conversation.get("last_error", "The previous response was not confirmed. Retry to recover it."))
    retry = st.button("Retry message")

if prompt and prompt.strip() and pending is None:
    prompt = prompt.strip()
    if not conversation["messages"]:
        conversation["title"] = make_title(prompt)
    conversation["messages"].append({"role": "user", "content": prompt})
    pending = {"message_id": str(uuid.uuid4()), "message": prompt}
    conversation["pending_message"] = pending
    send_requested = True
    with st.chat_message("user"):
        st.markdown(prompt, unsafe_allow_html=False)

if send_requested or retry:
    with st.chat_message("assistant"):
        try:
            with st.spinner("Planning your trip..."):
                response = chat(
                    token=st.session_state.access_token,
                    thread_id=conversation["thread_id"],
                    message=pending["message"],
                    message_id=pending["message_id"],
                )
            conversation["thread_id"] = response["thread_id"]
            conversation["waiting_for_clarification"] = response["interrupted"]
            conversation["memory_status"] = response["memory_status"]
            answer = clean_response(response.get("response", "")) or "I couldn't generate a response."
            conversation["messages"].append({"role": "assistant", "content": answer})
            conversation.pop("pending_message", None)
            conversation.pop("last_error", None)
            st.rerun()
        except requests.exceptions.ConnectionError:
            conversation["last_error"] = "Cannot connect to the API server. Your message is ready to retry."
        except requests.exceptions.Timeout:
            conversation["last_error"] = "The response timed out. Retry this message to recover its result."
        except requests.HTTPError as exc:
            if exc.response.status_code in (401, 403):
                conversation["last_error"] = "Your session expired. Reconnect your account, then retry."
            else:
                conversation["last_error"] = "The request could not finish. Retry the same message or start a new chat."
        except Exception:
            conversation["last_error"] = "The response was not confirmed. Retry the same message."
        # Re-render immediately with the input disabled and retry control shown.
        st.rerun()
