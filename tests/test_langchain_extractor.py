import json
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
from langchain_core.messages import AIMessage
from langchain_deepseek import ChatDeepSeek

from src.extractors.langchain_extractor import ExtractionError, LangChainExtractor
from src.models import Person, Sentiment, CompanyInfo, ProductInfo, ContactInfo


class LangChainExtractorTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test-key", "LLM_API_KEY": "",
            "LLM_MODEL": "deepseek-flash", "LLM_BASE_URL": "https://api.deepseek.com",
            "LLM_MAX_TOKENS": "8192",
        })
        env.start()
        self.addCleanup(env.stop)

    def make_extractor(self, llm=None):
        if llm is None:
            llm = MagicMock()
        with patch("src.extractors.langchain_extractor.ChatDeepSeek", return_value=llm) as constructor:
            extractor = LangChainExtractor()
        constructor.assert_called_once()
        self.assertEqual(constructor.call_args.kwargs["api_key"], "test-key")
        self.assertEqual(constructor.call_args.kwargs["max_tokens"], 8192)
        return extractor, llm

    @staticmethod
    def output(content, finish_reason="stop"):
        return {
            "raw": AIMessage(content=content, response_metadata={"finish_reason": finish_reason}),
            "parsed": None,
            "parsing_error": None,
        }

    def valid_person(self):
        return json.dumps({"items": [{"full_name": "张明", "job_title": "工程师", "company_name": None}]})

    def test_json_output_validated_and_source_language_preserved(self):
        extractor, llm = self.make_extractor()
        llm.with_structured_output.return_value.invoke.return_value = self.output(self.valid_person())
        result = extractor.extract("张明\n工程师", Person)
        self.assertEqual(result[0].full_name, "张明")
        self.assertEqual(result[0].job_title, "工程师")
        self.assertIsNone(result[0].company_name)
        self.assertAlmostEqual(result[0].confidence, 2 / 3)
        kwargs = llm.with_structured_output.call_args.kwargs
        self.assertEqual(kwargs["method"], "json_mode")
        self.assertTrue(kwargs["include_raw"])
        self.assertNotIn("strict", kwargs)

    def test_all_model_instructions_and_schema_descriptions_are_english(self):
        extractor, _ = self.make_extractor()
        for model in (Person, Sentiment, CompanyInfo, ProductInfo, ContactInfo):
            with self.subTest(model=model.__name__):
                messages = extractor._get_or_create_prompt_template(model).invoke({"text": "OCR_SAMPLE"}).to_messages()
                self.assertTrue(all(message.content.isascii() for message in messages))
                self.assertIn("JSON Schema", messages[0].content)
                self.assertIn("do not translate", messages[0].content)
                self.assertIn("Example JSON", messages[0].content)

    def test_blank_output_retries_once_then_succeeds(self):
        extractor, llm = self.make_extractor()
        invoke = llm.with_structured_output.return_value.invoke
        invoke.side_effect = [self.output("   "), self.output(self.valid_person())]
        self.assertEqual(extractor.extract("张明", Person)[0].full_name, "张明")
        self.assertEqual(invoke.call_count, 2)

    def test_bad_outputs_fail_after_one_retry_without_rule_fallback(self):
        invalid_cases = [
            ("   ", "stop"),
            (self.valid_person(), "length"),
            ('{"items": [', "stop"),
            ('{"items": [{"full_name": 12, "job_title": null, "company_name": null}]}', "stop"),
            ('{"items": [{"full_name": "张明"}]}', "stop"),
            ('{"items": [], "unexpected": true}', "stop"),
        ]
        for content, finish_reason in invalid_cases:
            with self.subTest(content=content, finish_reason=finish_reason):
                extractor, llm = self.make_extractor()
                invoke = llm.with_structured_output.return_value.invoke
                invoke.return_value = self.output(content, finish_reason)
                with patch.object(extractor, "_heuristic_extraction") as fallback:
                    with self.assertRaisesRegex(ExtractionError, "已重试一次"):
                        extractor.extract("张明\n工程师", Person)
                    fallback.assert_not_called()
                self.assertEqual(invoke.call_count, 2)

    def test_sentiment_rejects_invalid_enum_and_score(self):
        for label, score in (("happy", 0.8), ("positive", 2.0)):
            with self.subTest(label=label, score=score):
                extractor, llm = self.make_extractor()
                llm.with_structured_output.return_value.invoke.return_value = self.output(json.dumps({
                    "items": [{"sentiment": label, "confidence_score": score, "keywords": ["good"]}]
                }))
                with self.assertRaises(ExtractionError):
                    extractor.extract("good", Sentiment)

    def test_empty_record_list_is_valid(self):
        extractor, llm = self.make_extractor()
        llm.with_structured_output.return_value.invoke.return_value = self.output('{"items": []}')
        self.assertEqual(extractor.extract("No relevant records", Person), [])

    def test_provider_failure_is_sanitized(self):
        extractor, llm = self.make_extractor()
        llm.with_structured_output.return_value.invoke.side_effect = RuntimeError("private source or test-key")
        with self.assertRaises(ExtractionError) as caught:
            extractor.extract("private source", Person)
        self.assertNotIn("private source", str(caught.exception))
        self.assertNotIn("test-key", str(caught.exception))

    def test_no_key_keeps_heuristic_mode(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "", "LLM_API_KEY": ""}):
            extractor = LangChainExtractor()
        self.assertEqual(extractor.extract("Ada\nEngineer\nExample Inc", Person)[0].full_name, "Ada")

    def test_real_langchain_adapter_sends_json_object_without_tools(self):
        captured = []

        def handle(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "test-completion", "object": "chat.completion", "created": 1,
                "model": "deepseek-flash",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": self.valid_person(),
                }}],
            })

        with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
            model = ChatDeepSeek(model="deepseek-flash", api_key="test-key", http_client=http_client)
            extractor, _ = self.make_extractor(model)
            self.assertEqual(extractor.extract("张明\n工程师", Person)[0].full_name, "张明")
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["response_format"], {"type": "json_object"})
        self.assertNotIn("tools", captured[0])
        self.assertNotIn("tool_choice", captured[0])


if __name__ == "__main__":
    unittest.main()
