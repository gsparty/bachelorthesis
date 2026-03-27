"""
Audit prompt lengths (UTF-8 characters) for transparency / covariate analysis.

Run from repo root or src:
    python prompt_audit.py

Flags stressor user prompts that differ strongly in length from neutral within the same scenario.
"""

from __future__ import annotations

from prompts_config import ALL_SCENARIOS


def main() -> None:
    print("scenario\tvariant_id\tvariant_type\tuser_chars\tsystem_chars\tvs_neutral_user")
    for sid in sorted(ALL_SCENARIOS.keys()):
        scen = ALL_SCENARIOS[sid]
        neutral_len = None
        for v in scen.variants:
            if v.variant_type == "neutral":
                neutral_len = len(v.user_prompt)
                break
        for v in scen.variants:
            ul = len(v.user_prompt)
            sl = len(v.system_prompt)
            ratio = (ul / neutral_len) if neutral_len else float("nan")
            flag = ""
            if neutral_len and v.variant_type != "neutral" and (
                ratio < 0.85 or ratio > 1.25
            ):
                flag = "\t** length differs >15% from neutral **"
            print(f"{sid}\t{v.variant_id}\t{v.variant_type}\t{ul}\t{sl}\t{ratio:.3f}{flag}")


if __name__ == "__main__":
    main()
