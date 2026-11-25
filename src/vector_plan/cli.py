"""CLI entrypoint for vector-plan."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .planner import plan_irs_campaign, plan_itn_campaign, plan_smc_campaign


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vector-plan",
        description="WHO malaria vector-control microplanner (ITN/LLIN, IRS resistance rotation, and SMC SPAQ).",
    )
    parser.add_argument("--population", type=int, default=180000, help="District target population.")
    parser.add_argument("--structures", type=int, default=38000, help="IRS target residential structures.")
    parser.add_argument("--insecticide", default="actellic_300cs", help="IRS insecticide key.")
    parser.add_argument("--prior-moa", nargs="*", default=[], help="Prior years IRAC MoA groups (e.g. 1B 1B).")
    parser.add_argument("--smc-cycles", type=int, default=4, help="Seasonal malaria chemoprevention monthly cycles.")
    args = parser.parse_args(argv)

    itn = plan_itn_campaign(population=args.population)
    irs = plan_irs_campaign(
        target_structures=args.structures,
        insecticide_key=args.insecticide,
        prior_years_moa_history=args.prior_moa,
    )
    smc = plan_smc_campaign(total_population=args.population, monthly_cycles=args.smc_cycles)
    print(json.dumps({"itn_plan": asdict(itn), "irs_plan": asdict(irs), "smc_plan": asdict(smc)}, indent=2))
    return 0 if not irs.resistance_rotation_warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
