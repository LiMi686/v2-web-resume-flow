import pandas as pd

def load_policy_sources(path="Data/policy_sources.csv"):
    df = pd.read_csv(path)
    return df


if __name__ == "__main__":
    df = load_policy_sources()
    print(df.head())