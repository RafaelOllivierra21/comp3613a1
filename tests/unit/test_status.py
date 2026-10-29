from app.utilities.status import status_badge_class, status_label
import unittest


class StatusUnitTests(unittest.TestCase):
    def test_status_label(self):
        assert status_label("awaiting_rematch") == "Awaiting Rematch"


    def test_status_badge_class(self):
        assert status_badge_class("rejected by company") == "status-badge status-negative"
