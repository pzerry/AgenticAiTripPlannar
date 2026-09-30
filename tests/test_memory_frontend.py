"""Exercise the real Streamlit UI with a mocked HTTP client, without a server."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import requests
from streamlit.testing.v1 import AppTest


class FrontendMemoryTests(unittest.TestCase):
    def setUp(self):
        self.user_id = str(uuid4())
        self.api = SimpleNamespace(chat=Mock(), current_user=Mock(return_value={"user_id": self.user_id}),
                                   saved_memories=Mock(return_value=[]), forget_memory=Mock())
        self.modules = patch.dict(sys.modules, {"api": self.api})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "FrontEnd" / "app.py"))
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def connect(self, token="test-token"):
        self.app.text_input(key="token_input").set_value(token)
        self.button("Connect").click().run()
        self.assertEqual(len(self.app.exception), 0)

    def test_login_and_timeout_retry_keep_one_message_id(self):
        self.assertEqual(len(self.app.chat_input), 0)
        self.connect()
        self.api.chat.side_effect = requests.Timeout()
        self.app.chat_input[0].set_value("Plan a trip").run()
        self.assertEqual(len(self.app.exception), 0)
        original = self.api.chat.call_args.kwargs
        self.assertEqual(original["token"], "test-token")
        self.assertTrue(self.app.chat_input[0].disabled)
        self.api.chat.side_effect = None
        self.api.chat.return_value = {"thread_id": original["thread_id"], "message_id": original["message_id"],
                                      "response": "Where would you like to go?", "interrupted": True,
                                      "memory_status": "pending"}
        self.button("Retry message").click().run()
        self.assertEqual(self.api.chat.call_args.kwargs, original)
        self.assertFalse(self.app.chat_input[0].disabled)
        conversation = self.app.session_state["conversations"][original["thread_id"]]
        self.assertEqual([m["role"] for m in conversation["messages"]], ["user", "assistant"])
        self.assertTrue(conversation["waiting_for_clarification"])

    def test_switching_account_clears_old_conversations(self):
        self.connect()
        previous_thread = self.app.session_state["active_chat_id"]
        self.api.current_user.return_value = {"user_id": str(uuid4())}
        self.connect("different-token")
        self.assertNotIn(previous_thread, self.app.session_state["conversations"])

    def test_failed_forget_retries_same_deletion_id(self):
        self.connect()
        self.api.saved_memories.return_value = [{"memory_key": "preferred_hotel_class", "memory_value": "4_star"}]
        self.button("Refresh preferences").click().run()
        self.api.forget_memory.side_effect = requests.Timeout()
        self.button("Forget").click().run()
        original = self.api.forget_memory.call_args
        self.api.forget_memory.side_effect = None
        self.api.saved_memories.return_value = []
        self.button("Forget").click().run()
        self.assertEqual(self.api.forget_memory.call_args, original)
        self.assertEqual(self.app.session_state["saved_memories"], [])
