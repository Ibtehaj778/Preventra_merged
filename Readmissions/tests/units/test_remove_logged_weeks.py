"""scripts/remove_logged_weeks.py removes only the weeks the simulator did not write."""
import mongomock

from scripts import remove_logged_weeks as script


def test_only_non_simulated_weeks_are_listed_and_removed():
    db = mongomock.MongoClient()["neuroshield"]
    for wk in range(5):
        db.weekly_monitoring.insert_one({"patient_id": "MIMIC-1", "week_number": wk, "source": "simulated"})
    for wk in (5, 6):
        db.weekly_monitoring.insert_one({"patient_id": "MIMIC-1", "week_number": wk,
                                         "source": "patient_reported", "week_date": "2026-09-04"})
    found = script.logged_weeks(db)
    assert [d["week_number"] for d in found] == [5, 6]
    assert script.remove(db, found) == 2
    assert sorted(d["week_number"] for d in db.weekly_monitoring.find()) == [0, 1, 2, 3, 4]
    assert script.remove(db, []) == 0
