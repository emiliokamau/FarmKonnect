"""Tests for KonnectAI audit logging and PII masking compliance."""

from django.test import TestCase
from django.contrib.auth import get_user_model

from konnect_ai.audit import mask_pii, mask_phone, log_tool_call, check_rate_limit
from konnect_ai.models import AuditLog, ConversationSession

User = get_user_model()


class AuditLoggingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="audit_farmer",
            phone="+254722998877",
            is_phone_verified=True,
        )
        self.session = ConversationSession.objects.create(user=self.user)

    def test_mask_phone_shows_only_last_four_digits(self):
        """mask_phone should hide all digits except the last 4."""
        masked = mask_phone("+254722998877")
        self.assertTrue(masked.endswith("8877"))
        self.assertNotIn("72299", masked)

    def test_mask_pii_dictionary_recursive(self):
        """Sensitive fields like passwords, phones, and raw audio must be scrubbed."""
        raw_data = {
            "phone": "+254700112233",
            "password": "supersecretpassword123",
            "token": "abcdef1234567890",
            "audio_chunk": "UklGRi0AAABXQVZFZm10IBAAAAABAAEA",
            "farmer_name": "Kipchoge",
            "details": {
                "customer_phone": "0711223344",
                "notes": "Delivered to phone 0722334455 at market.",
            },
        }

        sanitized = mask_pii(raw_data)

        # Phone masked
        self.assertTrue(sanitized["phone"].endswith("2233"))
        self.assertNotIn("70011", sanitized["phone"])
        self.assertTrue(sanitized["details"]["customer_phone"].endswith("3344"))

        # Secret / Password masked
        self.assertEqual(sanitized["password"], "******")
        self.assertEqual(sanitized["token"], "******")

        # Audio binary omitted
        self.assertEqual(sanitized["audio_chunk"], "<binary_data_omitted>")

        # Non-sensitive kept
        self.assertEqual(sanitized["farmer_name"], "Kipchoge")

    def test_log_tool_call_creates_entry_with_masked_args(self):
        """log_tool_call creates an immutable AuditLog entry with masked payload."""
        entry = log_tool_call(
            user=self.user,
            tool_name="record_sale",
            args={
                "customer_phone": "+254799001122",
                "product": "Tomatoes",
                "amount": 4500,
            },
            ok=True,
            result={"sale_id": 99, "status": "recorded"},
            intent="POS",
            session=self.session,
        )

        self.assertIsNotNone(entry)
        self.assertEqual(entry.tool_name, "record_sale")
        self.assertTrue(entry.ok)
        self.assertEqual(entry.intent, "POS")
        # Ensure stored args has masked phone
        self.assertTrue(entry.args["customer_phone"].endswith("1122"))
        self.assertNotIn("79900", entry.args["customer_phone"])

        # Check entry persisted in DB
        db_entry = AuditLog.objects.get(id=entry.id)
        self.assertEqual(db_entry.user, self.user)
        self.assertEqual(db_entry.session, self.session)
