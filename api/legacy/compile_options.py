import json
from itertools import combinations_with_replacement
import numpy as np
import pandas as pd

mapping = {
    "strongly disagree": -1,
    "somewhat disagree": -0.5,
    "neutral": 0,
    "somewhat agree": 0.5,
    "strongly agree": 1
}


def cosine_similarity(vector, vectors):
    dot_products = vectors @ vector
    norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(vector)
    return dot_products / norms


def rank_types_by_mean_similarity(new_vector, vectors, df):
    cosine_similarities = cosine_similarity(new_vector, vectors)

    scores = {}
    for pokemon_type in df["Type"].unique():
        mask = df["Type"] == pokemon_type
        scores[pokemon_type] = float(np.mean(cosine_similarities[mask]))

    ranking = pd.Series(scores).sort_values(ascending=False)
    return ranking


def rank_types_by_weighted_similarity(new_vector, vectors, df):
    """Deprecated alias — kept for notebook parity; use mean similarity scoring."""
    return rank_types_by_mean_similarity(new_vector, vectors, df)


def rank_types_by_closest_similarity(new_vector, vectors, df):
    cosine_similarities = cosine_similarity(new_vector, vectors)
    closest_leader = [
        vector for vector in cosine_similarities if vector == max(cosine_similarities)]
    closest_leader.replace({
        -1: "Strongly Disagree",
        -0.5: "Somewhat Disagree",
        0: "Neutral",
        0.5: "Somewhat Agree",
        1: "Strongly Agree"
    })
    closest_leader = df[df.drop("Leader", "Type") == closest_leader]
    return closest_leader[['Leader', 'Type']]


def rank_types(new_vector, vectors, df, method="weighted"):
    match method:
        case "weighted":
            return rank_types_by_weighted_similarity(new_vector, vectors, df)
        case "closest":
            return rank_types_by_closest_similarity(new_vector, vectors, df)
        case _:
            raise Exception("Invalid method")


def build_results_map(*, df: pd.DataFrame, vectors: np.ndarray) -> dict[str, str]:
    """Build a mapping from answer-vectors -> top-ranked type.

    Kept as a function so importing this module doesn't trigger expensive work.
    """
    all_possible_vectors = list(
        combinations_with_replacement(mapping.values(), 15))
    all_possible_vectors = [np.array(vector)
                            for vector in all_possible_vectors]

    results_map: dict[str, str] = {}
    for vector in all_possible_vectors:
        key = ",".join(map(str, vector))
        ranking = rank_types_by_weighted_similarity(vector, vectors, df)
        results_map[key] = str(ranking.index[0])

    return results_map


if __name__ == "__main__":
    # Load your reference data here
    df = pd.read_csv("api/gym_leaders.csv")
    vectors = df.drop(columns=["Leader", "Type"]).replace(mapping).to_numpy()

    results_map = build_results_map(df=df, vectors=vectors)
    print(f"Generated {len(results_map)} combinations")

    # Export to JSON
    with open("quiz_results.json", "w") as f:
        json.dump(results_map, f, indent=2)

    print("Successfully created quiz_results.json!")
