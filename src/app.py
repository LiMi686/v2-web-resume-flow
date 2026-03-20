from src.load_data import load_policy_sources
from src.policy_analyzer import analyze_policy_sources

def main():
    df = load_policy_sources()
    policy_text = df.to_string(index=False)

    target_role = input("Data Analyst, Data Scientist, or AI Engineer? Enter your target role: ").strip()

    result = analyze_policy_sources(policy_text, target_role)

    print("\n===== ANALYSIS RESULT =====\n")
    print(result)

    with open("outputs/policy_analysis.txt", "w", encoding="utf-8") as f:
        f.write(result)

    print("\nSaved to outputs/policy_analysis.txt")


if __name__ == "__main__":
    main()