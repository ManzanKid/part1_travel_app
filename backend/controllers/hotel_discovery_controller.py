
import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import get_geoapify_api_key
from controllers.geoapify_controller import (
    lookup_postcode,
    GeoapifyConfigurationError,
    GeoapifyRequestError,
)

RADIUS_METERS = 5000


def distance_meters(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two points."""
    r = 6371000
    a1, a2 = math.radians(lat1), math.radians(lat2)
    da = a2 - a1
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(da / 2) ** 2
        + math.cos(a1) * math.cos(a2) * math.sin(dl / 2) ** 2
    )
    return 2 * r * math.asin(min(1, math.sqrt(a)))


def discover_hotels(postcode: str) -> dict:
    """Find hotels within 5 km of a verified U.S. postcode."""

    # Existing controller validates and resolves the ZIP.
    location = lookup_postcode(postcode)
    latitude = location["latitude"]
    longitude = location["longitude"]

    api_key = get_geoapify_api_key()
    if not api_key:
        raise GeoapifyConfigurationError(
            "Geoapify is not configured"
        )

    params = {
        "categories": "accommodation.hotel",
        "filter": f"circle:{longitude},{latitude},{RADIUS_METERS}",
        "bias": f"proximity:{longitude},{latitude}",
        "limit": 100,
        "apiKey": api_key,
    }

    request = Request(
        "https://api.geoapify.com/v2/places?" + urlencode(params),
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            data = json.load(response)
    except (HTTPError, URLError, OSError, ValueError):
        raise GeoapifyRequestError(
            "Hotel lookup service failed"
        ) from None

    if not isinstance(data, dict) or not isinstance(
        data.get("features"), list
    ):
        raise GeoapifyRequestError(
            "Hotel lookup returned an invalid response"
        )

    hotels = []
    seen_ids = set()

    for feature in data["features"]:
        if not isinstance(feature, dict):
            continue

        properties = feature.get("properties")
        geometry = feature.get("geometry")

        if not isinstance(properties, dict):
            continue
        if not isinstance(geometry, dict):
            continue

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
            continue

        try:
            lon = float(coordinates[0])
            lat = float(coordinates[1])
        except (TypeError, ValueError):
            continue

        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            continue

        distance = distance_meters(latitude, longitude, lat, lon)

        if distance > RADIUS_METERS:
            continue

        place_id = properties.get("place_id") or feature.get("id")
        if not place_id or place_id in seen_ids:
            continue

        seen_ids.add(place_id)

        hotels.append({
            "place_id": place_id,
            "name": properties.get("name") or None,
            "address": properties.get("formatted") or None,
            "latitude": lat,
            "longitude": lon,
            "distance_meters": round(distance),
        })

    return {
        "location": location,
        "radius_meters": RADIUS_METERS,
        "hotels": hotels,
    }
