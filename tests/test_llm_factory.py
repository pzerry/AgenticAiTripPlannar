import unittest
from unittest.mock import patch

from Backend.LLM import factory


class FactoryTests(unittest.TestCase):
    def test_memory_evaluation_provider_uses_its_own_configuration(self):
        config = {"llm": {"providers": {
            "openrouter_minimax": {"model": "test-memory-model", "max_tokens": 8192},
            "openrouter_analyzer": {"model": "test-analyzer-model"},
        }}}
        with patch.object(factory, "config", config), patch.object(factory, "ChatOpenAI") as client:
            result = factory.get_llm("openrouter_minimax")
        self.assertIs(result, client.return_value)
        self.assertEqual(client.call_args.kwargs["model"], "test-memory-model")
        self.assertEqual(client.call_args.kwargs["max_tokens"], 8192)
