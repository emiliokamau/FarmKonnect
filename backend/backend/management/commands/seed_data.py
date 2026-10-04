import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from backend.models import (
    County, Commodity, MarketPrice, Event, Product, Listing, User
)


class Command(BaseCommand):
    help = "Seed initial reference data for counties, commodities, market prices, events, and services."

    def handle(self, *args, **options):
        self.stdout.write("Seeding counties...")
        counties_data = [
            ("Nairobi", "047"),
            ("Kiambu", "022"),
            ("Nakuru", "032"),
            ("Uasin Gishu", "027"),
            ("Machakos", "016"),
            ("Mombasa", "001"),
            ("Kisumu", "042"),
            ("Meru", "012"),
            ("Kilifi", "003"),
            ("Nyeri", "019"),
            ("Bungoma", "039"),
            ("Kakamega", "037"),
        ]
        counties = {}
        for name, code in counties_data:
            c, _ = County.objects.get_or_create(name=name, defaults={"code": code})
            counties[name] = c

        self.stdout.write("Seeding commodities...")
        commodities_data = [
            ("Dry Maize", "kg", "Cereals"),
            ("Beans (Yellow)", "kg", "Legumes"),
            ("Potatoes (Irish)", "kg", "Tubers"),
            ("Tomatoes", "kg", "Horticulture"),
            ("Cabbage", "head", "Horticulture"),
            ("Red Onions", "kg", "Horticulture"),
            ("Watermelon", "kg", "Fruits"),
            ("Bananas (Cooking)", "bunch", "Fruits"),
            ("Fresh Tilapia", "kg", "Fisheries"),
            ("Raw Cow Milk", "litre", "Dairy"),
        ]
        commodities = {}
        for name, unit, cat in commodities_data:
            comm, _ = Commodity.objects.get_or_create(name=name, defaults={"unit": unit, "category": cat})
            commodities[name] = comm

        self.stdout.write("Seeding market prices...")
        today = datetime.date.today()
        price_samples = [
            ("Dry Maize", "Nairobi", 58.00),
            ("Dry Maize", "Nakuru", 48.00),
            ("Dry Maize", "Uasin Gishu", 44.00),
            ("Beans (Yellow)", "Nairobi", 130.00),
            ("Beans (Yellow)", "Kiambu", 125.00),
            ("Beans (Yellow)", "Mombasa", 140.00),
            ("Potatoes (Irish)", "Nakuru", 45.00),
            ("Potatoes (Irish)", "Nairobi", 65.00),
            ("Tomatoes", "Nairobi", 90.00),
            ("Tomatoes", "Kiambu", 80.00),
            ("Red Onions", "Nairobi", 120.00),
            ("Red Onions", "Machakos", 110.00),
            ("Fresh Tilapia", "Kisumu", 280.00),
            ("Fresh Tilapia", "Nairobi", 350.00),
            ("Raw Cow Milk", "Kiambu", 55.00),
            ("Raw Cow Milk", "Nyeri", 50.00),
        ]
        for days_ago in range(0, 5):
            d = today - datetime.timedelta(days=days_ago)
            for comm_name, county_name, base_price in price_samples:
                # Add slight variation per day
                p = base_price + (days_ago * 0.5)
                MarketPrice.objects.get_or_create(
                    commodity=commodities[comm_name],
                    county=counties[county_name],
                    date=d,
                    defaults={"price": p, "source": "KAMIS / MoA Daily Monitor"},
                )

        self.stdout.write("Seeding events & training...")
        events_data = [
            (
                "National Soil Health & Fertilizer Subsidy Workshop",
                "Training farmers on correct fertilizer application rates and subsidy voucher redemption.",
                "Nakuru Agricultural Training Centre",
                "training",
                timezone.now() + datetime.timedelta(days=7),
                timezone.now() + datetime.timedelta(days=8),
            ),
            (
                "Climate-Smart Drip Irrigation Grant Briefing",
                "Information session on qualifying for matching grants for water harvesting and solar pumps.",
                "Eldoret Town Hall, Uasin Gishu",
                "grant",
                timezone.now() + datetime.timedelta(days=14),
                timezone.now() + datetime.timedelta(days=14, hours=4),
            ),
            (
                "Post-Harvest Loss Prevention Seminar",
                "Hermetic bag storage techniques and aflatoxin management in maize and beans.",
                "Machakos Farmers Training Centre",
                "training",
                timezone.now() + datetime.timedelta(days=21),
                timezone.now() + datetime.timedelta(days=22),
            ),
        ]
        for title, desc, loc, etype, s_date, e_date in events_data:
            Event.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "location": loc,
                    "event_type": etype,
                    "start_date": s_date,
                    "end_date": e_date,
                    "is_active": True,
                },
            )

        self.stdout.write("Seeding products & services...")
        products_data = [
            ("Certified Maize Seed (DK 8031)", "High-yield, drought-tolerant certified seed.", 480.00, 150, "Seeds"),
            ("Certified Bean Seed (Nyota)", "Fast-maturing biofortified bean variety.", 320.00, 80, "Seeds"),
            ("NPK Planting Fertilizer (50kg)", "Subsidized planting blend 17:17:17.", 2500.00, 200, "Fertilizer"),
            ("Solar Drip Irrigation Kit (Quarter Acre)", "Complete gravity/solar kit with pipes and drippers.", 18500.00, 20, "Equipment"),
            ("Hermetic Grain Storage Bags (50kg)", "Pest-free grain storage without synthetic pesticides.", 280.00, 500, "Storage"),
            ("Agricultural Extension Soil Testing", "Comprehensive NPK and pH lab soil testing per acre.", 1500.00, 999, "service"),
        ]
        for name, desc, price, stock, cat in products_data:
            Product.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "price": price,
                    "stock": stock,
                    "category": cat,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
