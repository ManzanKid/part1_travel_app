"""Assignment 1 search and booking CRUD regression using a temporary DB."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers import database_controller as controller
from models.database import create_tables


class TestAssignmentOneDatabaseRegression(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_path = Path(handle.name)
        handle.close()
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        connection.execute(
            "INSERT INTO hotels VALUES ('H001', 'Harbor Lantern Hotel', 'Boston', 'MA', 129.50)"
        )
        connection.execute("INSERT INTO users VALUES ('U001', 'Demo Traveler')")
        connection.execute(
            "INSERT INTO trips VALUES ('T001', 'H001', 'Boston weekend', '2026-11-01', '2026-11-03')"
        )
        connection.commit()
        connection.close()

        def temp_connection():
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            return db

        self.connection_patch = patch.object(controller, "get_connection", temp_connection)
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        self.db_path.unlink(missing_ok=True)

    def test_hotel_search_and_booking_lifecycle(self):
        stays = controller.search_hotels("Harbor Lantern")
        self.assertEqual(len(stays), 1)
        self.assertEqual(stays[0]["hotel_id"], "H001")
        self.assertEqual(stays[0]["nightly_rate_usd"], 129.5)

        booking = controller.create_booking("U001", "T001")
        self.assertEqual(booking["booking_id"], "B001")
        self.assertEqual(len(controller.get_booking_history("U001")), 1)

        controller.cancel_booking("B001")
        self.assertEqual(controller.get_booking_history("U001")[0]["status"], "cancelled")

        controller.delete_booking("B001")
        self.assertEqual(controller.get_booking_history("U001"), [])


if __name__ == "__main__":
    unittest.main()
