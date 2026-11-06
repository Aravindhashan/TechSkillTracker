import pandas as pd

from modules import demand_fairness as fair


def _row(job_id, skill, location, company, month, remote=False, experience=3.0):
    return {
        "Job ID": job_id,
        "Job Title": f"{skill} Engineer",
        "Tech Skill": skill,
        "Company": company,
        "Location": location,
        "Is Remote": remote,
        "Experience Required (in years)": experience,
        "Date Posted": f"2024-{month:02d}-15",
    }


def _frame():
    rows = []
    for month in range(1, 9):
        # Bengaluru / remote / enterprise: Python demand grows.
        for index in range(3 + month):
            rows.append(
                _row(f"bl-{month}-{index}", "Python", "Bengaluru", "JPMorganChase",
                     month, remote=True, experience=2.0)
            )
        # Mumbai / on-site / staffing: flat React demand, senior postings.
        for index in range(3):
            rows.append(
                _row(f"mu-{month}-{index}", "React", "Mumbai", "Source-Right Staffing",
                     month, remote=False, experience=5.0)
            )
        # Cross-over postings so skill and location effects are separable.
        rows.append(
            _row(f"bl-{month}-x", "React", "Bengaluru", "JPMorganChase",
                 month, remote=True, experience=2.0)
        )
        rows.append(
            _row(f"mu-{month}-x", "Python", "Mumbai", "Source-Right Staffing",
                 month, remote=False, experience=5.0)
        )
        # A small "other" company so the third group is non-empty.
        rows.append(
            _row(f"ot-{month}-1", "Python", "Pune", "Acme", month, remote=False, experience=3.5)
        )
    return pd.DataFrame(rows)


# -- company type classifier -------------------------------------------------


def test_classify_enterprise_company():
    assert fair.classify_company_type("JPMorganChase") == "Enterprise"


def test_classify_staffing_company():
    assert fair.classify_company_type("Source-Right Staffing") == "Staffing"


def test_classify_unknown_company_is_other():
    assert fair.classify_company_type("Acme") == "Other"
    assert fair.classify_company_type("Unknown") == "Other"
    assert fair.classify_company_type(None) == "Other"


def test_classify_known_consultancy_is_enterprise_not_staffing():
    assert fair.classify_company_type("Tata Consultancy Services") == "Enterprise"


def test_remote_location_wins_over_false_flag():
    baseline = fair.audit_demand_fairness(_frame())
    baseline_remote = {row["group"]: row for row in baseline["by_remote"]}["Remote"]["postings"]

    frame = _frame()
    on_site_index = frame[frame["Location"] == "Mumbai"].index[0]
    frame.loc[on_site_index, "Location"] = "Remote India"
    assert bool(frame.loc[on_site_index, "Is Remote"]) is False

    result = fair.audit_demand_fairness(frame)
    remote = {row["group"]: row for row in result["by_remote"]}

    assert remote["Remote"]["postings"] == baseline_remote + 1


# -- grouping -----------------------------------------------------------------


def test_audit_groups_by_location_with_shares():
    result = fair.audit_demand_fairness(_frame())

    locations = {row["group"]: row for row in result["by_location"]}
    assert set(locations) == {"Bengaluru", "Mumbai", "Pune"}
    assert locations["Bengaluru"]["postings"] > locations["Mumbai"]["postings"]
    total_share = sum(row["share_pct"] for row in result["by_location"])
    assert abs(total_share - 100.0) < 1.5


def test_audit_by_remote_splits_remote_and_onsite():
    result = fair.audit_demand_fairness(_frame())

    remote = {row["group"]: row for row in result["by_remote"]}
    assert set(remote) == {"Remote", "On-site"}
    assert remote["Remote"]["postings"] > remote["On-site"]["postings"]


def test_audit_by_company_type_groups_staffing():
    result = fair.audit_demand_fairness(_frame())

    types = {row["group"]: row for row in result["by_company_type"]}
    assert set(types) == {"Enterprise", "Staffing", "Other"}
    assert types["Enterprise"]["postings"] > types["Staffing"]["postings"]


def test_is_remote_infers_from_location_when_flag_missing():
    frame = _frame().drop(columns=["Is Remote"])
    frame.loc[0, "Location"] = "Remote India"

    result = fair.audit_demand_fairness(frame)

    assert {row["group"] for row in result["by_remote"]} == {"Remote", "On-site"}


# -- momentum + adjusted gaps --------------------------------------------------


def test_audit_reports_median_momentum_per_group():
    result = fair.audit_demand_fairness(_frame())

    locations = {row["group"]: row for row in result["by_location"]}
    # Bengaluru Python demand grows across 8 months; Mumbai React is flat.
    assert locations["Bengaluru"]["median_momentum"] is not None
    assert locations["Bengaluru"]["median_momentum"] > locations["Mumbai"]["median_momentum"]
    assert locations["Bengaluru"]["median_roi_score"] is not None


def test_adjusted_gap_needs_three_months_of_history():
    thin = _frame()
    thin = thin[thin["Date Posted"] < "2024-02-01"]

    result = fair.audit_demand_fairness(thin)

    assert result["gaps"]["adjusted_by_location"] == {}
    assert result["confidence"] == "low"


def test_adjusted_gap_present_with_enough_history():
    result = fair.audit_demand_fairness(_frame())

    adjusted = result["gaps"]["adjusted_by_location"]
    assert "Bengaluru" in adjusted
    assert adjusted["Bengaluru"] is None  # baseline group
    assert adjusted["Mumbai"] is not None


def test_audit_top_skill_per_group():
    result = fair.audit_demand_fairness(_frame())

    locations = {row["group"]: row for row in result["by_location"]}
    assert locations["Bengaluru"]["top_skill"] == "Python"
    assert locations["Mumbai"]["top_skill"] == "React"


def test_audit_gap_summary_reports_share_range():
    result = fair.audit_demand_fairness(_frame())

    assert result["gaps"]["location_share_range_pp"] > 0
    assert result["overall"]["postings"] > 0


# -- edge cases ----------------------------------------------------------------


def test_audit_empty_frame_returns_empty_groups():
    result = fair.audit_demand_fairness(pd.DataFrame())

    assert result["by_location"] == []
    assert result["by_remote"] == []
    assert result["overall"]["postings"] == 0


def test_audit_output_contains_no_salary_terms():
    result = fair.audit_demand_fairness(_frame())

    def _check(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert "salary" not in str(key).lower()
                _check(value)
        elif isinstance(obj, list):
            for item in obj:
                _check(item)

    _check(result)


def test_audit_is_openly_descriptive_not_causal():
    result = fair.audit_demand_fairness(_frame())

    notes = " ".join(result["notes"]).lower()
    assert "association" in notes
