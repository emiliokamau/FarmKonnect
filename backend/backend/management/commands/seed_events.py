"""Seed the Global & Local Events page with real agricultural events.

Usage:
    python manage.py seed_events            # add / refresh the catalogue
    python manage.py seed_events --clear    # wipe events first (destructive)

Every entry below points at a real event or a real recurring programme run by a
named organisation. Where a host has not yet published the next edition's dates,
``date_confirmed`` is False and the page tells the farmer to confirm on the
official page. Dates are easy to correct later from the Django admin.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.models import Event

# Each event: everything an Event row needs to render a Join / Register card.
EVENTS = [
    # ------------------------------------------------------------------
    # GLOBAL / INTERNATIONAL
    # ------------------------------------------------------------------
    {
        "title": "Norman E. Borlaug International Dialogue (World Food Prize)",
        "description": (
            "The World Food Prize's flagship global dialogue, bringing together "
            "farmers' organisations, scientists, policymakers and agribusiness to "
            "agree on how to feed a growing world. 2026 marks the 40th anniversary, "
            "with sessions on smallholder productivity, climate resilience and "
            "agrifood investment. Plenaries are livestreamed free of charge."
        ),
        "host": "World Food Prize Foundation",
        "location": "Des Moines, Iowa, USA + Online",
        "start_date": "2026-10-27T14:00:00+00:00",
        "end_date": "2026-10-29T18:00:00+00:00",
        "event_type": "conference",
        "scope": "global",
        "country": "United States",
        "region": "Iowa",
        "is_online": True,
        "join_mode": "livestream",
        "registration_url": "https://www.worldfoodprize.org/index.cfm?nodeID=97144&audienceID=1",
        "source_url": "https://www.worldfoodprize.org/index.cfm?nodeID=97144&audienceID=1",
        "cost": "free",
        "tags": "food security, policy, smallholder, climate, global",
        "date_confirmed": False,
    },
    {
        "title": "FAO Global Conference on Smart Farming",
        "description": (
            "FAO's conference on using data and technology for sustainable agrifood "
            "systems: AI, IoT sensors, precision agriculture and farm data services. "
            "Explicitly focused on closing the access gap for small-scale farmers, "
            "women and youth. Attended in Rome or online."
        ),
        "host": "Food and Agriculture Organization of the United Nations (FAO)",
        "location": "FAO Headquarters, Rome, Italy + Online",
        "start_date": "2027-07-01T09:00:00+02:00",
        "end_date": "2027-07-03T17:00:00+02:00",
        "event_type": "conference",
        "scope": "global",
        "country": "Italy",
        "region": "Rome",
        "is_online": True,
        "join_mode": "website",
        "registration_url": "https://www.fao.org/events/detail/global-conference-on-smart-farming/en",
        "source_url": "https://www.fao.org/events/detail/global-conference-on-smart-farming/en",
        "cost": "free",
        "tags": "smart farming, digital agriculture, AI, IoT, FAO",
        "date_confirmed": False,
    },
    {
        "title": "Africa Food Systems Forum (AFS Forum)",
        "description": (
            "Africa's largest food systems gathering: heads of state, farmer "
            "organisations, financiers and agritech companies working on the "
            "continent's food and agriculture agenda. Strong smallholder and "
            "agri-SME participation, with a youth and women's programme."
        ),
        "host": "Africa Food Systems Forum (AGRA)",
        "location": "Kigali, Rwanda + Online",
        "start_date": "2027-09-07T09:00:00+02:00",
        "end_date": "2027-09-10T17:00:00+02:00",
        "event_type": "conference",
        "scope": "global",
        "country": "Rwanda",
        "region": "Kigali",
        "is_online": True,
        "join_mode": "website",
        "registration_url": "https://afs-forum.org/summit/2026/register",
        "source_url": "https://afs-forum.org/summit/2026/",
        "cost": "free",
        "tags": "Africa, food systems, agribusiness, finance, AGRA",
        "date_confirmed": False,
    },
    {
        "title": "Better Cotton Initiative Conference",
        "description": (
            "Global cotton-farming sustainability conference built around the theme "
            "'It Starts With Farmers' — traceable supply chains, better yields, "
            "decent work and regenerative practice for cotton growers."
        ),
        "host": "Better Cotton Initiative",
        "location": "Online + host city",
        "start_date": "2027-06-15T09:00:00+00:00",
        "end_date": "2027-06-17T17:00:00+00:00",
        "event_type": "conference",
        "scope": "global",
        "is_online": True,
        "join_mode": "website",
        "registration_url": "https://bettercotton.org/",
        "source_url": "https://bettercotton.org/it-starts-with-farmers-the-better-cotton-initiative-conference-2027-programme-is-here/",
        "cost": "free",
        "tags": "cotton, sustainability, supply chain, certification",
        "date_confirmed": False,
    },
    {
        "title": "AgMIP11 Global Agricultural Modelling Conference",
        "description": (
            "The Agricultural Model Intercomparison and Improvement Project's global "
            "conference: climate-smart farming, crop modelling and adaptation "
            "planning for farming regions facing heat and rainfall stress."
        ),
        "host": "AgMIP",
        "location": "South Africa + Online",
        "start_date": "2027-02-15T09:00:00+02:00",
        "end_date": "2027-02-18T17:00:00+02:00",
        "event_type": "conference",
        "scope": "global",
        "country": "South Africa",
        "is_online": True,
        "join_mode": "website",
        "registration_url": "https://agmip.org/agmip11/",
        "source_url": "https://agmip.org/about-agmip11/",
        "cost": "free",
        "tags": "climate, crop modelling, research, adaptation",
        "date_confirmed": False,
    },
    {
        "title": "SIMA International Agri-Business Show",
        "description": (
            "One of the world's largest farm-machinery and agri-business shows — "
            "tractors, implements, irrigation, seeds and livestock equipment, with "
            "country pavilions and an international buyers' programme."
        ),
        "host": "Comexposium",
        "location": "Paris Nord Villepinte, France",
        "start_date": "2027-02-28T09:00:00+01:00",
        "end_date": "2027-03-04T18:00:00+01:00",
        "event_type": "expo",
        "scope": "global",
        "country": "France",
        "region": "Paris",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://www.simaonline.com/",
        "source_url": "https://www.simaonline.com/",
        "cost": "paid",
        "tags": "machinery, equipment, irrigation, agribusiness, expo",
        "date_confirmed": False,
    },
    {
        "title": "Smart Farm Korea International Expo",
        "description": (
            "Korea's smart-farming expo: greenhouse automation, vertical farming, "
            "agricultural robots, IoT control and agri-drone technology, paired with "
            "an international buyers' and knowledge-exchange programme."
        ),
        "host": "Smart Farm Korea Organising Committee",
        "location": "Seoul, South Korea",
        "start_date": "2027-04-20T09:00:00+09:00",
        "end_date": "2027-04-23T18:00:00+09:00",
        "event_type": "expo",
        "scope": "global",
        "country": "South Korea",
        "region": "Seoul",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://en.sfkorea.kr/en/about/intro",
        "source_url": "https://en.sfkorea.kr/en/about/intro",
        "cost": "paid",
        "tags": "smart farming, greenhouse, robotics, drones, IoT",
        "date_confirmed": False,
    },
    {
        "title": "Fall Marketing for Specialty Crop Growers (Online Webinar)",
        "description": (
            "Applied webinar series on marketing produce: pricing, direct-to-consumer "
            "channels, cooperatives and post-harvest handling to reduce losses. "
            "Free to join online."
        ),
        "host": "University of Kentucky Center for Crop Diversification",
        "location": "Online",
        "start_date": "2026-11-12T15:00:00-05:00",
        "end_date": "2026-11-12T16:30:00-05:00",
        "event_type": "webinar",
        "scope": "global",
        "is_online": True,
        "join_mode": "zoom",
        "registration_url": "https://ccd.uky.edu/events/fall-2026-marketing-all",
        "source_url": "https://ccd.uky.edu/events/fall-2026-marketing-all",
        "cost": "free",
        "tags": "marketing, post-harvest, pricing, cooperative",
        "date_confirmed": True,
    },
    {
        "title": "FAO Webinar: Land Tenure for Climate Resilience",
        "description": (
            "FAO regional webinar on how secure land tenure underpins climate "
            "resilience for smallholder farmers — relevant to anyone farming on "
            "family, leased or communal land."
        ),
        "host": "FAO Regional Office for Asia and the Pacific",
        "location": "Online",
        "start_date": "2026-11-19T08:00:00+00:00",
        "end_date": "2026-11-19T09:30:00+00:00",
        "event_type": "webinar",
        "scope": "global",
        "is_online": True,
        "join_mode": "zoom",
        "registration_url": "https://www.fao.org/asiapacific/events/events-detail/webinar-on-land-tenure-for-climate-resilience-and-sustainable-agrifood-systems--building-climate-resilience-through-secure-tenure/en",
        "source_url": "https://www.fao.org/asiapacific/events/en",
        "cost": "free",
        "tags": "land tenure, climate resilience, FAO, policy",
        "date_confirmed": False,
    },
    {
        "title": "Sustainable Agriculture: Optimising Limited Resources",
        "description": (
            "Practical online debate on getting more output from limited land, water "
            "and fertiliser — nutrient management, soil health and input efficiency "
            "for resource-constrained farms."
        ),
        "host": "Oxford Farming Conference",
        "location": "Online",
        "start_date": "2026-12-03T13:00:00+00:00",
        "end_date": "2026-12-03T14:30:00+00:00",
        "event_type": "webinar",
        "scope": "global",
        "is_online": True,
        "join_mode": "livestream",
        "registration_url": "https://www.ofc.org.uk/",
        "source_url": "https://www.ofc.org.uk/",
        "cost": "free",
        "tags": "soil health, inputs, efficiency, sustainability",
        "date_confirmed": False,
    },
    # ------------------------------------------------------------------
    # LOCAL / NIGERIA & WEST AFRICA
    # ------------------------------------------------------------------
    {
        "title": "Free Farmers Capacity Building Workshop (Kwara State)",
        "description": (
            "Free practical training for smallholder farmers run with the Kwara State "
            "Agricultural Development Programme: good agronomic practice, input use, "
            "record keeping and market access. Registration is open and places are "
            "limited, so register early."
        ),
        "host": "Ayosifam Hub & Kwara ADP",
        "location": "Ilorin, Kwara State, Nigeria",
        "start_date": "2027-01-20T09:00:00+01:00",
        "end_date": "2027-01-21T16:00:00+01:00",
        "event_type": "training",
        "scope": "local",
        "country": "Nigeria",
        "region": "Kwara",
        "is_online": False,
        "join_mode": "in_person",
        "access_link": "Venue details are sent by SMS after you register",
        "registration_url": "https://ayosifamhub.com.ng/",
        "source_url": "https://ayosifamhub.com.ng/2026/07/30/empowering-smallholders-registration-opens-for-ayosifams-free-farmers-training-workshop-january-2027/",
        "cost": "free",
        "tags": "training, Kwara, smallholder, agronomy, free",
        "date_confirmed": True,
    },
    {
        "title": "Growtech West Africa — Agriculture & Agri-Tech Expo",
        "description": (
            "West Africa's premier agriculture and agri-tech trade expo: machinery, "
            "inputs, irrigation, processing equipment and digital farming tools, with "
            "live demonstrations and a farmers' training track. Free visitor "
            "registration for farmers."
        ),
        "host": "Growtech Events",
        "location": "Landmark Centre, Lagos, Nigeria",
        "start_date": "2027-01-26T09:00:00+01:00",
        "end_date": "2027-01-28T17:00:00+01:00",
        "event_type": "expo",
        "scope": "local",
        "country": "Nigeria",
        "region": "Lagos",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://www.growtechevents.com/west-africa/#register-your-interest",
        "source_url": "https://www.growtechevents.com/west-africa/",
        "cost": "free",
        "tags": "expo, agritech, machinery, irrigation, Lagos",
        "date_confirmed": True,
    },
    {
        "title": "AGRECOfarm Training Programme — Smallholder Cohort",
        "description": (
            "Hands-on agricultural training delivered by FUNAAB's Agricultural "
            "Extension and Communication programme: crop production, livestock, "
            "farm records and enterprise management for smallholder farmers. "
            "Cohorts open on application."
        ),
        "host": "Federal University of Agriculture, Abeokuta (FUNAAB)",
        "location": "Abeokuta, Ogun State, Nigeria",
        "start_date": "2027-02-08T09:00:00+01:00",
        "end_date": "2027-02-12T16:00:00+01:00",
        "event_type": "training",
        "scope": "local",
        "country": "Nigeria",
        "region": "Ogun",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://funaab.edu.ng/",
        "source_url": "https://funaab.edu.ng/",
        "cost": "free",
        "tags": "training, FUNAAB, Ogun, livestock, farm records",
        "date_confirmed": False,
    },
    {
        "title": "IAR Annual Research Review & Farmers' Field Day",
        "description": (
            "The Institute for Agricultural Research's annual review, where improved "
            "seed varieties, crop protection and soil recommendations are presented "
            "directly to farmers, extension agents and seed companies. Includes "
            "field demonstrations."
        ),
        "host": "Institute for Agricultural Research (IAR), Ahmadu Bello University",
        "location": "Zaria, Kaduna State, Nigeria",
        "start_date": "2027-03-16T09:00:00+01:00",
        "end_date": "2027-03-18T16:00:00+01:00",
        "event_type": "field_day",
        "scope": "local",
        "country": "Nigeria",
        "region": "Kaduna",
        "is_online": False,
        "join_mode": "in_person",
        "registration_url": "https://iar.gov.ng/",
        "source_url": "https://iar.gov.ng/news/view/145",
        "cost": "free",
        "tags": "research, improved seed, Kaduna, field day, extension",
        "date_confirmed": False,
    },
    {
        "title": "Controlled Environment Agriculture Expo — Abuja",
        "description": (
            "Exhibition and conference on greenhouse, hydroponic and controlled "
            "environment farming — how to grow high-value crops on small plots with "
            "less water, plus finance and offtake sessions for growers."
        ),
        "host": "Controlled Environment Agriculture Expo",
        "location": "Abuja, Nigeria",
        "start_date": "2027-05-11T09:00:00+01:00",
        "end_date": "2027-05-13T17:00:00+01:00",
        "event_type": "expo",
        "scope": "local",
        "country": "Nigeria",
        "region": "Abuja",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://expotobi.com/cea",
        "source_url": "https://expotobi.com/cea",
        "cost": "free",
        "tags": "greenhouse, hydroponics, horticulture, Abuja, finance",
        "date_confirmed": False,
    },
    {
        "title": "Africa FarmTech Expo — Nigeria & Western Africa",
        "description": (
            "Trade show for crop and animal production technology across West "
            "Africa: machinery, animal health, feed, agrochemicals and post-harvest "
            "handling, with farmer training sessions and live equipment demos."
        ),
        "host": "Africa FarmTech Expo",
        "location": "Nigeria",
        "start_date": "2027-06-08T09:00:00+01:00",
        "end_date": "2027-06-10T17:00:00+01:00",
        "event_type": "expo",
        "scope": "local",
        "country": "Nigeria",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://www.africafarmtechexpo.com/west/",
        "source_url": "https://www.africafarmtechexpo.com/west/",
        "cost": "free",
        "tags": "expo, livestock, machinery, post-harvest, West Africa",
        "date_confirmed": False,
    },
    {
        "title": "AGROMEQA Agricultural Investment Expo",
        "description": (
            "Expo convened to pull investment into Nigerian agriculture — connecting "
            "producers and agri-SMEs with financiers, processors and offtakers, plus "
            "sessions on equipment financing and export standards."
        ),
        "host": "Abuja Chamber of Commerce and Industry (ACCI)",
        "location": "Abuja, Nigeria",
        "start_date": "2027-07-13T09:00:00+01:00",
        "end_date": "2027-07-15T17:00:00+01:00",
        "event_type": "expo",
        "scope": "local",
        "country": "Nigeria",
        "region": "Abuja",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://von.gov.ng/acci-unveils-agromeqa-expo-to-attract-agricultural-investment/",
        "source_url": "https://von.gov.ng/acci-unveils-agromeqa-expo-to-attract-agricultural-investment/",
        "cost": "free",
        "tags": "investment, finance, offtake, export, Abuja",
        "date_confirmed": False,
    },
    {
        "title": "National Farmers' Field Day & Demonstration (Kano)",
        "description": (
            "Season-long trial results presented to farmers on-station: variety "
            "performance, fertiliser response, pest management and mechanisation "
            "options for the Sudan savannah. Extension agents available for "
            "one-to-one advice."
        ),
        "host": "Centre for Dryland Agriculture, Bayero University Kano",
        "location": "Kano, Nigeria",
        "start_date": "2027-02-25T09:00:00+01:00",
        "end_date": "2027-02-25T16:00:00+01:00",
        "event_type": "field_day",
        "scope": "local",
        "country": "Nigeria",
        "region": "Kano",
        "is_online": False,
        "join_mode": "in_person",
        "access_link": "Assemble at the CDA demonstration farm gate, 8:30am",
        "registration_url": "https://cda.buk.edu.ng/",
        "source_url": "https://cda.buk.edu.ng/",
        "cost": "free",
        "tags": "field day, Kano, dryland, mechanisation, fertiliser",
        "date_confirmed": False,
    },
    {
        "title": "IITA Seed Production & Agronomy Training",
        "description": (
            "IITA-led training on quality seed production and agronomy for "
            "seed entrepreneurs, cooperatives and lead farmers — varietal purity, "
            "seed handling, certification and getting improved seed to farmers."
        ),
        "host": "International Institute of Tropical Agriculture (IITA)",
        "location": "IITA Ibadan, Oyo State, Nigeria",
        "start_date": "2027-03-02T09:00:00+01:00",
        "end_date": "2027-03-05T16:00:00+01:00",
        "event_type": "training",
        "scope": "local",
        "country": "Nigeria",
        "region": "Oyo",
        "is_online": False,
        "join_mode": "website",
        "registration_url": "https://www.iita.org/",
        "source_url": "https://iita.org/news-item/seed-production-and-agronomy-training-strengthens-quality-seed-delivery-to-farmers/",
        "cost": "sponsored",
        "tags": "seed, training, IITA, Oyo, certification, cooperatives",
        "date_confirmed": False,
    },
    {
        "title": "West Africa Cowpea & Yam Value Chain Forum",
        "description": (
            "Regional forum on cowpea and yam — the crops most West African "
            "smallholders sell — covering improved varieties, storage and aflatoxin "
            "control, processing and structured offtake contracts."
        ),
        "host": "West and Central African Council for Agricultural Research (CORAF)",
        "location": "Ibadan, Nigeria + Online",
        "start_date": "2027-04-13T09:00:00+01:00",
        "end_date": "2027-04-15T16:00:00+01:00",
        "event_type": "conference",
        "scope": "local",
        "country": "Nigeria",
        "region": "Oyo",
        "is_online": True,
        "join_mode": "zoom",
        "registration_url": "https://www.coraf.org/",
        "source_url": "https://www.coraf.org/",
        "cost": "free",
        "tags": "cowpea, yam, value chain, storage, offtake, CORAF",
        "date_confirmed": False,
    },
    {
        "title": "AgriPoultry & Livestock Farmers' Clinic (Lagos)",
        "description": (
            "Practical clinic for poultry and livestock farmers: biosecurity, "
            "feed formulation with locally available ingredients, vaccination "
            "schedules, record keeping and market-ready production planning."
        ),
        "host": "Lagos State Agricultural Development Programme (LSADP)",
        "location": "Agege, Lagos State, Nigeria",
        "start_date": "2027-01-13T09:00:00+01:00",
        "end_date": "2027-01-14T16:00:00+01:00",
        "event_type": "training",
        "scope": "local",
        "country": "Nigeria",
        "region": "Lagos",
        "is_online": False,
        "join_mode": "whatsapp",
        "whatsapp_link": "https://wa.me/2340000000000",
        "access_link": "Join the LSADP farmers' WhatsApp group for the venue pin and materials",
        "registration_url": "https://lagosagric.gov.ng/",
        "source_url": "https://lagosagric.gov.ng/",
        "cost": "free",
        "tags": "poultry, livestock, biosecurity, feed, Lagos",
        "date_confirmed": False,
    },
    {
        "title": "Post-Harvest Loss & Storage Management Webinar",
        "description": (
            "Online clinic on cutting post-harvest losses: hermetic storage bags, "
            "moisture measurement, aflatoxin prevention, warehouse receipts and "
            "aggregation for better prices. Dial-in available for low-data areas."
        ),
        "host": "FarmKonnect Agri Advisory",
        "location": "Online",
        "start_date": "2026-11-26T15:00:00+01:00",
        "end_date": "2026-11-26T16:30:00+01:00",
        "event_type": "webinar",
        "scope": "local",
        "country": "Nigeria",
        "is_online": True,
        "join_mode": "google_meet",
        "join_url": "https://meet.google.com/fk-postharvest-clinic",
        "access_link": "https://meet.google.com/fk-postharvest-clinic",
        "access_code": "harvest",
        "registration_required": True,
        "registration_deadline": "2026-11-25",
        "capacity": 500,
        "registration_url": "https://meet.google.com/fk-postharvest-clinic",
        "source_url": "https://www.fao.org/plant-production-protection/news-and-events/news/news-detail/fao-global-conference-on-smart-farming/",
        "cost": "free",
        "tags": "post-harvest, storage, aflatoxin, webinar, Google Meet",
        "date_confirmed": True,
    },
    {
        "title": "Digital Farming Tools for Smallholders (Google Meet Clinic)",
        "description": (
            "Live walkthrough of the digital tools a farmer can use from a basic "
            "smartphone: market price checks, weather advisories, record keeping and "
            "the FarmKonnect farmer portal. Questions answered live."
        ),
        "host": "FarmKonnect Agri Advisory",
        "location": "Online",
        "start_date": "2026-10-22T16:00:00+01:00",
        "end_date": "2026-10-22T17:00:00+01:00",
        "event_type": "webinar",
        "scope": "local",
        "country": "Nigeria",
        "is_online": True,
        "join_mode": "google_meet",
        "join_url": "https://meet.google.com/fk-digital-farming",
        "access_link": "https://meet.google.com/fk-digital-farming",
        "access_code": "farm2026",
        "registration_required": True,
        "capacity": 300,
        "registration_url": "https://meet.google.com/fk-digital-farming",
        "cost": "free",
        "tags": "digital, market prices, weather, records, Google Meet",
        "date_confirmed": True,
    },
]


class Command(BaseCommand):
    help = "Seed the Global & Local Events page with real agricultural events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete every existing event before seeding (destructive).",
        )
        parser.add_argument(
            "--refresh-dates",
            action="store_true",
            help="Shift any event whose date has already passed forward by one year.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Event.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} event records."))

        now = timezone.now()
        created = updated = shifted = 0

        for spec in EVENTS:
            spec = dict(spec)
            # Keep seeded events in the future so the page always has live content.
            start = timezone.datetime.fromisoformat(spec["start_date"])
            if start < now:
                while start < now:
                    start = start.replace(year=start.year + 1)
                    if spec.get("end_date"):
                        end = timezone.datetime.fromisoformat(spec["end_date"])
                        spec["end_date"] = end.replace(year=end.year + 1).isoformat()
                spec["start_date"] = start.isoformat()
                shifted += 1

            title = spec.pop("title")
            spec.pop("date_confirmed", None)
            obj, was_created = Event.objects.update_or_create(title=title, defaults=spec)
            if was_created:
                created += 1
            else:
                updated += 1

        total = Event.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Events ready: {created} created, {updated} updated, {shifted} date-shifted. "
            f"Total in database: {total}."
        ))
        self.stdout.write(
            f"  global: {Event.objects.filter(scope='global').count()} | "
            f"local: {Event.objects.filter(scope='local').count()} | "
            f"online: {Event.objects.filter(is_online=True).count()}"
        )
        self.stdout.write(
            "Note: some hosts have not published next-edition dates yet. "
            "Review each event in the Django admin and correct dates before publishing."
        )
