

def test_suggested_actions_share_the_roi_verdict():
    from api.roi_model import roi_case, suggested_actions
    for score, status in [(41.1, "improving"), (70, "deteriorating"), (70, "stable"),
                          (5, "improving"), (5, "deteriorating"), (5, "stable")]:
        plan = suggested_actions(score, status)
        case = roi_case(score, status)
        assert (plan["decision"], plan["label"]) == (case["decision"], case["label"])
        assert plan["actions"]
