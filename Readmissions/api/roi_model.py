"""
Itemised ROI model for a post-discharge care-coordination intervention.

WHY THIS EXISTS
---------------
The ROI figures used to be produced entirely by Gemini: it invented a lump-sum
readmission cost and a lump-sum intervention cost, did the arithmetic itself,
and returned five numbers with no breakdown. Nothing could be audited, nothing
was reproducible between two runs on the same patient, and nothing checked that
the five numbers were even consistent with each other.

Every figure below is now an explicit, named line item, the arithmetic is done
here in Python, and Gemini is left to write the narrative around numbers it did
not choose.

THESE ARE DEFAULTS, NOT FACTS ABOUT YOUR HOSPITAL
-------------------------------------------------
The line items are anchored on published US averages so the totals land in a
defensible range, but a health system should replace them with its own finance
figures. That is the point of itemising: every number is visible and separately
editable rather than buried in a prompt.

Public anchors used for the defaults:
  - AHRQ HCUP Statistical Brief 278: mean cost of an adult 30-day all-cause
    readmission is approximately 15,200 USD all-payer, and slightly higher for
    Medicare.
  - Mean readmission length of stay is approximately 5.2 days.
  - Meta-analyses of transitional-care and post-discharge follow-up programmes
    report a relative reduction in 30-day readmission of roughly 20-30%.

THE EFFECTIVENESS TERM
----------------------
The previous formula was:

    expected_cost_avoided = P(readmit) * readmission_cost

which silently assumes the intervention prevents EVERY readmission it is
applied to. It does not. Multiplying by an explicit effectiveness factor is the
difference between a ratio of about 32x and about 8x for the same patient, and
only the second survives a finance review.

NOT EVERY PATIENT HAS AN ROI CASE
---------------------------------
The arithmetic runs for any score, but below a certain risk it returns a
NEGATIVE net benefit: the coordinator hours cost more than the readmission they
are expected to avert. That break-even point falls straight out of the line
items above and is computed as BREAK_EVEN_RISK_PCT, currently about 9%.

Presenting "expected savings" for a low-risk, improving patient is worse than
useless - it implies enrolling them is free money when the model's own numbers
say the opposite. `roi_case` therefore returns a verdict alongside the figures,
and the UI leads with the verdict rather than the dollar amounts.

Trajectory matters as well as level. A patient at 55% whose risk is falling
week over week still clears break-even comfortably, so the case is to CONTINUE,
not to escalate; a patient below break-even whose risk is falling should be
stepped down. Level alone cannot express that, which is why the trend status
from the monitoring series is an input here.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# What one avoided readmission is worth
# ---------------------------------------------------------------------------
# Line items sum to the episode cost. Amounts are USD per readmission episode.
READMISSION_COST_ITEMS = [
    {
        "item": "Emergency department presentation and triage",
        "basis": "1 ED visit before admission",
        "amount": 1250.0,
    },
    {
        "item": "Inpatient bed-days",
        "basis": "5.2 days at 2,150 per day",
        "amount": 11180.0,
    },
    {
        "item": "Laboratory and diagnostic imaging",
        "basis": "per readmission episode",
        "amount": 1120.0,
    },
    {
        "item": "Pharmacy and procedures",
        "basis": "per readmission episode",
        "amount": 1450.0,
    },
    {
        "item": "Discharge planning for the return stay",
        "basis": "per readmission episode",
        "amount": 500.0,
    },
]

# ---------------------------------------------------------------------------
# What the intervention costs to deliver
# ---------------------------------------------------------------------------
# One patient, across the 30-day post-discharge monitoring window. Staff rates
# are fully loaded, i.e. salary plus employer costs and overhead.
INTERVENTION_COST_ITEMS = [
    {
        "item": "Care coordinator time",
        "basis": "3.5 hours at 48 per hour loaded",
        "amount": 168.0,
    },
    {
        "item": "Pharmacist medication reconciliation",
        "basis": "0.75 hours at 76 per hour loaded",
        "amount": 57.0,
    },
    {
        "item": "Remote monitoring device and data plan",
        "basis": "30 days amortised",
        "amount": 65.0,
    },
    {
        "item": "Appointment scheduling and transport support",
        "basis": "per enrolled patient",
        "amount": 40.0,
    },
    {
        "item": "Platform licence per monitored patient",
        "basis": "per enrolled patient per month",
        "amount": 20.0,
    },
]

# Relative reduction in 30-day readmission attributable to the intervention.
# Deliberately conservative within the 20-30% range reported for transitional
# care programmes; the whole ROI scales linearly with it.
INTERVENTION_EFFECTIVENESS = 0.25

READMISSION_COST_TOTAL = sum(i["amount"] for i in READMISSION_COST_ITEMS)
INTERVENTION_COST_TOTAL = sum(i["amount"] for i in INTERVENTION_COST_ITEMS)

# The risk at which expected avoided cost exactly equals delivery cost:
#
#   p x readmission_cost x effectiveness = intervention_cost
#
# Everything below this line is money lost, however well-intentioned. It is
# derived, not chosen, so editing any line item above moves it automatically.
BREAK_EVEN_RISK_PCT = round(
    INTERVENTION_COST_TOTAL / (READMISSION_COST_TOTAL * INTERVENTION_EFFECTIVENESS) * 100, 1)


# Trend statuses from the monitoring series that mean "getting better".
_IMPROVING = {"improving"}
_WORSENING = {"deteriorating", "action_required"}


def roi_case(risk_score: float, trend_status: Optional[str] = None) -> dict:
    """
    Whether there is a case for intervening at all, and what to do instead.

    Returns a verdict the UI leads with, so a patient who is low-risk or
    recovering is never shown a savings figure as though enrolling them were
    free money. `show_roi` is the flag for that: when it is false the dollar
    amounts are still computed and still available behind a disclosure, they
    just stop being the headline.
    """
    p = max(0.0, min(1.0, float(risk_score) / 100.0))
    avoidable = p * READMISSION_COST_TOTAL * INTERVENTION_EFFECTIVENESS
    net = avoidable - INTERVENTION_COST_TOTAL
    improving = trend_status in _IMPROVING
    worsening = trend_status in _WORSENING

    if net < 0:
        shortfall = abs(round(net))
        if improving:
            return {
                "decision": "step_down",
                "label": "No intervention case - step monitoring down",
                "reason": (
                    f"Risk is falling and now sits below the {BREAK_EVEN_RISK_PCT}% "
                    f"break-even point for this programme. Enrolling this patient would "
                    f"cost about ${shortfall:,} more than the readmission it would be "
                    f"expected to avert, so the value here is in reducing check-in "
                    f"frequency, not in adding a coordinator."),
                "show_roi": False,
            }
        if worsening:
            # Rising but still cheap to leave alone. Saying only "no case"
            # would hide the direction, and enrolling now would spend money the
            # arithmetic does not yet support - so the action is to re-check.
            return {
                "decision": "watch",
                "label": "Below break-even, but the trend is upward",
                "reason": (
                    f"At {risk_score:.1f}% the intervention would still cost about "
                    f"${abs(round(net)):,} more than it is expected to save, so enrolling "
                    f"now is not justified. Risk is rising though, and it becomes "
                    f"cost-effective at {BREAK_EVEN_RISK_PCT}%. Keep monitoring weekly "
                    f"and re-assess at the next score."),
                "show_roi": False,
            }
        return {
            "decision": "monitor_only",
            "label": "No intervention case - routine monitoring",
            "reason": (
                f"At {risk_score:.1f}% this patient is below the "
                f"{BREAK_EVEN_RISK_PCT}% break-even point, where the expected cost of "
                f"a readmission stops covering the ${INTERVENTION_COST_TOTAL:,.0f} it "
                f"costs to deliver the intervention. Continue routine monitoring and "
                f"re-assess if the score rises."),
            "show_roi": False,
        }

    if improving:
        return {
            "decision": "continue",
            "label": "Continue current plan - do not escalate",
            "reason": (
                f"The intervention still pays for itself at {risk_score:.1f}%, but risk "
                f"is falling week over week, so the plan already in place is working. "
                f"The case is to keep going and re-check next week, not to add "
                f"intensity. Value below assumes the trend does not continue."),
            "show_roi": True,
        }

    if worsening:
        return {
            "decision": "escalate",
            "label": "Intervene now - risk is rising",
            "reason": (
                f"At {risk_score:.1f}% the expected avoided cost is well clear of the "
                f"${INTERVENTION_COST_TOTAL:,.0f} delivery cost, and the trajectory is "
                f"upward rather than flat. This is the point in the window where "
                f"contact is worth most."),
            "show_roi": True,
        }

    return {
        "decision": "intervene",
        "label": "Intervention is cost-effective",
        "reason": (
            f"At {risk_score:.1f}% this patient is above the "
            f"{BREAK_EVEN_RISK_PCT}% break-even point, so the expected avoided cost "
            f"exceeds what the intervention costs to deliver."),
        "show_roi": True,
    }


def compute_roi(risk_score: float,
                effectiveness: Optional[float] = None,
                readmission_cost: Optional[float] = None,
                intervention_cost: Optional[float] = None,
                trend_status: Optional[str] = None) -> dict:
    """
    Turn a risk score into an itemised ROI breakdown.

        gross_exposure = P(readmit) x readmission_cost
        avoidable      = gross_exposure x effectiveness
        net_benefit    = avoidable - intervention_cost
        roi_ratio      = avoidable / intervention_cost

    `risk_score` is a percentage, matching what the dashboard displays.

    Returns every intermediate figure plus the line items behind the two cost
    totals, so the UI can show exactly what was added and what was subtracted.
    """
    p = max(0.0, min(1.0, float(risk_score) / 100.0))
    eff = INTERVENTION_EFFECTIVENESS if effectiveness is None else float(effectiveness)
    rc = READMISSION_COST_TOTAL if readmission_cost is None else float(readmission_cost)
    ic = INTERVENTION_COST_TOTAL if intervention_cost is None else float(intervention_cost)

    gross_exposure = p * rc
    avoidable = gross_exposure * eff
    net_benefit = avoidable - ic
    ratio = (avoidable / ic) if ic else 0.0

    return {
        "risk_probability": round(p, 4),
        "intervention_effectiveness": eff,

        "readmission_cost_items": READMISSION_COST_ITEMS,
        "estimated_readmission_cost_usd": round(rc, 2),

        "intervention_cost_items": INTERVENTION_COST_ITEMS,
        "estimated_intervention_cost_usd": round(ic, 2),

        # The three steps, each shown so the arithmetic can be followed.
        "gross_exposure_usd": round(gross_exposure, 2),
        "expected_cost_avoided_usd": round(avoidable, 2),
        "net_roi_usd": round(net_benefit, 2),
        "roi_ratio": round(ratio, 2),

        # The risk below which this arithmetic returns a loss, and the verdict
        # that follows from where this patient sits relative to it.
        "break_even_risk_pct": BREAK_EVEN_RISK_PCT,
        "case": roi_case(risk_score, trend_status),

        "calculation_steps": [
            {
                "step": "Exposure",
                "formula": f"{p:.3f} readmission probability x ${rc:,.0f} episode cost",
                "amount": round(gross_exposure, 2),
            },
            {
                "step": "Avoidable share",
                "formula": f"${gross_exposure:,.0f} x {eff:.0%} intervention effectiveness",
                "amount": round(avoidable, 2),
            },
            {
                "step": "Less intervention cost",
                "formula": f"${avoidable:,.0f} minus ${ic:,.0f} delivery cost",
                "amount": round(net_benefit, 2),
            },
        ],

        "assumptions": [
            f"Only {eff:.0%} of the expected readmission cost is treated as avoidable, "
            "which is the relative reduction reported for transitional care programmes. "
            "The remaining risk is assumed to materialise regardless.",
            "Costs are gross episode costs, not net of reimbursement, and exclude any "
            "readmissions-reduction penalty exposure.",
            "Line items are published-average defaults and should be replaced with the "
            "organisation's own finance figures before the number is used to plan.",
        ],
    }
