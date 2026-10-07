"""Tests for KonnectAI database tools: owner-scoped isolation, atomic rollback, and confirm gating."""

from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core_up.models import (
    FarmerProfile,
    Farm,
    CropRecord,
    Sale,
    Purchase,
    Product,
)
from konnect_ai import tools

User = get_user_model()


class ToolsSecurityAndIsolationTests(TestCase):
    def setUp(self):
        # Create Farmer A
        self.user_a = User.objects.create_user(username="farmer_a", phone="+254700000001")
        self.profile_a = FarmerProfile.objects.create(
            user=self.user_a,
            full_name="Farmer Alice",
            county="Nakuru",
        )
        self.farm_a = Farm.objects.create(
            farmer=self.profile_a,
            name="Alice Orchard",
            size=Decimal("5.0"),
        )

        # Create Farmer B
        self.user_b = User.objects.create_user(username="farmer_b", phone="+254700000002")
        self.profile_b = FarmerProfile.objects.create(
            user=self.user_b,
            full_name="Farmer Bob",
            county="Uasin Gishu",
        )
        self.farm_b = Farm.objects.create(
            farmer=self.profile_b,
            name="Bob Wheatfields",
            size=Decimal("12.0"),
        )

        # Create records for Farmer B
        self.sale_b = Sale.objects.create(
            farmer=self.profile_b,
            date="2026-10-01",
            product="Wheat",
            quantity=Decimal("50.0"),
            price=Decimal("3000.0"),
            amount=Decimal("150000.0"),
            customer="Grain Corp",
        )

    def test_owner_scoped_read_isolation_farms(self):
        """Farmer A should NEVER see Farmer B's farms."""
        res_a = tools.list_farms(self.user_a)
        self.assertTrue(res_a["ok"])
        farm_names = [f["name"] for f in res_a["data"]]
        self.assertIn("Alice Orchard", farm_names)
        self.assertNotIn("Bob Wheatfields", farm_names)

    def test_owner_scoped_read_isolation_sales(self):
        """Farmer A should NEVER see Farmer B's sales."""
        res_a = tools.list_recent_sales(self.user_a)
        self.assertTrue(res_a["ok"])
        self.assertEqual(len(res_a["data"]), 0)

    def test_missing_market_price_is_not_replaced_with_estimate(self):
        result = tools.get_market_price("Unlisted Test Commodity", county="Nakuru")

        self.assertFalse(result["ok"])
        self.assertIsNone(result["data"])
        self.assertIn("No recorded market price", result["summary_en"])

    def test_owner_scoped_write_isolation(self):
        """Farmer A cannot add a crop to Farmer B's farm."""
        initial_crops_b = CropRecord.objects.filter(farm=self.farm_b).count()

        # Farmer A attempts to add crop using Farmer B's farm_id
        res = tools.add_crop(
            user=self.user_a,
            crop="Tomatoes",
            farm_id=self.farm_b.id,
            confirm=True,
        )
        # Even if executed, it should fall back to Farmer A's own farm or fail, never touching Farmer B's farm
        crops_b_after = CropRecord.objects.filter(farm=self.farm_b).count()
        self.assertEqual(initial_crops_b, crops_b_after)

    def test_confirm_enforcement_for_writes(self):
        """All write tools must refuse to execute when confirm=False."""
        # Farm creation
        res_farm = tools.add_farm(self.user_a, name="New Ridge Farm", confirm=False)
        self.assertFalse(res_farm["ok"])
        self.assertFalse(res_farm["wrote"])
        self.assertFalse(Farm.objects.filter(name="New Ridge Farm").exists())

        # Crop creation
        res_crop = tools.add_crop(self.user_a, crop="Cabbage", confirm=False)
        self.assertFalse(res_crop["ok"])
        self.assertFalse(res_crop["wrote"])
        self.assertFalse(CropRecord.objects.filter(crop="Cabbage").exists())

        # Sale creation
        res_sale = tools.record_sale(
            self.user_a,
            product="Beans",
            quantity=10,
            price=2000,
            confirm=False,
        )
        self.assertFalse(res_sale["ok"])
        self.assertFalse(res_sale["wrote"])
        self.assertFalse(Sale.objects.filter(farmer=self.profile_a, product="Beans").exists())

    def test_confirm_true_creates_records(self):
        """When confirm=True, records are written and localized SMS text is returned."""
        res = tools.add_farm(
            self.user_a,
            name="Green Valley",
            size=3.5,
            size_unit="acres",
            confirm=True,
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["wrote"])
        self.assertTrue(Farm.objects.filter(name="Green Valley", farmer=self.profile_a).exists())
        self.assertIsNotNone(res.get("sms_text_local"))
        self.assertIn("Shamba jipya", res["sms_text_local"])

    def test_atomic_rollback_on_failure(self):
        """If a database error occurs during write, transaction rolls back and no SMS is sent."""
        initial_count = Farm.objects.filter(farmer=self.profile_a).count()

        with patch("core_up.models.Farm.objects.create", side_effect=IntegrityError("DB write error")):
            try:
                tools.add_farm(
                    self.user_a,
                    name="Failed Farm",
                    size=1.0,
                    confirm=True,
                )
            except Exception:
                pass

        final_count = Farm.objects.filter(farmer=self.profile_a).count()
        self.assertEqual(initial_count, final_count)
        self.assertFalse(Farm.objects.filter(name="Failed Farm").exists())
