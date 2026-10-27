from datetime import date

from src.edtech_service import CourseListing, report_status


def test_report_marks_a_listing_open_until_its_learner_deadline():
    listing = CourseListing("Checkout Analytics", "https://example.test/course", date(2026, 11, 1), "self-paced")

    assert report_status(listing, date(2026, 10, 24)) == "open"
    assert report_status(listing, date(2026, 11, 2)) == "closed"
