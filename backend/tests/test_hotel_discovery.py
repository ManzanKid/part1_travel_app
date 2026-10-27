
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from controllers.hotel_discovery_controller import discover_hotels
from controllers.geoapify_controller import (
    ZipNotFoundError,
    GeoapifyRequestError,
)


def mock_response(features):
    data = json.dumps({"features": features})
    return io.BytesIO(data.encode("utf-8"))


def make_hotel(place_id, name, latitude, longitude):
    return {
        "type": "Feature",
        "properties": {
            "place_id": place_id,
            "name": name,
            "formatted": "Example address",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude],
        },
    }


class TestHotelDiscovery(unittest.TestCase):

    def setUp(self):
        # Mock ZIP lookup so tests never contact Geoapify.
        lookup_patcher = patch(
            "controllers.hotel_discovery_controller.lookup_postcode",
            return_value={
                "postcode": "16802",
                "country_code": "us",
                "latitude": 40.8,
                "longitude": -77.86,
                "locality": "State College",
            },
        )

        key_patcher = patch(
            "controllers.hotel_discovery_controller.get_geoapify_api_key",
            return_value="test-only-key",
        )

        request_patcher = patch(
            "controllers.hotel_discovery_controller.urlopen"
        )

        self.mock_lookup = lookup_patcher.start()
        self.mock_key = key_patcher.start()
        self.mock_open = request_patcher.start()

        self.addCleanup(lookup_patcher.stop)
        self.addCleanup(key_patcher.stop)
        self.addCleanup(request_patcher.stop)

    def test_success(self):
        self.mock_open.return_value = mock_response([
            make_hotel(
                "hotel-001",
                "Example Hotel",
                40.801,
                -77.861,
            )
        ])

        result = discover_hotels("16802")

        self.assertEqual(result["location"]["postcode"], "16802")
        self.assertEqual(result["radius_meters"], 5000)
        self.assertEqual(len(result["hotels"]), 1)

        hotel = result["hotels"][0]

        self.assertEqual(hotel["place_id"], "hotel-001")
        self.assertEqual(hotel["name"], "Example Hotel")
        self.assertLessEqual(hotel["distance_meters"], 5000)

        self.mock_lookup.assert_called_once_with("16802")

        # Verify the outbound request parameters.
        request = self.mock_open.call_args.args[0]
        params = parse_qs(urlparse(request.full_url).query)

        self.assertEqual(
            params["categories"],
            ["accommodation.hotel"],
        )
        self.assertEqual(
            params["filter"],
            ["circle:-77.86,40.8,5000"],
        )
        self.assertEqual(
            self.mock_open.call_args.kwargs["timeout"],
            8,
        )

    def test_no_hotels(self):
        self.mock_open.return_value = mock_response([])

        result = discover_hotels("16802")

        self.assertEqual(result["hotels"], [])
        self.assertEqual(result["radius_meters"], 5000)

    def test_outside_radius(self):
        self.mock_open.return_value = mock_response([
            make_hotel(
                "hotel-far",
                "Far Away Hotel",
                40.95,
                -77.86,
            )
        ])

        result = discover_hotels("16802")

        self.assertEqual(result["hotels"], [])

    def test_duplicate_hotels(self):
        self.mock_open.return_value = mock_response([
            make_hotel(
                "hotel-001",
                "Example Hotel",
                40.801,
                -77.861,
            ),
            make_hotel(
                "hotel-001",
                "Example Hotel",
                40.801,
                -77.861,
            ),
        ])

        result = discover_hotels("16802")

        self.assertEqual(len(result["hotels"]), 1)

    def test_provider_failure(self):
        self.mock_open.side_effect = URLError(
            "Simulated provider failure"
        )

        with self.assertRaises(GeoapifyRequestError):
            discover_hotels("16802")

    def test_unresolved_zip(self):
        self.mock_lookup.side_effect = ZipNotFoundError()

        with self.assertRaises(ZipNotFoundError):
            discover_hotels("16802")

        # No Places API request should happen.
        self.mock_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
