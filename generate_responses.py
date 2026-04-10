import os
import csv
import time

import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")


def get_retry_delay(e) -> float | None:
    try:
        for detail in e.details:  # e.details is already the list
            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                delay_str = detail.get("retryDelay", "0s")
                return float(delay_str.rstrip("s"))
    except Exception:
        pass
    return None


def generate_responses(client, model, prompt, _attempts=0, max_attempts=3):
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=500,
                temperature=0.7,
            )
        )
    except Exception as e:
        if get_retry_delay(e) is not None and _attempts < max_attempts:
            delay = get_retry_delay(e)
            print(f"Rate limit exceeded. Retrying in {delay} seconds...")
            time.sleep(delay)
            return generate_responses(client, model, prompt, _attempts + 1, max_attempts)
        else:
            print(f"An error occurred: {e}")
            return None
    return response.text


def roleplay_responses(character, retries=0):
    client = genai.Client(api_key=api_key)
    model = "models/gemini-2.5-pro"

    with open("roleplay_quiz_prompt.md", "r") as f:
        prompt = f.read()
    prompt = prompt.replace("[INSERT_CHARACTER]", character+" from Pokemon")

    if retries < 0:
        print("Retries cannot be negative. Setting retries to 0.")
        retries = 0

    if retries == 0:
        responses = [generate_responses(client, model, prompt)]

    else:
        responses = []
        for _ in range(retries+1):
            responses.append(generate_responses(client, model, prompt))

    return responses


if __name__ == "__main__":
    df = pd.read_csv("gym_leaders.csv")
    characters = df["Leader"].tolist()

    with open("responses.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for character in characters:
            print(f"Generating response for {character}...")
            response = roleplay_responses(character, retries=1)
            writer.writerow([character, response])
            f.flush()  # ensure it's written to disk immediately
