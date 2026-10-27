
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from controllers.geoapify_controller import (
    lookup_postcode,
    ZipNotFoundError,
    GeoapifyRequestError,
    InvalidZipError,
)


def mock_response(results):
    data = json.dumps({"results": results})
    return io.BytesIO(data.encode("utf-8"))


class TestGeoapifyController(unittest.TestCase):

    @patch(
        "controllers.geoapify_controller.get_geoapify_api_key",
        return_value="test-only-key"
    )
    @patch("controllers.geoapify_controller.urlopen")
    def test_success(self, mock_open, mock_key):
        mock_open.return_value = mock_response([
            {
                "postcode": "16802",
                "country_code": "us",
                "lat": 40.8,
                "lon": -77.86,
                "city": "State College"
            }
        ])

        result = lookup_postcode("16802")

        self.assertEqual(result["postcode"], "16802")
        self.assertEqual(result["country_code"], "us")
        self.assertEqual(result["latitude"], 40.8)
        self.assertEqual(result["longitude"], -77.86)
        self.assertEqual(result["locality"], "State College")
        self.assertEqual(mock_open.call_args.kwargs["timeout"], 8)

    @patch(
        "controllers.geoapify_controller.get_geoapify_api_key",
        return_value="test-only-key"
    )
    @patch("controllers.geoapify_controller.urlopen")
    def test_mismatched_location(self, mock_open, mock_key):
        mock_open.return_value = mock_response([
            {
                "postcode": "10001",
                "country_code": "us",
                "lat": 40.7,
                "lon": -74.0
            }
        ])

        with self.assertRaises(ZipNotFoundError):
            lookup_postcode("16802")

    @patch(
        "controllers.geoapify_controller.get_geoapify_api_key",
        return_value="test-only-key"
    )
    @patch("controllers.geoapify_controller.urlopen")
    def test_provider_failure(self, mock_open, mock_key):
        mock_open.side_effect = URLError("Simulated failure")

        with self.assertRaises(GeoapifyRequestError):
            lookup_postcode("16802")

    @patch(
        "controllers.geoapify_controller.get_geoapify_api_key",
        return_value="test-only-key"
    )
    @patch("controllers.geoapify_controller.urlopen")
    def test_invalid_coordinates(self, mock_open, mock_key):
        mock_open.return_value = mock_response([
            {
                "postcode": "16802",
                "country_code": "us",
                "lat": 999,
                "lon": -77.86
            }
        ])

        with self.assertRaises(ZipNotFoundError):
            lookup_postcode("16802")

    @patch("controllers.geoapify_controller.urlopen")
    def test_invalid_zip(self, mock_open):
        invalid_zips = [
            "123",
            "123456",
            "ABCDE",
            "12 34",
            "",
            "1234A",
            "16802-1234",
        ]

        for zipcode in invalid_zips:
            with self.subTest(zipcode=zipcode):
                with self.assertRaises(InvalidZipError):
                    lookup_postcode(zipcode)

        mock_open.assert_not_called()

    @patch(
        "controllers.geoapify_controller.get_geoapify_api_key",
        return_value="test-only-key"
    )
    @patch("controllers.geoapify_controller.urlopen")
    def test_leading_zero(self, mock_open, mock_key):
        mock_open.return_value = mock_response([
            {
                "postcode": "02108",
                "country_code": "us",
                "lat": 42.36,
                "lon": -71.06,
                "city": "Boston"
            }
        ])

        result = lookup_postcode("02108")

        self.assertEqual(result["postcode"], "02108")
        self.assertEqual(result["country_code"], "us")
        self.assertEqual(result["latitude"], 42.36)
        self.assertEqual(result["longitude"], -71.06)
        self.assertEqual(result["locality"], "Boston")


if __name__ == "__main__":
    unittest.main()

