# Copyright 2026 Google LLC
"""Seed script for Spotnest parking spots in Firestore."""

from datetime import datetime, timezone
from google.cloud import firestore

# Hardcoded project ID string to ensure compatibility with Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-241dd311c4eb"
COLLECTION_NAME = "parking_spots"

SEED_SPOTS = [
    {
        "spot_id": "maple_ave_1240",
        "title": "Maple Ave Driveway",
        "address": "1240 Maple Ave, Downtown",
        "hourly_rate": 8.0,
        "rating": 4.9,
        "reviews_count": 128,
        "match_percent": 98,
        "walking_minutes": 3,
        "distance_miles": 0.2,
        "available_now": True,
        # Spot Size Specifications
        "dimensions": {
            "spot_size": "Standard / Large (Fits up to Full-size SUV / Pickup)",
            "length_ft": 22,
            "width_ft": 10,
            "clearance": "No height limit (Open air driveway)",
            "vehicle_types": ["compact", "sedan", "suv", "truck", "ev"],
        },
        # Owner & Credibility
        "owner": {
            "host_id": "host_sarah_1240",
            "name": "Sarah Jenkins",
            "badge": "Top Host · Supernest",
            "identity_verified": True,
            "joined_year": 2023,
            "response_rate": "99%",
            "response_time": "within 5 mins",
            "total_bookings_hosted": 342,
        },
        "coordinates": {"latitude": 37.7749, "longitude": -122.4194},
        "image_url": "https://storage.googleapis.com/spotnest-driveways-qwiklabs-gcp-03-241dd311c4eb/driveway_maple.jpg",
        "features": ["EV Charging (Level 2)", "Paved", "Security Camera", "Well-lit at night"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "spot_id": "oak_street_512",
        "title": "Oak St Shaded Carport",
        "address": "512 Oak St, Arts District",
        "hourly_rate": 6.0,
        "rating": 4.8,
        "reviews_count": 64,
        "match_percent": 92,
        "walking_minutes": 5,
        "distance_miles": 0.4,
        "available_now": True,
        "dimensions": {
            "spot_size": "Compact / Midsize Sedan",
            "length_ft": 18,
            "width_ft": 8.5,
            "clearance": "Covered Carport: 7ft 2in clearance",
            "vehicle_types": ["compact", "sedan"],
        },
        "owner": {
            "host_id": "host_marcus_512",
            "name": "Marcus Lee",
            "badge": "Verified Local Host",
            "identity_verified": True,
            "joined_year": 2024,
            "response_rate": "95%",
            "response_time": "within 15 mins",
            "total_bookings_hosted": 118,
        },
        "coordinates": {"latitude": 37.7780, "longitude": -122.4140},
        "image_url": "https://storage.googleapis.com/spotnest-driveways-qwiklabs-gcp-03-241dd311c4eb/carport_oak.jpg",
        "features": ["Covered / Shaded", "Paved", "Easy Drive-in Access"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "spot_id": "pine_avenue_88",
        "title": "Pine Ave Gated Driveway",
        "address": "88 Pine Ave, Waterfront",
        "hourly_rate": 9.0,
        "rating": 5.0,
        "reviews_count": 42,
        "match_percent": 95,
        "walking_minutes": 4,
        "distance_miles": 0.3,
        "available_now": True,
        "dimensions": {
            "spot_size": "Oversized / Multi-Vehicle (Fits Sprinter Van / RV / Large SUV)",
            "length_ft": 28,
            "width_ft": 12,
            "clearance": "Gated open air, no height limit",
            "vehicle_types": ["compact", "sedan", "suv", "truck", "van", "ev"],
        },
        "owner": {
            "host_id": "host_elena_88",
            "name": "Elena Rostova",
            "badge": "Premier Host · 100% 5★",
            "identity_verified": True,
            "joined_year": 2022,
            "response_rate": "100%",
            "response_time": "within 2 mins",
            "total_bookings_hosted": 215,
        },
        "coordinates": {"latitude": 37.7810, "longitude": -122.4110},
        "image_url": "https://storage.googleapis.com/spotnest-driveways-qwiklabs-gcp-03-241dd311c4eb/driveway_pine.jpg",
        "features": ["Motorized Gate Entry", "EV Fast Charging", "24/7 Monitored Cameras"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "spot_id": "elm_court_19",
        "title": "Elm Court Budget Spot",
        "address": "19 Elm Court, Downtown North",
        "hourly_rate": 5.0,
        "rating": 4.7,
        "reviews_count": 31,
        "match_percent": 88,
        "walking_minutes": 7,
        "distance_miles": 0.5,
        "available_now": False,
        "dimensions": {
            "spot_size": "Standard Sedan",
            "length_ft": 19,
            "width_ft": 9,
            "clearance": "Open air",
            "vehicle_types": ["compact", "sedan"],
        },
        "owner": {
            "host_id": "host_dave_19",
            "name": "Dave Kaplan",
            "badge": "Community Neighbor",
            "identity_verified": True,
            "joined_year": 2024,
            "response_rate": "90%",
            "response_time": "within 1 hour",
            "total_bookings_hosted": 52,
        },
        "coordinates": {"latitude": 37.7850, "longitude": -122.4230},
        "image_url": "https://storage.googleapis.com/spotnest-driveways-qwiklabs-gcp-03-241dd311c4eb/driveway_elm.jpg",
        "features": ["Budget Friendly", "Paved", "Quiet cul-de-sac"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    for spot in SEED_SPOTS:
        doc_ref = collection.document(spot["spot_id"])
        doc_ref.set(spot)
        print(f"  ✓ Seeded parking spot: '{spot['title']}' ({spot['spot_id']}) with size specs and owner credibility")

    print("\nAll Spotnest parking spots seeded successfully!")


if __name__ == "__main__":
    seed_database()
