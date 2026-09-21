"""
GLP-1 Analytics Platform — Phase 1 Data Processing
ClinicalTrials.gov: SUSTAIN, STEP, and SURMOUNT Trial Families

Pulls study metadata, outcome results, adverse events, and baseline
characteristics via the ClinicalTrials.gov API v2 (no registration needed).

Requirements: pip install requests pandas
"""

import requests
import pandas as pd
import time
import os
import json

# ── CONFIG ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# Trial families and their NCT IDs
TRIALS = {
    # SUSTAIN — Semaglutide injectable for T2D
    "SUSTAIN-1":  "NCT02054897",
    "SUSTAIN-2":  "NCT01930188",
    "SUSTAIN-3":  "NCT01885208",
    "SUSTAIN-4":  "NCT02128932",
    "SUSTAIN-5":  "NCT02305381",
    "SUSTAIN-6":  "NCT01720446",
    "SUSTAIN-7":  "NCT02648204",
    "SUSTAIN-8":  "NCT03136009",
    "SUSTAIN-9":  "NCT03086330",
    "SUSTAIN-10": "NCT03191396",

    # STEP — Semaglutide 2.4mg for obesity/weight management
    "STEP-1":  "NCT03548935",
    "STEP-2":  "NCT03552757",
    "STEP-3":  "NCT03611582",
    "STEP-4":  "NCT03548987",
    "STEP-5":  "NCT04074161",

    # SURMOUNT — Tirzepatide for obesity/weight management
    "SURMOUNT-1": "NCT04184622",
    "SURMOUNT-2": "NCT04657003",
    "SURMOUNT-3": "NCT04657016",
    "SURMOUNT-4": "NCT04660643",
}

RATE_LIMIT_SECONDS = 0.5  # polite delay between API calls


def fetch_study(nct_id):
    """Fetch a single study from ClinicalTrials.gov API v2."""
    url = f"{BASE_URL}/{nct_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_metadata(study, trial_name, nct_id):
    """Extract study-level metadata."""
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    design = ps.get("designModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})

    design_info = design.get("designInfo", {})
    enroll = design.get("enrollmentInfo", {})

    return {
        "trial_name": trial_name,
        "nct_id": nct_id,
        "brief_title": ident.get("briefTitle", ""),
        "official_title": ident.get("officialTitle", ""),
        "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
        "overall_status": status.get("overallStatus", ""),
        "phase": ", ".join(design.get("phases", [])),
        "study_type": design.get("studyType", ""),
        "allocation": design_info.get("allocation", ""),
        "intervention_model": design_info.get("interventionModel", ""),
        "masking": design_info.get("maskingInfo", {}).get("masking", ""),
        "enrollment": enroll.get("count", None),
        "enrollment_type": enroll.get("type", ""),
        "start_date": status.get("startDateStruct", {}).get("date", ""),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "completion_date": status.get("completionDateStruct", {}).get("date", ""),
        "has_results": study.get("hasResults", False),
    }


def extract_outcomes(study, trial_name, nct_id):
    """Extract outcome measure results."""
    rs = study.get("resultsSection", {})
    om_module = rs.get("outcomeMeasuresModule", {})
    outcome_measures = om_module.get("outcomeMeasures", [])

    rows = []
    for om in outcome_measures:
        # Build group ID -> title map
        groups = {g["id"]: g.get("title", "") for g in om.get("groups", [])}

        om_title = om.get("title", "")
        om_type = om.get("type", "")
        om_desc = om.get("description", "")
        param_type = om.get("paramType", "")
        dispersion_type = om.get("dispersionType", "")
        unit = om.get("unitOfMeasure", "")
        time_frame = om.get("timeFrame", "")

        # Extract measurements from classes
        for cls in om.get("classes", []):
            class_title = cls.get("title", "")
            for cat in cls.get("categories", []):
                for meas in cat.get("measurements", []):
                    rows.append({
                        "trial_name": trial_name,
                        "nct_id": nct_id,
                        "outcome_type": om_type,
                        "outcome_title": om_title,
                        "outcome_description": om_desc,
                        "param_type": param_type,
                        "dispersion_type": dispersion_type,
                        "unit": unit,
                        "time_frame": time_frame,
                        "class_title": class_title,
                        "arm_group_id": meas.get("groupId", ""),
                        "arm_title": groups.get(meas.get("groupId", ""), ""),
                        "value": meas.get("value", ""),
                        "spread": meas.get("spread", ""),
                        "lower_limit": meas.get("lowerLimit", ""),
                        "upper_limit": meas.get("upperLimit", ""),
                        "comment": meas.get("comment", ""),
                    })

        # Extract statistical analyses if present
        for analysis in om.get("analyses", []):
            # Attach p-values to the outcome title
            for ag in analysis.get("groupIds", []):
                for row in rows:
                    if (row["outcome_title"] == om_title and
                        row["arm_group_id"] == ag and
                        row["nct_id"] == nct_id):
                        row["p_value"] = analysis.get("pValue", "")
                        row["statistical_method"] = analysis.get("statisticalMethod", "")
                        row["ci_lower"] = analysis.get("ciLowerLimit", "")
                        row["ci_upper"] = analysis.get("ciUpperLimit", "")
                        row["estimate_value"] = analysis.get("estimateValue", "")
                        break

    return rows


def extract_adverse_events(study, trial_name, nct_id):
    """Extract adverse event data (both serious and other)."""
    rs = study.get("resultsSection", {})
    ae_module = rs.get("adverseEventsModule", {})

    # Build group ID -> title map from eventGroups
    event_groups = ae_module.get("eventGroups", [])
    groups = {}
    group_meta = {}
    for eg in event_groups:
        gid = eg.get("id", "")
        groups[gid] = eg.get("title", "")
        group_meta[gid] = {
            "serious_affected": eg.get("seriousNumAffected"),
            "serious_at_risk": eg.get("seriousNumAtRisk"),
            "other_affected": eg.get("otherNumAffected"),
            "other_at_risk": eg.get("otherNumAtRisk"),
        }

    rows = []

    # Process both serious and other events
    for event_type, events_key in [("SERIOUS", "seriousEvents"), ("OTHER", "otherEvents")]:
        for event in ae_module.get(events_key, []):
            term = event.get("term", "")
            organ_system = event.get("organSystem", "")
            for stat in event.get("stats", []):
                gid = stat.get("groupId", "")
                rows.append({
                    "trial_name": trial_name,
                    "nct_id": nct_id,
                    "event_type": event_type,
                    "ae_term": term,
                    "organ_system": organ_system,
                    "arm_group_id": gid,
                    "arm_title": groups.get(gid, ""),
                    "num_events": stat.get("numEvents"),
                    "num_affected": stat.get("numAffected"),
                    "num_at_risk": stat.get("numAtRisk"),
                })

    return rows


def extract_baselines(study, trial_name, nct_id):
    """Extract baseline characteristics data."""
    rs = study.get("resultsSection", {})
    bl_module = rs.get("baselineCharacteristicsModule", {})

    # Build group ID -> title map
    groups = {g["id"]: g.get("title", "") for g in bl_module.get("groups", [])}

    rows = []
    for measure in bl_module.get("measures", []):
        m_title = measure.get("title", "")
        param_type = measure.get("paramType", "")
        dispersion_type = measure.get("dispersionType", "")
        unit = measure.get("unitOfMeasure", "")

        for cls in measure.get("classes", []):
            class_title = cls.get("title", "")
            for cat in cls.get("categories", []):
                cat_title = cat.get("title", "")
                for meas in cat.get("measurements", []):
                    gid = meas.get("groupId", "")
                    rows.append({
                        "trial_name": trial_name,
                        "nct_id": nct_id,
                        "measure_title": m_title,
                        "param_type": param_type,
                        "dispersion_type": dispersion_type,
                        "unit": unit,
                        "class_title": class_title,
                        "category": cat_title,
                        "arm_group_id": gid,
                        "arm_title": groups.get(gid, ""),
                        "value": meas.get("value", ""),
                        "spread": meas.get("spread", ""),
                        "lower_limit": meas.get("lowerLimit", ""),
                        "upper_limit": meas.get("upperLimit", ""),
                    })

    return rows


def main():
    print("=" * 70)
    print("CLINICALTRIALS.GOV — SUSTAIN / STEP / SURMOUNT DATA ACQUISITION")
    print("=" * 70)

    all_metadata = []
    all_outcomes = []
    all_adverse = []
    all_baselines = []

    total = len(TRIALS)
    for idx, (trial_name, nct_id) in enumerate(TRIALS.items(), 1):
        print(f"\n[{idx}/{total}] Fetching {trial_name} ({nct_id})...")

        try:
            study = fetch_study(nct_id)
        except Exception as e:
            print(f"  ERROR fetching: {e}")
            continue

        has_results = study.get("hasResults", False)
        print(f"  Has results: {has_results}")

        # Always extract metadata
        meta = extract_metadata(study, trial_name, nct_id)
        all_metadata.append(meta)
        print(f"  Status: {meta['overall_status']} | Phase: {meta['phase']} | Enrolled: {meta['enrollment']}")

        # Extract results only if available
        if has_results:
            outcomes = extract_outcomes(study, trial_name, nct_id)
            all_outcomes.extend(outcomes)
            print(f"  Outcomes extracted: {len(outcomes)} measurements")

            adverse = extract_adverse_events(study, trial_name, nct_id)
            all_adverse.extend(adverse)
            print(f"  Adverse events extracted: {len(adverse)} records")

            baselines = extract_baselines(study, trial_name, nct_id)
            all_baselines.extend(baselines)
            print(f"  Baseline measures extracted: {len(baselines)} records")
        else:
            print(f"  [!] No results posted yet -- protocol-only data captured")

        time.sleep(RATE_LIMIT_SECONDS)

    # ── SAVE ALL OUTPUTS ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SAVING OUTPUT FILES")
    print("=" * 70)

    # 1. Trial Metadata
    df_meta = pd.DataFrame(all_metadata)
    meta_path = os.path.join(OUTPUT_DIR, "trial_metadata.csv")
    df_meta.to_csv(meta_path, index=False)
    print(f"\n  trial_metadata.csv         -> {len(df_meta)} trials")
    print(f"    With results: {df_meta['has_results'].sum()}")
    print(f"    Protocol only: {(~df_meta['has_results']).sum()}")

    # 2. Outcome Results
    df_outcomes = pd.DataFrame(all_outcomes)
    out_path = os.path.join(OUTPUT_DIR, "trial_outcomes.csv")
    if not df_outcomes.empty:
        df_outcomes.to_csv(out_path, index=False)
        print(f"\n  trial_outcomes.csv         -> {len(df_outcomes)} measurements")
        print(f"    Primary outcomes: {(df_outcomes['outcome_type'] == 'PRIMARY').sum()}")
        print(f"    Secondary outcomes: {(df_outcomes['outcome_type'] == 'SECONDARY').sum()}")
        # Show key primary results
        primary = df_outcomes[df_outcomes['outcome_type'] == 'PRIMARY']
        if not primary.empty:
            print("\n  Key Primary Outcomes (sample):")
            for trial in primary['trial_name'].unique()[:5]:
                trial_primary = primary[primary['trial_name'] == trial]
                title = trial_primary['outcome_title'].iloc[0][:60]
                print(f"    {trial}: {title}")
                for _, row in trial_primary.head(4).iterrows():
                    val = row.get('value', '')
                    spread = row.get('spread', '')
                    arm = row.get('arm_title', '')[:30]
                    unit = row.get('unit', '')
                    spread_str = f" ± {spread}" if spread else ""
                    print(f"      {arm}: {val}{spread_str} {unit}")
    else:
        print("\n  trial_outcomes.csv         -> 0 measurements (no results posted)")

    # 3. Adverse Events
    df_ae = pd.DataFrame(all_adverse)
    ae_path = os.path.join(OUTPUT_DIR, "trial_adverse_events.csv")
    if not df_ae.empty:
        df_ae.to_csv(ae_path, index=False)
        print(f"\n  trial_adverse_events.csv   -> {len(df_ae)} records")
        print(f"    Serious events: {(df_ae['event_type'] == 'SERIOUS').sum()}")
        print(f"    Other events: {(df_ae['event_type'] == 'OTHER').sum()}")
        print(f"    Unique AE terms: {df_ae['ae_term'].nunique()}")
    else:
        print("\n  trial_adverse_events.csv   -> 0 records")

    # 4. Baseline Characteristics
    df_bl = pd.DataFrame(all_baselines)
    bl_path = os.path.join(OUTPUT_DIR, "trial_baselines.csv")
    if not df_bl.empty:
        df_bl.to_csv(bl_path, index=False)
        print(f"\n  trial_baselines.csv        -> {len(df_bl)} records")
        print(f"    Unique measures: {df_bl['measure_title'].nunique()}")
    else:
        print("\n  trial_baselines.csv        -> 0 records")

    # ── FINAL REPORT ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CLINICALTRIALS.GOV DATA ACQUISITION COMPLETE")
    print("=" * 70)

    # Trial family summary
    for family in ["SUSTAIN", "STEP", "SURMOUNT"]:
        family_trials = df_meta[df_meta["trial_name"].str.startswith(family)]
        with_results = family_trials["has_results"].sum()
        print(f"\n  {family} trials: {len(family_trials)} fetched, {with_results} with posted results")
        for _, row in family_trials.iterrows():
            status_icon = "[Y]" if row["has_results"] else "[ ]"
            print(f"    {status_icon} {row['trial_name']:15s} | {row['overall_status']:12s} | N={row['enrollment']}")

    print(f"\nOutput files in {os.path.abspath(OUTPUT_DIR)}/:")
    print("  trial_metadata.csv         -- one row per trial (protocol info)")
    print("  trial_outcomes.csv         -- outcome measurements by arm")
    print("  trial_adverse_events.csv   -- AE counts by arm (serious + other)")
    print("  trial_baselines.csv        -- baseline demographics by arm")
    print()
    print("NEXT STEP -> Day 7: Merge all sources into unified schema")


if __name__ == "__main__":
    main()
