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


def rank_types_by_similarity(new_vector, vectors, df):
    cosine_similarities = cosine_similarity(new_vector, vectors)

    type_vectors = {}
    for pokemon_type in df["Type"].unique():
        mask = df["Type"] == pokemon_type
        weights = cosine_similarities[mask]

        if np.sum(weights) == 0:
            type_vectors[pokemon_type] = np.mean(vectors[mask], axis=0)
        else:
            type_vectors[pokemon_type] = np.average(
                vectors[mask], axis=0, weights=weights)

    scores = {pokemon_type: vec.mean()
              for pokemon_type, vec in type_vectors.items()}
    ranking = pd.Series(scores).sort_values(ascending=False)
    return ranking


def build_results_map(*, df: pd.DataFrame, vectors: np.ndarray) -> dict[str, str]:
    """Build a mapping from answer-vectors -> top-ranked type.

    Kept as a function so importing this module doesn't trigger expensive work.
    """
    all_possible_vectors = list(combinations_with_replacement(mapping.values(), 15))
    all_possible_vectors = [np.array(vector) for vector in all_possible_vectors]

    results_map: dict[str, str] = {}
    for vector in all_possible_vectors:
        key = ",".join(map(str, vector))
        ranking = rank_types_by_similarity(vector, vectors, df)
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
