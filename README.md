# Agentic Personality Quiz Builder

## Overview

A personality quiz engine that uses vector geometry and LLM-generated synthetic data to match users to a character archetype from any fictional universe. Rather than assigning arbitrary point values like traditional quizzes, each answer contributes a weighted vector toward one or more archetypes. The quiz result is the argmax cosine similarity between the user's aggregated answer vector and a set of normalized reference vectors — one per archetype.

The system is built around an **agent** that receives a quiz topic, determines what to scrape, generates synthetic personality data by prompting an LLM to roleplay as each archetype, and selects the most discriminating questions for that character space. This makes the quiz engine character-set agnostic: swapping "Pokemon types" for "Hogwarts houses" or "Greek gods" is a matter of re-running the agent with a new prompt.

Questions are lifestyle-based and non-leading, which means they can be reused and shuffled across character sets — and across quiz attempts, allowing users to verify their results without gaming the quiz on a second pass.

---

## MVP — Which Pokémon Type Are You?

The MVP targets **Pokémon gym leader types** (Fire, Water, Grass, etc.) as archetypes. Gym leaders are used as a proxy: each leader canonically represents one type, and the LLM is prompted to embody that type's general personality rather than the specific character.

### Agent Tools

| Tool | Purpose |
|---|---|
| `scrape_archetype_data(topic)` | Determines the best source to scrape and extracts relevant archetype info (e.g. Bulbapedia for Pokémon types) |
| `generate_synthetic_data(archetypes, questions)` | Prompts the LLM to answer each question as each archetype; runs multiple times per archetype and averages for stable reference vectors |
| `check_db_for_similar_quiz(topic)` | Checks whether a matching or overlapping quiz already exists in the database to avoid redundant generation |
| `question_selector(reference_vectors)` | Selects questions that maximize separation between reference vectors; flags and handles near-collinear archetypes |
| `validate_reference_vectors(vectors)` | Checks that all archetypes have meaningful separation; surfaces pairs that are too similar to discriminate |

### Classification

- Each answer maps to a weight vector over all archetypes
- User answers are summed and normalized to a unit vector
- Result is the archetype with the highest cosine similarity to the user's unit vector
- A decision tree trained on per-question answer sequences serves as a secondary validator during development; disagreement between the two flags miscalibrated questions or reference vectors

### Tech Stack

- Python
- BeautifulSoup4 for scraping
- Anthropic API for synthetic data generation and agent reasoning
- (TBD) vector store for reference vectors and quiz cache

---

## Future Updates

- **Character-set agnostic pipeline** — rerun the agent on any topic (Hogwarts houses, Myers-Briggs archetypes, office roles, etc.) with no changes to the quiz engine
- **Question shuffling** — randomize question and answer order between attempts so users can double-check results without reverse-engineering the quiz
- **Soft results** — optionally surface the top 2–3 archetypes with cosine scores rather than a hard single answer, for users who want nuance
- **Web UI** — a clean frontend for taking and sharing quizzes
- **Quiz database** — store generated quizzes so the agent can reuse or extend existing character sets rather than regenerating from scratch
