"""scripts/pin_demo_patient.py: MIMIC-10683325 keeps its original readings and
wording, and only week 4's risk changes."""
import mongomock
import pytest

from scripts import pin_demo_patient as pin

PID = "MIMIC-10683325"


@pytest.fixture
def db():
    d = mongomock.MongoClient()["neuroshield"]
    for wk, score in enumerate([57.5, 85.8, 96.0, 96.0, 96.0]):     # what the new run writes
        d.weekly_monitoring.insert_one({"patient_id": PID, "week_number": wk, "risk_score": score,
                                        "source": "simulated", "clinical_group": "mental_health",
                                        "driver_1": "new text", "red_flags": []})
    return d


def weeks(db):
    return {d["week_number"]: d for d in db.weekly_monitoring.find({"patient_id": PID})}


def test_the_series_is_the_original_except_week_4(db):
    pin.pin(db)
    w = weeks(db)
    assert [w[k]["risk_score"] for k in range(5)] == [57.5, 83.2, 87.4, 89.9, 96.0]
    assert w[0]["driver_1"] == "new text"                            # discharge untouched
    assert w[4]["driver_3"].startswith("Oxygen saturation: 85% (")
    assert all(w[k]["risk_band"] == "High" for k in range(1, 5))


def test_only_week_4_carries_a_red_flag(db):
    pin.pin(db)
    w = weeks(db)
    assert w[4]["red_flags"] == ["spo2"] and not any(w[k]["red_flags"] for k in (1, 2, 3))


def test_every_driver_keeps_the_card_format(db):
    """The API splits "<label>: <value> (<explanation>)" on the last " (".""" 
    for spec in pin.PINNED[PID].values():
        for d in spec["drivers"]:
            assert d.count(" (") == 1 and d.endswith(")")


def test_the_readings_are_the_simulators_own():
    """Nothing on the cards is invented: seed 42, patient index 271, 4 weeks."""
    np = pytest.importorskip("numpy")
    sim = pytest.importorskip("scripts.simulate_weekly_monitoring")
    severity = np.random.default_rng(42 + 7).uniform(0.55, 1.35, size=272)[271]
    rng = np.random.default_rng(42 + 271 * 97)
    for wk in range(1, 5):
        assert rng.random() > sim.NO_CONTACT_RATE                    # contacted every week
        obs = sim.observe_week(wk, 4, True, float(severity), rng, group="mental_health",
                               groups=["mental_health", "general"])
        assert obs == pin.PINNED[PID][wk]["monitoring"], wk


def test_a_dry_run_writes_nothing(db):
    before = list(db.weekly_monitoring.find({}, {"_id": 0}))
    pin.pin(db, dry=True)
    assert list(db.weekly_monitoring.find({}, {"_id": 0})) == before


def test_six_week_data_is_refused(db):
    db.weekly_monitoring.insert_one({"patient_id": PID, "week_number": 5, "risk_score": 90})
    with pytest.raises(SystemExit):
        pin.pin(db)
    assert weeks(db)[1]["risk_score"] == 85.8
