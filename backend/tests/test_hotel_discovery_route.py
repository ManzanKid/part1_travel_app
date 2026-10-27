
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from main import discover_nearby_hotels

from controllers.geoapify_controller import (
    InvalidZipError,
    ZipNotFoundError,
    GeoapifyConfigurationError,
    GeoapifyRequestError,
)


class TestHotelDiscoveryRoute(unittest.TestCase):

    @patch("main.discover_hotels")
    def test_success(self, mock_discover):
        mock_discover.return_value = {
            "location": {
                "postcode": "16802",
                "country_code": "us",
                "latitude": 40.8,
                "longitude": -77.86,
                "locality": "State College",
            },
            "radius_meters": 5000,
            "hotels": [
                {
                    "place_id": "mock-hotel-001",
                    "name": "Mock Hotel",
                    "address": "Example address",
                    "latitude": 40.801,
                    "longitude": -77.861,
                    "distance_meters": 140,
                }
            ],
        }

        result = discover_nearby_hotels("16802")

        self.assertEqual(result["location"]["postcode"], "16802")
        self.assertEqual(result["radius_meters"], 5000)
        self.assertEqual(len(result["hotels"]), 1)
        mock_discover.assert_called_once_with("16802")

    @patch("main.discover_hotels")
    def test_invalid_zip(self, mock_discover):
        mock_discover.side_effect = InvalidZipError()

        with self.assertRaises(HTTPException) as error:
            discover_nearby_hotels("123")

        self.assertEqual(error.exception.status_code, 422)

    @patch("main.discover_hotels")
    def test_unresolved_zip(self, mock_discover):
        mock_discover.side_effect = ZipNotFoundError()

        with self.assertRaises(HTTPException) as error:
            discover_nearby_hotels("99999")

        self.assertEqual(error.exception.status_code, 404)

    @patch("main.discover_hotels")
    def test_missing_configuration(self, mock_discover):
        mock_discover.side_effect = GeoapifyConfigurationError()

        with self.assertRaises(HTTPException) as error:
            discover_nearby_hotels("16802")

        self.assertEqual(error.exception.status_code, 503)

    @patch("main.discover_hotels")
    def test_provider_failure(self, mock_discover):
        mock_discover.side_effect = GeoapifyRequestError()

        with self.assertRaises(HTTPException) as error:
            discover_nearby_hotels("16802")

        self.assertEqual(error.exception.status_code, 502)

    @patch("main.discover_hotels")
    def test_leading_zero(self, mock_discover):
        mock_discover.return_value = {
            "location": {
                "postcode": "02108",
                "country_code": "us",
                "latitude": 42.36,
                "longitude": -71.06,
            },
            "radius_meters": 5000,
            "hotels": [],
        }

        result = discover_nearby_hotels("02108")

        self.assertEqual(result["location"]["postcode"], "02108")
        mock_discover.assert_called_once_with("02108")


if __name__ == "__main__":
    unittest.main()
