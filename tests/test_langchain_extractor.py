import os
import unittest
from unittest.mock import MagicMock, patch

from src.extractors.langchain_extractor import LangChainExtractor
from src.models.person import Person


class LangChainExtractorTests(unittest.TestCase):
    def make_extractor(self, llm):
        env = patch.dict(os.environ, {"LLM_API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)
        chat_openai = patch(
            "src.extractors.langchain_extractor.ChatOpenAI",
            return_value=llm,
        )
        mocked_chat_openai = chat_openai.start()
        self.addCleanup(chat_openai.stop)
        extractor = LangChainExtractor()
        mocked_chat_openai.assert_called_once()
        return extractor

    def test_structured_output_consumes_pydantic_items(self):
        llm = MagicMock()
        extractor = self.make_extractor(llm)
        list_model = extractor._get_or_create_list_model(Person)
        expected = Person(full_name="Ada Lovelace", job_title="Engineer")
        llm.with_structured_output.return_value.invoke.return_value = list_model(
            items=[expected]
        )

        result = extractor.extract("# Ada Lovelace\nEngineer", Person)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].full_name, "Ada Lovelace")
        self.assertEqual(result[0].job_title, "Engineer")
        self.assertGreater(result[0].confidence, 0)
        kwargs = llm.with_structured_output.call_args.kwargs
        self.assertIs(kwargs["schema"], list_model)
        self.assertEqual(kwargs["method"], "function_calling")

    def test_structured_output_failure_uses_heuristic_fallback(self):
        llm = MagicMock()
        llm.with_structured_output.return_value.invoke.side_effect = RuntimeError(
            "mocked LLM failure"
        )
        extractor = self.make_extractor(llm)

        result = extractor.extract(
            "# Ada Lovelace\n# Engineer\n# Example Inc",
            Person,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].full_name, "Ada Lovelace")
        self.assertEqual(result[0].job_title, "Engineer")
        self.assertEqual(result[0].company_name, "Example Inc")


if __name__ == "__main__":
    unittest.main()
