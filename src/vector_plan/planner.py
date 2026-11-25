"""WHO Global Malaria Programme ITN/LLIN, IRS resistance-rotation, and SMC SPAQ microplanning."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ItnCampaignPlan:
    """WHO ITN/LLIN universal coverage campaign + 3-year attrition & continuous top-up plan."""

    population: int
    mass_campaign_nets_required: int
    bales_of_50_nets: int
    annual_anc_epi_topup_nets: int
    surviving_nets_year1: int
    surviving_nets_year2: int
    surviving_nets_year3: int
    population_access_pct_year2: float
    months_until_access_below_80pct: int
    recommended_net_type: str


def _netcalc_survival(years: float, median_life_years: float) -> float:
    """WHO NetCALC S-shaped Weibull net-survival fraction at age `years`."""
    # Shape parameter k=2.5 matches published NetCALC field durability curves across Sub-Saharan Africa
    k = 2.5
    lam = median_life_years / float(math.log(2.0) ** (1.0 / k))
    return math.exp(-float((years / lam) ** k))


def plan_itn_campaign(
    *,
    population: int,
    buffer_pct: float = 10.0,
    median_net_life_years: float = 2.2,
    anc_pregnant_pct: float = 4.5,
    epi_infant_pct: float = 3.8,
    pyrethroid_resistance_confirmed: bool = True,
) -> ItnCampaignPlan:
    """Quantify WHO ITN mass campaign (pop / 1.8) + 3-year NetCALC attrition & ANC/EPI top-ups."""
    if population <= 0:
        raise ValueError("population must be strictly positive")
    if not (0.5 <= median_net_life_years <= 5.0):
        raise ValueError("median_net_life_years must be in [0.5, 5.0]")

    base_nets = population / 1.8
    mass_nets = math.ceil(round(base_nets * (1.0 + buffer_pct / 100.0), 6))
    bales = math.ceil(mass_nets / 50.0)
    anc_epi_annual = math.ceil(population * ((anc_pregnant_pct + epi_infant_pct) / 100.0) * 1.05)

    # Track surviving mass-campaign nets at years 1, 2, 3 (each net protects up to 1.8 people)
    y1 = round(base_nets * _netcalc_survival(1.0, median_net_life_years))
    y2 = round(base_nets * _netcalc_survival(2.0, median_net_life_years))
    y3 = round(base_nets * _netcalc_survival(3.0, median_net_life_years))
    access_y2 = min(100.0, (y2 * 1.8 / population) * 100.0)

    # First month where mass-campaign coverage drops below WHO 80% universal access floor
    months_80 = 36
    for m in range(1, 37):
        surv = _netcalc_survival(m / 12.0, median_net_life_years)
        if surv * 100.0 < 80.0:
            months_80 = m
            break

    net_type = (
        "Dual-AI (Chlorfenapyr/Pyrethroid or PBO-Pyrethroid LLIN)"
        if pyrethroid_resistance_confirmed
        else "Standard Pyrethroid LLIN"
    )

    return ItnCampaignPlan(
        population=population,
        mass_campaign_nets_required=mass_nets,
        bales_of_50_nets=bales,
        annual_anc_epi_topup_nets=anc_epi_annual,
        surviving_nets_year1=y1,
        surviving_nets_year2=y2,
        surviving_nets_year3=y3,
        population_access_pct_year2=round(access_y2, 1),
        months_until_access_below_80pct=months_80,
        recommended_net_type=net_type,
    )


@dataclass(frozen=True)
class IrsInsecticide:
    """WHO PQT-VC prequalified IRS insecticide formulation & IRAC resistance group."""

    key: str
    display_name: str
    irac_moa_group: str
    pyrethroid_based: bool
    m2_per_unit: float  # One bottle/sachet covers 1 Hudson 10L pump charge (250 m2)
    unit_label: str
    residual_months: int


IRS_INSECTICIDES: dict[str, IrsInsecticide] = {
    "actellic_300cs": IrsInsecticide(
        "actellic_300cs", "Actellic 300CS (Pirimiphos-methyl)", "1B", False, 250.0, "833mL bottle", 8
    ),
    "sumishield_50wg": IrsInsecticide(
        "sumishield_50wg", "SumiShield 50WG (Clothianidin)", "4A", False, 250.0, "150g sachet", 8
    ),
    "fludora_fusion": IrsInsecticide(
        "fludora_fusion", "Fludora Fusion (Clothianidin+Deltamethrin)", "4A+3A", True, 250.0, "100g sachet", 8
    ),
    "k_othrine_polyzone": IrsInsecticide(
        "k_othrine_polyzone", "K-Othrine PolyZone (Deltamethrin)", "3A", True, 250.0, "sachet", 6
    ),
}


@dataclass(frozen=True)
class IrsCampaignPlan:
    """WHO Indoor Residual Spraying (IRS) operational quantification & resistance audit."""

    target_structures: int
    insecticide: str
    irac_moa_group: str
    total_sprayable_area_m2: float
    pump_charges_10l_required: int
    insecticide_units_with_buffer: int
    unit_label: str
    spray_operator_days_required: int
    spray_operators_for_campaign: int
    resistance_rotation_warnings: tuple[str, ...]


def plan_irs_campaign(
    *,
    target_structures: int,
    insecticide_key: str,
    avg_sprayable_m2_per_structure: float = 110.0,
    porous_mud_wall_fraction: float = 0.50,
    campaign_days: int = 24,
    structures_per_operator_day: float = 10.0,
    buffer_pct: float = 10.0,
    prior_years_moa_history: Sequence[str] = (),
    pyrethroid_resistance_confirmed: bool = True,
) -> IrsCampaignPlan:
    """Quantify IRS sachets/bottles, 10L pump charges, spray teams, and enforce IRAC MoA rotation."""
    if target_structures <= 0 or avg_sprayable_m2_per_structure <= 0 or campaign_days <= 0:
        raise ValueError("target_structures, avg_sprayable_m2_per_structure, and campaign_days must be positive")
    key = insecticide_key.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in IRS_INSECTICIDES:
        raise KeyError(f"Unknown IRS insecticide '{insecticide_key}'. Options: {sorted(IRS_INSECTICIDES)}")

    ins = IRS_INSECTICIDES[key]
    # Porous unplastered mud walls absorb ~12% extra spray volume compared to smooth plaster
    porosity_mult = 1.0 + 0.12 * max(0.0, min(1.0, porous_mud_wall_fraction))
    eff_area = target_structures * avg_sprayable_m2_per_structure * porosity_mult
    pump_charges = math.ceil(eff_area / ins.m2_per_unit)
    units_total = math.ceil(pump_charges * (1.0 + buffer_pct / 100.0))

    op_days = math.ceil(target_structures / structures_per_operator_day)
    operators = math.ceil(op_days / campaign_days)

    warnings: list[str] = []
    if pyrethroid_resistance_confirmed and ins.irac_moa_group == "3A":
        warnings.append(
            f"PYRETHROID RESISTANCE BLOCK: {ins.display_name} (MoA 3A) is ineffective where pyrethroid "
            "resistance is confirmed; switch to Actellic 300CS (1B) or SumiShield 50WG (4A)."
        )
    if len(prior_years_moa_history) >= 2 and all(m == ins.irac_moa_group for m in prior_years_moa_history[-2:]):
        warnings.append(
            f"IRAC ROTATION VIOLATION: MoA {ins.irac_moa_group} was already sprayed 2+ consecutive years; "
            "rotate to a distinct IRAC mode of action to prevent vector resistance."
        )

    return IrsCampaignPlan(
        target_structures=target_structures,
        insecticide=ins.key,
        irac_moa_group=ins.irac_moa_group,
        total_sprayable_area_m2=round(eff_area, 1),
        pump_charges_10l_required=pump_charges,
        insecticide_units_with_buffer=units_total,
        unit_label=ins.unit_label,
        spray_operator_days_required=op_days,
        spray_operators_for_campaign=operators,
        resistance_rotation_warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class SmcCampaignPlan:
    """WHO Seasonal Malaria Chemoprevention (SMC) SPAQ blister-pack quantification."""

    children_3_to_11m: int
    children_12_to_59m: int
    monthly_cycles: int
    spaq_infant_blisters_required: int
    spaq_child_blisters_required: int
    total_spaq_blisters_required: int


def plan_smc_campaign(
    *,
    total_population: int,
    monthly_cycles: int = 4,
    buffer_pct: float = 10.0,
) -> SmcCampaignPlan:
    """Quantify WHO SMC SPAQ blister packs for children 3-11m (~3.2% pop) & 12-59m (~14.8% pop)."""
    if total_population <= 0 or not (1 <= monthly_cycles <= 6):
        raise ValueError("total_population must be positive and monthly_cycles in [1, 6]")
    c_inf = round(total_population * 0.032)
    c_chd = round(total_population * 0.148)
    mult = 1.0 + (buffer_pct / 100.0)
    inf_blisters = math.ceil(c_inf * monthly_cycles * mult)
    chd_blisters = math.ceil(c_chd * monthly_cycles * mult)
    return SmcCampaignPlan(
        children_3_to_11m=c_inf,
        children_12_to_59m=c_chd,
        monthly_cycles=monthly_cycles,
        spaq_infant_blisters_required=inf_blisters,
        spaq_child_blisters_required=chd_blisters,
        total_spaq_blisters_required=inf_blisters + chd_blisters,
    )
