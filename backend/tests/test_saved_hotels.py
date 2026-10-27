import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers import database_controller as controller
from models.database import create_tables


class TestSavedHotelMutations(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_path = Path(handle.name)
        handle.close()
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        connection.close()

        def temp_connection():
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            return db

        self.connection_patch = patch.object(controller, "get_connection", temp_connection)
        self.connection_patch.start()
        self.hotel = {"place_id": "provider-1", "name": "Test Hotel", "address": "1 Main St", "latitude": 40.8, "longitude": -77.8}
        self.location = {"postcode": "16802", "locality": "State College", "country_code": "us", "latitude": 40.8, "longitude": -77.8}

    def tearDown(self):
        self.connection_patch.stop()
        self.db_path.unlink(missing_ok=True)

    def test_repeat_save_preserves_single_hotel_context_and_nights(self):
        controller.save_api_hotel(self.hotel, "16802", self.location)
        connection = controller.get_connection()
        connection.execute("UPDATE demo_hotel_nights SET nightly_rate_cents=12345, rooms_available=3 WHERE hotel_id='provider-1' AND stay_date='2026-10-10'")
        connection.commit()
        connection.close()
        controller.save_api_hotel({**self.hotel, "name": "Changed name"}, "16802", self.location)
        connection = controller.get_connection()
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0], 1)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM saved_hotel_locations").fetchone()[0], 1)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM demo_hotel_nights").fetchone()[0], 5)
        self.assertEqual(tuple(connection.execute("SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights WHERE stay_date='2026-10-10'").fetchone()), (12345, 3))
        self.assertEqual(connection.execute("SELECT name FROM saved_hotels").fetchone()[0], "Test Hotel")
        connection.close()

    def test_delete_cascades_saved_children_and_preserves_unrelated_hotel(self):
        controller.save_api_hotel(self.hotel, "16802", self.location)
        controller.save_api_hotel({**self.hotel, "place_id": "provider-2"}, "02108", {**self.location, "postcode": "02108"})
        controller.remove_saved_hotel("provider-1")
        connection = controller.get_connection()
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0], 1)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM saved_hotel_locations WHERE hotel_id='provider-1'").fetchone()[0], 0)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM demo_hotel_nights WHERE hotel_id='provider-1'").fetchone()[0], 0)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM saved_hotels WHERE hotel_id='provider-2'").fetchone()[0], 1)
        connection.close()

    def test_zip_lookup_uses_context_and_demo_values(self):
        controller.save_api_hotel(self.hotel, "16802", self.location)
        hotels = controller.get_saved_hotels("16802")
        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0]["locality"], "State College")
        self.assertEqual(hotels[0]["nights"][0]["nightly_rate_cents"], 10000)
        self.assertEqual(hotels[0]["nights"][0]["rooms_available"], 20)
        self.assertEqual(controller.get_saved_hotels("10001"), [])


if __name__ == "__main__":
    unittest.main()
