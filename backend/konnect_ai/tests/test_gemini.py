from unittest.mock import Mock, patch
import requests

from django.test import SimpleTestCase

from konnect_ai.gemini import GeminiClient


class GeminiClientTests(SimpleTestCase):
    def test_offline_fallback_never_invents_or_executes_a_write(self):
        client = GeminiClient(api_key="")

        reply, tool_calls = client._fallback_chat(
            user="yes",
            context="Farmer in Nakuru",
            tools=[],
            intent="POS",
        )

        self.assertIn("AI service is unavailable", reply)
        self.assertEqual(tool_calls, [])

    @patch("konnect_ai.gemini.time.sleep")
    @patch("konnect_ai.gemini.requests.post")
    def test_exhausted_project_quota_is_not_retried(self, mock_post, mock_sleep):
        exhausted = Mock(status_code=429)
        exhausted.json.return_value = {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "message": "You exceeded your current quota.",
            }
        }
        exhausted.raise_for_status.side_effect = requests.HTTPError(response=exhausted)
        mock_post.return_value = exhausted
        client = GeminiClient(api_key="test-secret", model="test-model")

        client.generate("Give a watering tip")

        self.assertEqual(mock_post.call_count, 1)
        mock_sleep.assert_not_called()
    @patch("konnect_ai.gemini.time.sleep")
    @patch("konnect_ai.gemini.requests.post")
    def test_generate_uses_api_key_header_and_retries_overload(self, mock_post, mock_sleep):
        overloaded = Mock(status_code=503)
        overloaded.raise_for_status.side_effect = Exception("should not raise before retry")
        successful = Mock(status_code=200)
        successful.raise_for_status.return_value = None
        successful.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Water at the roots."}]}}]
        }
        mock_post.side_effect = [overloaded, successful]
        client = GeminiClient(api_key="test-secret", model="test-model")

        result = client.generate("Give a watering tip")

        self.assertEqual(result, "Water at the roots.")
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)
        request_url = mock_post.call_args.args[0]
        request_headers = mock_post.call_args.kwargs["headers"]
        self.assertNotIn("test-secret", request_url)
        self.assertEqual(request_headers["x-goog-api-key"], "test-secret")

    @patch("konnect_ai.gemini.time.sleep")
    @patch("konnect_ai.gemini.requests.post")
    def test_chat_uses_api_key_header(self, mock_post, mock_sleep):
        successful = Mock(status_code=200)
        successful.raise_for_status.return_value = None
        successful.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Water early in the morning."}]}}]
        }
        mock_post.return_value = successful
        client = GeminiClient(api_key="test-secret", model="test-model")

        reply, calls = client.chat(
            system="You are a farm assistant.",
            history=[],
            user="How should I water tomatoes?",
            context="Farmer in Kiambu.",
            tools=[],
            intent="FMS",
        )

        self.assertEqual(reply, "Water early in the morning.")
        self.assertEqual(calls, [])
        request_url = mock_post.call_args.args[0]
        request_headers = mock_post.call_args.kwargs["headers"]
        self.assertNotIn("test-secret", request_url)
        self.assertEqual(request_headers["x-goog-api-key"], "test-secret")