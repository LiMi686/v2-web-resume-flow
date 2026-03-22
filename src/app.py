"""Interactive app for policy-source analysis."""

from __future__ import annotations

from pathlib import Path

try:
    from .load_data import load_policy_sources
    from .policy_analyzer import analyze_policy_sources
except ImportError:
    from load_data import load_policy_sources
    from policy_analyzer import analyze_policy_sources


def main() -> None:
    df = load_policy_sources()
    policy_text = df.to_string(index=False)

    target_role = input(
        "Data Analyst, Data Scientist, or AI Engineer? Enter your target role: "
    ).strip()

    result = analyze_policy_sources(policy_text, target_role)

    print("\n===== ANALYSIS RESULT =====\n")
    print(result)

    output_path = Path("outputs/policy_analysis.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")

    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
