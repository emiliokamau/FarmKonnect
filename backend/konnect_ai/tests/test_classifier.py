"""Tests for KonnectAI intent classification and confidence gating."""

from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from konnect_ai.classifier import classify_intent, _fallback_rule_classifier
from konnect_ai.agent import run_turn
from konnect_ai.models import ConversationSession
from konnect_ai.gemini import GeminiClient

User = get_user_model()


class ClassifierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="farmer_test", phone="+254711223344")
        self.session = ConversationSession.objects.create(user=self.user, modality="text")

    def test_fixed_messages_fms(self):
        """FMS agricultural queries should classify as FMS."""
        fms_queries = [
            "I planted 2 acres of maize in the north field",
            "There are yellow spots and disease on my potato leaves",
            "We finished harvesting 50 bags of beans today",
            "How much fertilizer should I apply on my farm?",
        ]
        for query in fms_queries:
            result = _fallback_rule_classifier(query, page="dashboard")
            self.assertEqual(result["intent"], "FMS", f"Failed for query: {query}")
            self.assertGreaterEqual(result["confidence"], 0.6)

    def test_fixed_messages_pos(self):
        """POS sales and commerce queries should classify as POS."""
        pos_queries = [
            "I sold 5 bags of maize to customer Peter for 15000",
            "Record a sale of 10 trays of eggs",
            "Bought 3 sacks of animal feed from supplier",
            "Check low stock products in my store",
        ]
        for query in pos_queries:
            result = _fallback_rule_classifier(query, page="pos")
            self.assertEqual(result["intent"], "POS", f"Failed for query: {query}")
            self.assertGreaterEqual(result["confidence"], 0.6)

    def test_fixed_messages_general(self):
        """Greetings and broad help queries should classify as GENERAL."""
        general_queries = [
            "Hello, what can you do for me?",
            "Habari ya leo nisaidie",
            "Hi FarmKonnect",
        ]
        for query in general_queries:
            result = _fallback_rule_classifier(query, page="dashboard")
            self.assertEqual(result["intent"], "GENERAL", f"Failed for query: {query}")

    def test_page_prior_bias(self):
        """Ambiguous term leans POS on pos.html and FMS on dashboard.html."""
        ambiguous_text = "Check the counter receipts"
        pos_res = _fallback_rule_classifier(ambiguous_text, page="pos")
        self.assertEqual(pos_res["intent"], "POS")

        ambiguous_crop = "Check the field records"
        fms_res = _fallback_rule_classifier(ambiguous_crop, page="dashboard")
        self.assertEqual(fms_res["intent"], "FMS")

    def test_gemini_classification_mock(self):
        """Gemini classifier parses structured JSON response properly."""
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.generate.return_value = '{"intent": "FMS", "confidence": 0.95, "reason": "Planting activity detected."}'

        res = classify_intent("I planted carrots", page="dashboard", gemini_client=mock_gemini)
        self.assertEqual(res["intent"], "FMS")
        self.assertAlmostEqual(res["confidence"], 0.95)
        self.assertEqual(res["reason"], "Planting activity detected.")

    def test_clear_intent_uses_local_classifier_when_preferred(self):
        mock_gemini = MagicMock(spec=GeminiClient)

        result = classify_intent(
            "I planted maize on my farm",
            page="dashboard",
            gemini_client=mock_gemini,
            prefer_local=True,
        )

        self.assertEqual(result["intent"], "FMS")
        mock_gemini.generate.assert_not_called()

    def test_low_confidence_triggers_clarification_no_tools(self):
        """Confidence < 0.6 must ask clarifying question and NOT execute tools."""
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.generate.return_value = '{"intent": "GENERAL", "confidence": 0.45, "reason": "Too ambiguous."}'

        with patch("konnect_ai.agent.execute_tool") as mock_exec:
            turn_res = run_turn(
                session=self.session,
                user_text_local="Record something for me",
                lang="en",
                page="dashboard",
                gemini_client=mock_gemini,
            )
            # Must ask clarification
            self.assertIn("farm management records or about a sale", turn_res["reply_en"])
            # Tool calls must be empty
            self.assertEqual(turn_res["tool_calls"], [])
            mock_exec.assert_not_called()
