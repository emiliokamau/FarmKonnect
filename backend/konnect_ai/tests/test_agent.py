"""Tests for KonnectAI full conversational agent turn orchestrator."""

from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model

from core_up.models import FarmerProfile, Farm, Sale
from konnect_ai.agent import run_turn, detect_language
from konnect_ai.models import ConversationSession, AuditLog
from konnect_ai.gemini import GeminiClient

User = get_user_model()


class AgentTurnTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="farmer_mwangi",
            phone="+254712345678",
            is_phone_verified=True,
        )
        self.profile = FarmerProfile.objects.create(
            user=self.user,
            full_name="Mwangi Kamau",
            county="Kiambu",
        )
        self.farm = Farm.objects.create(
            farmer=self.profile,
            name="Kiambu Shamba",
            size=3.0,
        )
        self.session = ConversationSession.objects.create(
            user=self.user,
            modality="text",
            language="auto",
        )

    def test_detect_language_swahili_and_english(self):
        """detect_language should accurately distinguish Swahili and English."""
        self.assertEqual(detect_language("Nimeuza mahindi gunia tano"), "sw")
        self.assertEqual(detect_language("Habari ya asubuhi, nisaidie"), "sw")
        self.assertEqual(detect_language("I planted 3 acres of beans today"), "en")
        self.assertEqual(detect_language("Show me the weather forecast"), "en")

    @patch("konnect_ai.agent.send_sms")
    def test_full_turn_integration_pos_with_sms(self, mock_send_sms):
        """User records a sale -> POS intent -> record_sale tool -> SMS sent -> reply."""
        mock_send_sms.return_value = {"ok": True, "provider": "textsms"}

        mock_gemini = MagicMock(spec=GeminiClient)
        # 1. Translate Swahili to English
        mock_gemini.translate.return_value = "I sold 5 bags of potatoes for 10000 shillings"
        # 2. Classifier output
        mock_gemini.generate.return_value = '{"intent": "POS", "confidence": 0.95, "reason": "Sale recorded."}'
        # 3. Chat tool calling
        mock_gemini.chat.return_value = (
            "Recorded sale of 5 bags of potatoes for KES 10,000.",
            [
                {
                    "name": "record_sale",
                    "args": {
                        "product": "Potatoes",
                        "quantity": 5,
                        "unit": "bags",
                        "price": 2000,
                        "customer": "Market Buyer",
                        "payment_method": "cash",
                        "confirm": True,
                    },
                }
            ],
        )

        turn = run_turn(
            session=self.session,
            user_text_local="Nimeuza magunia 5 ya viazi kwa shilingi elfu kumi",
            lang="sw",
            page="pos",
            gemini_client=mock_gemini,
        )

        # Check turn results
        self.assertEqual(turn["intent"], "POS")
        self.assertIn("Recorded sale of", turn["reply_en"])
        self.assertTrue(turn["sms_sent"])
        self.assertEqual(len(turn["tool_calls"]), 1)
        self.assertTrue(turn["tool_calls"][0]["ok"])

        # Check DB record created
        self.assertTrue(Sale.objects.filter(farmer=self.profile, product="Potatoes").exists())

        # Check SMS dispatched to user phone
        mock_send_sms.assert_called_once()
        call_args = mock_send_sms.call_args[0]
        self.assertEqual(call_args[0], "+254712345678")

        # Check audit log was written
        self.assertTrue(
            AuditLog.objects.filter(user=self.user, tool_name="record_sale", ok=True).exists()
        )

    def test_tool_backed_reply_uses_database_result_not_model_claim(self):
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.chat.return_value = (
            "You have 99 farms.",
            [{"name": "list_farms", "args": {}}],
        )
        self.session.transcript = [
            {"role": "user", "text": "Hello"},
            {"role": "assistant", "text": "How can I help?"},
        ]
        self.session.save(update_fields=["transcript"])

        turn = run_turn(
            session=self.session,
            user_text_local="Show me my farms",
            lang="en",
            page="dashboard",
            gemini_client=mock_gemini,
        )

        self.assertIn("Kiambu Shamba", turn["reply_en"])
        self.assertNotIn("99", turn["reply_en"])
        self.assertEqual(
            mock_gemini.chat.call_args.kwargs["history"],
            self.session.transcript[:2],
        )

    def test_personal_data_question_without_read_tool_does_not_guess(self):
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.chat.return_value = ("You have 12 farms.", [])

        turn = run_turn(
            session=self.session,
            user_text_local="How many farms do I have?",
            lang="en",
            page="dashboard",
            gemini_client=mock_gemini,
        )

        self.assertIn("can't verify", turn["reply_en"])
        self.assertNotIn("12", turn["reply_en"])

    def test_language_roundtrip_swahili(self):
        """Swahili input should return localized Swahili reply."""
        mock_gemini = MagicMock(spec=GeminiClient)
        mock_gemini.translate.side_effect = lambda text, src, tgt: (
            "Hello, how can I assist you with your farm?" if tgt == "en"
            else "Habari, nawezaje kukusaidia na shamba lako?"
        )
        mock_gemini.generate.return_value = '{"intent": "GENERAL", "confidence": 0.9, "reason": "Greeting."}'
        mock_gemini.chat.return_value = ("Hello, how can I assist you with your farm?", [])

        turn = run_turn(
            session=self.session,
            user_text_local="Habari, unaweza kunisaidiaje leo?",
            lang="sw",
            page="dashboard",
            gemini_client=mock_gemini,
        )

        self.assertEqual(self.session.language, "sw")
        self.assertIn("Habari", turn["reply"])
