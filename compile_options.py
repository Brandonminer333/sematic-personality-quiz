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


# Load your reference data here
df = pd.read_csv("api/gym_leaders.csv")
vectors = df.drop(columns=['Leader', 'Type']).replace(mapping)

# Generate all possible answer combinations
all_possible_vectors = list(
    combinations_with_replacement(mapping.values(), 15))
all_possible_vectors = [np.array(vector) for vector in all_possible_vectors]

# Build the results map
results_map = {}
for vector in all_possible_vectors:
    key = ','.join(map(str, vector))
    ranking = rank_types_by_similarity(vector, vectors, df)
    results_map[key] = ranking.index[0]  # Get the top-ranked type

print(f"Generated {len(results_map)} combinations")

# Export to JSON
with open('quiz_results.json', 'w') as f:
    json.dump(results_map, f, indent=2)

print("Successfully created quiz_results.json!")
