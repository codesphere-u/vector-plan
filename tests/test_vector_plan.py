"""Tests for vector-plan."""

from __future__ import annotations

import json

import pytest

from vector_plan import plan_irs_campaign, plan_itn_campaign, plan_smc_campaign
from vector_plan.cli import main as cli_main


def test_itn_pop_over_1_8_and_netcalc_attrition() -> None:
    plan = plan_itn_campaign(population=180000, buffer_pct=10.0, median_net_life_years=2.2)
    # 180,000 / 1.8 * 1.10 = 110,000 nets
    assert plan.mass_campaign_nets_required == 110000
    assert plan.bales_of_50_nets == 2200
    assert plan.surviving_nets_year1 > plan.surviving_nets_year2 > plan.surviving_nets_year3
    assert 12 <= plan.months_until_access_below_80pct <= 24
    assert "Dual-AI" in plan.recommended_net_type


def test_irs_resistance_rotation_and_pyrethroid_block() -> None:
    blocked = plan_irs_campaign(
        target_structures=20000,
        insecticide_key="k_othrine_polyzone",
        pyrethroid_resistance_confirmed=True,
    )
    assert any("PYRETHROID RESISTANCE BLOCK" in w for w in blocked.resistance_rotation_warnings)

    repeat_moa = plan_irs_campaign(
        target_structures=20000,
        insecticide_key="actellic_300cs",
        prior_years_moa_history=["1B", "1B"],
    )
    assert any("IRAC ROTATION VIOLATION" in w for w in repeat_moa.resistance_rotation_warnings)

    rotated = plan_irs_campaign(
        target_structures=20000,
        insecticide_key="sumishield_50wg",
        prior_years_moa_history=["1B", "1B"],
    )
    assert rotated.resistance_rotation_warnings == ()
    assert rotated.insecticide_units_with_buffer > 9000


def test_smc_spaq_quantification_and_cli(capsys: pytest.CaptureFixture[str]) -> None:
    smc = plan_smc_campaign(total_population=100000, monthly_cycles=4, buffer_pct=10.0)
    assert smc.children_3_to_11m == 3200
    assert smc.children_12_to_59m == 14800
    assert smc.total_spaq_blisters_required == smc.spaq_infant_blisters_required + smc.spaq_child_blisters_required

    assert cli_main(["--population", "100000", "--structures", "20000", "--insecticide", "sumishield_50wg"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["itn_plan"]["mass_campaign_nets_required"] > 60000
