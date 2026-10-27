
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from main import demo_zip_location
from controllers.geoapify_controller import (
    GeoapifyConfigurationError,
    GeoapifyRequestError,
    ZipNotFoundError,
)


class TestGeoapifyRoute(unittest.TestCase):

    @patch("main.lookup_postcode")
    def test_success(self, mock_lookup):
        mock_lookup.return_value = {
            "postcode": "16802",
            "country_code": "us",
            "latitude": 40.8,
            "longitude": -77.86,
            "locality": "State College",
        }

        response = demo_zip_location()

        self.assertEqual(response["postcode"], "16802")
        mock_lookup.assert_called_once_with("16802")

    @patch("main.lookup_postcode")
    def test_missing_configuration(self, mock_lookup):
        mock_lookup.side_effect = GeoapifyConfigurationError()

        with self.assertRaises(HTTPException) as error:
            demo_zip_location()

        self.assertEqual(error.exception.status_code, 503)

    @patch("main.lookup_postcode")
    def test_unresolved_zip(self, mock_lookup):
        mock_lookup.side_effect = ZipNotFoundError()

        with self.assertRaises(HTTPException) as error:
            demo_zip_location()

        self.assertEqual(error.exception.status_code, 404)

    @patch("main.lookup_postcode")
    def test_provider_failure(self, mock_lookup):
        mock_lookup.side_effect = GeoapifyRequestError()

        with self.assertRaises(HTTPException) as error:
            demo_zip_location()

        self.assertEqual(error.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
