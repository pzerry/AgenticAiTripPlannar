import uuid

import requests
import streamlit as st

from api import chat

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ AI Travel Planner")
st.caption("Production Agentic AI Travel Planner")

# --------------------------------------------------
# Session State
# --------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "waiting_for_clarification" not in st.session_state:
    st.session_state.waiting_for_clarification = False

# --------------------------------------------------
# Render Chat History
# --------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --------------------------------------------------
# Chat Input
# --------------------------------------------------

if prompt := st.chat_input("Plan your next trip..."):

    # Show user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):

        with st.spinner("Planning your trip..."):

            try:

                response = chat(
                        thread_id=st.session_state.thread_id,
                        message=prompt,
                        interrupted=st.session_state.waiting_for_clarification,
                    )

                st.session_state.thread_id = response["thread_id"]

                st.session_state.waiting_for_clarification = response[
                    "interrupted"
                ]

                answer = response["response"]

                st.markdown(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except requests.exceptions.ConnectionError:

                st.error(
                    "Cannot connect to FastAPI server."
                )

            except requests.HTTPError as e:

                st.error(str(e))

            except Exception as e:

                st.error(str(e))