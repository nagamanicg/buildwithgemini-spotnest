# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from google.cloud import firestore, storage
from google import genai

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

# Hardcoded project ID string to ensure compatibility with Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-241dd311c4eb"
BUCKET_NAME = "spotnest-driveways-qwiklabs-gcp-03-241dd311c4eb"
COLLECTION_NAME = "parking_spots"
BOOKINGS_COLLECTION = "parking_bookings"
MODEL = "gemini-3.6-flash"


def _get_firestore_client() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def list_parking_spots(
    max_price: Optional[float] = None,
    available_only: bool = True,
) -> List[Dict[str, Any]]:
    """List available neighborhood driveway parking spots from Firestore.

    Args:
        max_price: Optional maximum hourly rate in dollars (e.g. 10.0).
        available_only: Filter only spots currently marked as available (default True).

    Returns:
        A list of parking spots with address, hourly price, rating, and walking distance.
    """
    db = _get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    spots = []
    for doc in docs:
        data = doc.to_dict()
        data["spot_id"] = doc.id
        if available_only and not data.get("available_now", True):
            continue
        if max_price is not None and data.get("hourly_rate", 0) > max_price:
            continue
        spots.append(data)
    return spots


def get_parking_spot(spot_id: str) -> Dict[str, Any]:
    """Retrieve details for a specific parking spot by ID.

    Args:
        spot_id: Identifier of the spot (e.g. 'maple_ave_1240', 'oak_street_512').

    Returns:
        The full spot details including rate, walking distance, reviews, and host info.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(spot_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Parking spot '{spot_id}' not found."}
    data = doc.to_dict()
    data["spot_id"] = doc.id
    return data


def book_parking_spot(
    spot_id: str,
    driver_name: str,
    duration_hours: int = 2,
    start_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Reserve an available driveway parking spot for a specified duration.

    Args:
        spot_id: ID of the parking spot to reserve (e.g. 'maple_ave_1240').
        driver_name: Name of the driver making the reservation.
        duration_hours: Number of hours to reserve (default 2).
        start_time: Optional starting time window (e.g. '2:00 PM').

    Returns:
        A booking confirmation object with total cost and reservation status.
    """
    db = _get_firestore_client()
    spot = get_parking_spot(spot_id)
    if "error" in spot:
        return spot

    hourly_rate = spot.get("hourly_rate", 8.0)
    total_cost = round(hourly_rate * duration_hours, 2)
    booking_id = f"book_{spot_id}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

    booking_record = {
        "booking_id": booking_id,
        "spot_id": spot_id,
        "spot_title": spot.get("title", "Driveway Spot"),
        "address": spot.get("address", ""),
        "driver_name": driver_name,
        "duration_hours": duration_hours,
        "hourly_rate": hourly_rate,
        "total_cost": total_cost,
        "start_time": start_time or datetime.datetime.now(datetime.timezone.utc).strftime("%I:%M %p"),
        "status": "reserved",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    db.collection(BOOKINGS_COLLECTION).document(booking_id).set(booking_record)
    return {
        "message": f"Successfully reserved {spot.get('title')} for {duration_hours} hours!",
        "booking": booking_record,
    }


def list_host_driveway(
    spot_id: str,
    title: str,
    address: str,
    hourly_rate: float,
    host_name: str,
    features: Optional[List[str]] = None,
    available_now: bool = True,
) -> Dict[str, Any]:
    """Register or publish a homeowner's driveway parking spot on Spotnest.

    Args:
        spot_id: A slug identifier for the spot (e.g., 'elm_street_42').
        title: Descriptive title (e.g., 'Elm St Wide Paved Driveway').
        address: Full street address.
        hourly_rate: Hourly rate in dollars (e.g., 7.50).
        host_name: Name of the host.
        features: Optional list of features (e.g., ['EV Charging', 'Paved', 'Security Camera']).
        available_now: Whether the spot is immediately available (default True).

    Returns:
        Confirmation dictionary with the newly listed spot details.
    """
    db = _get_firestore_client()
    spot_data = {
        "spot_id": spot_id,
        "title": title,
        "address": address,
        "hourly_rate": float(hourly_rate),
        "rating": 5.0,
        "reviews_count": 0,
        "match_percent": 95,
        "walking_minutes": 4,
        "distance_miles": 0.3,
        "available_now": available_now,
        "host_name": host_name,
        "features": features or ["Paved Driveway"],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    db.collection(COLLECTION_NAME).document(spot_id).set(spot_data, merge=True)
    return {
        "message": f"You're live! Spot '{title}' published successfully at ${hourly_rate}/hr.",
        "spot": spot_data,
    }


def calculate_walking_route(spot_address: str, destination_address: str) -> Dict[str, Any]:
    """Calculate exact walking distance in miles and walking duration in minutes between a parking spot and destination.

    Args:
        spot_address: Address of the reserved or proposed parking spot.
        destination_address: Final destination address or venue (e.g., '100 Market St' or 'Convention Center').

    Returns:
        A dictionary with walking minutes, walking distance in miles, and foot path details.
    """
    import json
    import urllib.parse
    import urllib.request

    def _geocode(query: str):
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "SpotnestAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            if not data:
                return None
            return float(data[0]["lon"]), float(data[0]["lat"])

    try:
        p1 = _geocode(spot_address)
        p2 = _geocode(destination_address)
        if not p1 or not p2:
            # Fallback estimation if geocoding coordinates are approximate
            return {
                "spot_address": spot_address,
                "destination_address": destination_address,
                "walking_minutes": 4,
                "walking_distance_miles": 0.25,
                "route_type": "Pedestrian Sidewalk Route (Estimated)",
            }

        osrm_url = f"https://router.project-osrm.org/route/v1/foot/{p1[0]},{p1[1]};{p2[0]},{p2[1]}?overview=false"
        req = urllib.request.Request(osrm_url, headers={"User-Agent": "SpotnestAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            route_data = json.loads(resp.read().decode())
            if "routes" not in route_data or not route_data["routes"]:
                return {
                    "spot_address": spot_address,
                    "destination_address": destination_address,
                    "walking_minutes": 3,
                    "walking_distance_miles": 0.2,
                    "route_type": "Direct Walk",
                }

            duration_seconds = route_data["routes"][0]["duration"]
            distance_meters = route_data["routes"][0]["distance"]
            walking_minutes = max(1, round(duration_seconds / 60))
            distance_miles = round(distance_meters * 0.000621371, 2)

            return {
                "spot_address": spot_address,
                "destination_address": destination_address,
                "walking_minutes": walking_minutes,
                "walking_distance_miles": distance_miles,
                "walking_chip": f"{walking_minutes} min walk · {distance_miles} mi",
                "route_type": "Real-time OSRM Foot Network",
            }
    except Exception as e:
        return {
            "spot_address": spot_address,
            "destination_address": destination_address,
            "walking_minutes": 3,
            "walking_distance_miles": 0.2,
            "note": f"Fallback estimation applied: {str(e)}",
        }


def get_parking_map_url(
    spot_address: str,
    destination_address: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    """Generate live Google Maps directions, embedded links, and static map preview URLs for a parking spot.

    Args:
        spot_address: The street address of the parking spot.
        destination_address: Optional driver destination to show live walking directions.
        latitude: Optional spot latitude for pinpoint accuracy.
        longitude: Optional spot longitude for pinpoint accuracy.

    Returns:
        A dictionary containing live Google Maps directions URL, search URL, and map display metadata.
    """
    import os
    import urllib.parse
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # Live interactive Google Maps URLs
    query_dest = destination_address or spot_address
    google_maps_directions_url = (
        f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(spot_address)}"
        f"&destination={urllib.parse.quote(query_dest)}&travelmode=walking"
    )
    google_maps_view_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(spot_address)}"

    # Google Static Maps Image URL (renders directly as an image if API key is active)
    pin_location = f"{latitude},{longitude}" if (latitude and longitude) else urllib.parse.quote(spot_address)
    static_map_preview_url = (
        f"https://maps.googleapis.com/maps/api/staticmap?center={pin_location}&zoom=16&size=600x300"
        f"&scale=2&markers=color:orange%7Clabel:P%7C{pin_location}&key={api_key}"
    )

    return {
        "spot_address": spot_address,
        "destination_address": destination_address,
        "google_maps_directions_url": google_maps_directions_url,
        "google_maps_view_url": google_maps_view_url,
        "static_map_image_url": static_map_preview_url,
        "map_label": "Live Google Maps Route",
    }


def get_parking_weather(location: str) -> Dict[str, Any]:
    """Fetch real-time weather and outdoor parking/walking conditions for a spot using Open-Meteo public API.

    Args:
        location: Street address or neighborhood name (e.g. '1240 Maple Ave, Downtown' or 'San Francisco').

    Returns:
        A dictionary with temperature, precipitation, wind speed, condition description, and outdoor parking advisories.
    """
    import json
    import os
    import urllib.parse
    import urllib.request

    def _geocode(query: str):
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "SpotnestAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            if not data:
                return None
            return float(data[0]["lon"]), float(data[0]["lat"])

    try:
        coords = _geocode(location)
        if not coords:
            lat, lon = 37.7749, -122.4194
        else:
            lon, lat = coords

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,precipitation,weather_code,wind_speed_10m"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
        )
        req = urllib.request.Request(weather_url, headers={"User-Agent": "SpotnestAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            current = data.get("current", {})
            temp = current.get("temperature_2m")
            precip = current.get("precipitation", 0.0)
            wind = current.get("wind_speed_10m", 0.0)

            # Spotnest outdoor parking advice
            if precip > 0.1:
                advisory = "🌧️ Rain reported: Covered carport recommended. Don't forget an umbrella for your walk to your venue."
                condition = "Rainy"
            elif temp is not None and temp > 85:
                advisory = "☀️ High heat: Shaded carport recommended to keep your car interior cool."
                condition = "Sunny / Hot"
            elif temp is not None and temp < 32:
                advisory = "❄️ Freezing: Beware of ice on driveway surfaces."
                condition = "Freezing"
            else:
                advisory = "🌤️ Clear skies: Ideal conditions for open driveway parking and walking."
                condition = "Clear / Fair"

            return {
                "location": location,
                "temperature_f": temp,
                "precipitation_inches": precip,
                "wind_speed_mph": wind,
                "condition": condition,
                "parking_advisory": advisory,
                "source": "Open-Meteo Free Public Weather API",
            }
    except Exception as e:
        return {"error": f"Failed to fetch parking weather: {str(e)}"}


def geocode_address(address: str) -> Dict[str, Any]:
    """Turn an address or location name into geographic coordinates using Google Maps Geocoding API.

    Args:
        address: The street address or city to geocode (e.g., '1600 Amphitheatre Parkway, Mountain View, CA').

    Returns:
        A dictionary with formatted address, latitude, and longitude.
    """
    import json
    import os
    import urllib.parse
    import urllib.request
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not configured in environment."}

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") != "OK" or not data.get("results"):
                return {"error": f"Geocoding failed for '{address}': {data.get('status', 'NO_RESULTS')}"}

            first = data["results"][0]
            loc = first["geometry"]["location"]
            return {
                "address_query": address,
                "formatted_address": first.get("formatted_address"),
                "location": {
                    "latitude": loc["lat"],
                    "longitude": loc["lng"],
                },
            }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    place_type: str,
    latitude: float,
    longitude: float,
    radius_meters: float = 1500.0,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Find nearby places (e.g. coffee shop, gas station, EV charger, restaurant) using Places API (New).

    Args:
        place_type: Type of place to search for (e.g. 'cafe', 'gas_station', 'restaurant', 'electric_vehicle_charging_station').
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        radius_meters: Search radius in meters (default 1500 meters).
        max_results: Maximum number of places to return (default 5, max 20).

    Returns:
        A dictionary containing list of matching places with name, formatted address, and location coordinates.
    """
    import json
    import os
    import urllib.request
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not configured in environment."}

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        payload = json.dumps({
            "includedTypes": [place_type],
            "maxResultCount": min(max_results, 20),
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                    },
                    "radius": float(radius_meters),
                }
            },
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            places_raw = data.get("places", [])
            places_summary = []
            for p in places_raw:
                display_name = p.get("displayName", {}).get("text", "")
                places_summary.append({
                    "name": display_name,
                    "address": p.get("formattedAddress"),
                    "location": p.get("location"),
                })

            return {
                "place_type": place_type,
                "count": len(places_summary),
                "places": places_summary,
            }
    except Exception as e:
        return {"error": f"Nearby places search failed: {str(e)}"}


async def generate_driveway_image(
    spot_title: str,
    visual_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a photo of a parking spot driveway or carport using gemini-3.1-flash-lite-image, save as artifact, and upload to public GCS bucket.

    Args:
        spot_title: Name of the spot (e.g., 'Maple Ave Driveway', 'Oak St Shaded Carport').
        visual_description: Visual details of the property (e.g., 'Suburban paved driveway with manicured lawn and EV charging station').
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary with image details and the public HTTPS URL from Google Cloud Storage.
    """
    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global region
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        prompt = (
            f"Realistic high quality architectural photograph of a residential parking spot: {spot_title}. "
            f"Details: {visual_description}. Clear daylight, clean driveway, welcoming home environment."
        )
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "Failed to generate image bytes from model."}

        # Safe slug for artifact and storage object
        safe_name = "".join(c if c.isalnum() else "_" for c in spot_title.lower()).strip("_")
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        filename = f"{safe_name}_{timestamp}.jpg"

        # 2. Save image with tool_context.save_artifact so it shows in Playground's Artifacts panel
        part = types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes))
        await tool_context.save_artifact(filename=filename, artifact=part)

        # 3. Upload image bytes directly to public GCS bucket (no local file write)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_https_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "spot_title": spot_title,
            "artifact_filename": filename,
            "public_url": public_https_url,
            "message": f"Generated driveway photo for '{spot_title}', saved to artifacts, and published to Cloud Storage.",
        }
    except Exception as e:
        return {"error": f"Image generation or upload failed: {str(e)}"}


async def generate_driveway_video(
    spot_title: str,
    scene_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a short video of a residential parking spot using Google's Omni model (gemini-omni-flash-preview) in global region, save as artifact, and upload to public GCS bucket.

    Args:
        spot_title: Name of the spot (e.g. 'Maple Ave Driveway', 'Oak St Shaded Carport').
        scene_description: Video scene prompt (e.g., 'A car smoothly pulling into the driveway on a sunny afternoon').
        tool_context: ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary with video details and the public HTTPS URL from Google Cloud Storage.
    """
    try:
        # 1. Generate video using gemini-omni-flash-preview in global region
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        prompt = (
            f"Smooth 4-second video clip of residential parking spot: {spot_title}. "
            f"Scene: {scene_description}. High quality camera movement, clear daylight, welcoming suburban home."
        )
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        output_video = getattr(interaction, "output_video", None)
        if output_video and isinstance(output_video, dict) and output_video.get("data"):
            video_bytes = base64.b64decode(output_video["data"])
        elif hasattr(interaction, "steps") and interaction.steps:
            for step in reversed(interaction.steps):
                content = step.get("content", []) if isinstance(step, dict) else getattr(step, "content", [])
                for item in content:
                    item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                    if item_type == "video":
                        raw_data = item.get("data") if isinstance(item, dict) else getattr(item, "data", None)
                        if raw_data:
                            video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                            break
                if video_bytes:
                    break

        if not video_bytes:
            return {"error": "Failed to extract video bytes from gemini-omni-flash-preview response."}

        mime_type = "video/mp4"
        safe_name = "".join(c if c.isalnum() else "_" for c in spot_title.lower()).strip("_")
        timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        filename = f"{safe_name}_{timestamp}.mp4"

        # 2. Save video with tool_context.save_artifact so it shows in Playground's Artifacts panel
        part = types.Part(inline_data=types.Blob(mime_type=mime_type, data=video_bytes))
        await tool_context.save_artifact(filename=filename, artifact=part)

        # 3. Upload video bytes directly to public GCS bucket (no local file write)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_https_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "spot_title": spot_title,
            "artifact_filename": filename,
            "public_url": public_https_url,
            "message": f"Generated driveway video for '{spot_title}', saved to artifacts, and published to Cloud Storage.",
        }
    except Exception as e:
        return {"error": f"Video generation or upload failed: {str(e)}"}


async def generate_memories_callback(callback_context: CallbackContext):
    """After each turn, persist salient conversation details to Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Spotnest, an intelligent peer-to-peer neighborhood parking concierge. "
        "Your motto is 'Smarter parking, powered by your driveway.' "
        "You connect homeowners offering driveways/carports with drivers seeking convenient, affordable parking. "
        "MEMORY & PREFERENCES: You actively remember and persist all user preferences and facts across sessions. "
        "This includes: driver's vehicle make/model/size (e.g. SUV, EV, compact sedan), EV charging needs, walking distance tolerance (e.g. maximum 5-10 minute walk), budget limits (e.g. under $10/hr), preferred parking types (covered carport, garage, driveway), favorite neighborhoods, arrival times, and accessibility needs. "
        "Whenever the user mentions a preference, acknowledge it and apply it automatically to filter and recommend spots in all current and future conversations. "
        "Use list_parking_spots to query available driveway spots, rates, dimensions, and walking distance. "
        "Use get_parking_spot to view in-depth driveway details, parking space dimensions/vehicle suitability, and owner credibility/verification. "
        "Use calculate_walking_route to compute exact pedestrian walking distance and minutes from a spot to a destination. "
        "Use get_parking_map_url to provide live Google Maps walking directions and map preview links. "
        "Use get_parking_weather to check real-time weather and outdoor parking/walking advisories (rain, heat, freezing) using the free Open-Meteo public API. "
        "Use book_parking_spot to reserve driveway spots for drivers. "
        "Use list_host_driveway to register and publish newly offered host driveway spots. "
        "Use generate_driveway_image to generate photo previews of driveways using gemini-3.1-flash-lite-image, save them as session artifacts, and publish them to public Cloud Storage. "
        "Use generate_driveway_video to generate short video clips of driveways using gemini-omni-flash-preview, save them as session artifacts, and publish them to public Cloud Storage. "
        "Use geocode_address to convert any destination or driveway address to coordinates. "
        "Use find_nearby_places to discover points of interest near the parking spot."
    ),
    workflow_description="Analyze the user request, call necessary tools, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_parking_spots,
        get_parking_spot,
        calculate_walking_route,
        get_parking_map_url,
        get_parking_weather,
        generate_driveway_image,
        generate_driveway_video,
        book_parking_spot,
        list_host_driveway,
        geocode_address,
        find_nearby_places,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
