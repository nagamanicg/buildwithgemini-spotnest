# 🚗 Spotnest — Smarter Parking, Powered by Your Driveway

> A peer-to-peer neighborhood parking concierge connecting homeowners with unused driveways and carports to drivers looking for convenient, affordable parking.

<div align="center">
  <img src="spotnest_demo.gif" alt="Spotnest AI Driveway Demo" width="600" />
  <p><em>AI-generated driveway parking simulation powered by <code>gemini-omni-flash-preview</code></em></p>
</div>

Built with Google's **Agent Development Kit (ADK)** and `agents-cli`, deployed on **Agent Platform**, and served via an A2A chat interface.

---

## 🌟 What Spotnest Does

Spotnest acts as an intelligent neighborhood parking concierge that assists both drivers and homeowners:

- **Find & Filter Neighborhood Parking**: Searches real-time driveway inventory stored in Firestore by location, maximum hourly rate, and availability.
- **Detailed Space Inspection**: Retrieves spot dimensions, vehicle clearance (compact, SUV, EV), and host verification badges.
- **Walking Route & Foot Network Calculation**: Computes real pedestrian walking duration and distances to destination venues using OSRM foot routing and OpenStreetMap geocoding.
- **Live Google Maps Links**: Generates instant walking route links and map search URLs.
- **Microclimate & Parking Weather Advisories**: Queries the Open-Meteo API for real-time temperature, precipitation, and conditions to advise drivers on covered carports vs. open driveways and walking weather.
- **Driveway Reservations**: Records driver bookings directly into Firestore with automated pricing calculation.
- **Homeowner Listings**: Enables hosts to list their driveway or carport with custom hourly rates and amenities.
- **AI Driveway Photo Generation**: Synthesizes photorealistic driveway previews using `gemini-3.1-flash-lite-image`, saves them to the session artifact store, and publishes them to Google Cloud Storage.
- **AI Driveway Video Generation**: Generates 4-second video walkthroughs using Google's Omni model (`gemini-omni-flash-preview`) in the global region, saves them as session artifacts, and publishes them to Google Cloud Storage.
- **Cross-Session Memory**: Actively remembers driver vehicle profiles (EV, SUV, compact), charging requirements, walking tolerances, and budget caps across conversations using Vertex AI Memory Bank.
- **A2UI Rich Surfaces**: Returns structured cards, columns, rows, and image components rendered natively in the UI.

---

## 🛠️ Wired Google Cloud Services & Tools

Spotnest implements and connects the following technologies:

| Layer / Service | Technology | Role in Spotnest |
|---|---|---|
| **Agent Reasoning** | ADK + `gemini-3.6-flash` | Orchestrates search, route calculation, booking, and dialogue flow. |
| **Long-Term Memory** | Vertex AI Memory Bank | Automatically persists driver preferences across sessions via `PreloadMemoryTool` and callbacks. |
| **Database** | Google Cloud Firestore | Houses `parking_spots` and `parking_bookings` collections. |
| **Media Storage** | Google Cloud Storage | Stores generated driveway preview images and videos with public URLs. |
| **Image Generation** | `gemini-3.1-flash-lite-image` | Generates architectural photos of driveways and carports. |
| **Video Generation** | `gemini-omni-flash-preview` | Generates short video clips of driveway parking spaces. |
| **Agent UI** | A2UI (v0.8) | Emits structured JSON schemas rendered into responsive UI cards. |
| **External APIs** | Open-Meteo & OSRM | Provides real-time weather advisories and pedestrian route calculations without paid keys. |
| **Mapping** | Google Maps Platform | Geocoding, Nearby Places, and directions links. |

---

## 📋 Real Tools Registered on the Agent

Inspected from [`app/agent.py`](app/agent.py):

1. `PreloadMemoryTool`: Fetches user memories from Memory Bank before each turn.
2. `list_parking_spots`: Queries Firestore for available driveway spots under a maximum price.
3. `get_parking_spot`: Retrieves details, dimensions, and host verification for a specific spot.
4. `calculate_walking_route`: Calculates pedestrian walking minutes and miles to destination.
5. `get_parking_map_url`: Generates Google Maps directions and search URLs.
6. `get_parking_weather`: Fetches weather conditions and parking advisories via Open-Meteo.
7. `book_parking_spot`: Creates a confirmed reservation record in Firestore.
8. `list_host_driveway`: Adds a new host driveway listing to Firestore.
9. `generate_driveway_image`: Generates photos using `gemini-3.1-flash-lite-image` and publishes to Cloud Storage.
10. `generate_driveway_video`: Generates video clips using `gemini-omni-flash-preview` and publishes to Cloud Storage.
11. `geocode_address`: Resolves street addresses to coordinates via Google Maps Geocoding API.
12. `find_nearby_places`: Finds nearby coffee shops, gas stations, and EV chargers via Google Places API.

---

## 🚀 Running Locally

### 1. Prerequisites
- Python 3.11+
- `uv` package manager
- Authenticated Google Cloud SDK (`gcloud auth login` and `gcloud auth application-default login`)

### 2. Setup the Agent

```bash
cd spotnest
uv sync
```

### 3. Run the ADK Web Playground

To run the local ADK developer playground with Memory Bank connected:

```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<MEMORY_BANK_RESOURCE_ID>
```

### 4. Run the Web Frontend Proxy

To run the standalone FastAPI proxy and chat interface:

```bash
cd spotnest/frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<REASONING_ENGINE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```

The frontend will start on port `8080` and connect to the agent over the A2A protocol.

---

## 📂 Project Structure

```text
spotnest/
├── app/
│   ├── agent.py               # Root agent, tools, system instructions, and callbacks
│   ├── a2ui_utils.py          # A2UI callback and data envelope handling
│   └── __init__.py
├── frontend/
│   ├── main.py                # FastAPI proxy communicating via A2A
│   ├── requirements.txt       # Frontend proxy dependencies
│   └── static/
│       └── index.html         # Spotnest branded chat UI & A2UI card renderer
├── agents-cli-manifest.yaml   # Deployment manifest for Agent Runtime
├── deployment_metadata.json   # Deployed Reasoning Engine resource metadata
└── pyproject.toml             # Project dependencies and configuration
```
