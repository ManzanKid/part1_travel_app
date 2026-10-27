
import json
import math
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import get_geoapify_api_key


class ZipNotFoundError(Exception):
    """No matching U.S. ZIP code was found."""


class GeoapifyRequestError(Exception):
    """The Geoapify request could not be completed."""

class GeoapifyConfigurationError(Exception):
    """Geoapify API key is missing."""

class InvalidZipError(Exception):
    """ZIP code must contain exactly five digits."""

def lookup_postcode(postcode: str) -> dict:
    """Look up a U.S. ZIP code using Geoapify."""
    if not isinstance(postcode, str) or not re.fullmatch(r"[0-9]{5}", postcode):
        raise InvalidZipError("Enter a valid five-digit U.S. ZIP code.")
    
    api_key = get_geoapify_api_key()

    if not api_key:
        raise GeoapifyConfigurationError(
        "Geoapify is not configured"
    )

    params = {
        "postcode": postcode,
        "type": "postcode",
        "filter": "countrycode:us",
        "format": "json",
        "apiKey": api_key,
    }

    request = Request(
        "https://api.geoapify.com/v1/geocode/search?"
        + urlencode(params),
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            data = json.load(response)
    except (HTTPError, URLError, OSError, ValueError, UnicodeError):
        raise GeoapifyRequestError(
            "Geoapify request failed"
        ) from None

    if not isinstance(data, dict) or not isinstance(
        data.get("results"), list
    ):
        raise GeoapifyRequestError(
            "Geoapify returned an invalid response"
        )

    for item in data["results"]:
        if not isinstance(item, dict):
            continue

        if str(item.get("postcode", "")).strip() != postcode:
            continue

        if str(item.get("country_code", "")).lower() != "us":
            continue

        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
        ):
            continue

        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            continue

        result = {
            "postcode": postcode,
            "country_code": "us",
            "latitude": latitude,
            "longitude": longitude,
        }

        for field in ("city", "town", "village", "suburb"):
            locality = item.get(field)
            if isinstance(locality, str) and locality.strip():
                result["locality"] = locality.strip()
                break

        return result

    raise ZipNotFoundError(
        "No matching U.S. ZIP code found"
    )
