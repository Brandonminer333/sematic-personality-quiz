from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import numpy as np
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df = pd.read_csv("gym_leaders_synthetic.csv")

questions = [
    {"text": "I feel most like myself when I'm around other people."},
    {"text": "I often take the lead in group situations without being asked."},
    {"text": "After a long social event, I need time alone to feel like myself again."},
    {"text": "I would rather spend years perfecting one craft than spread my energy across many interests."},
    {"text": "I tend to prepare thoroughly before starting something new."},
    {"text": "I lose interest in a project once the hardest problem is solved."},
    {"text": "When something goes wrong, my first instinct is to do something about it rather than sit with the feeling."},
    {"text": "I find it easy to stay calm when the people around me are stressed."},
    {"text": "I tend to take criticism personally, even when I know it isn't meant that way."},
    {"text": "I find comfort in a predictable daily routine."},
    {"text": "I'm drawn to situations where the outcome isn't guaranteed."},
    {"text": "I often seek out experiences that most people in my life would consider unusual."},
    {"text": "I often think through problems by talking or writing rather than sitting in silence."},
    {"text": "I notice details in my environment that other people seem to walk past."},
    {"text": "I prefer finding a reliable method and sticking to it over experimenting with new approaches."}
]

answer_options = [
    "strongly disagree",
    "somewhat disagree",
    "neutral",
    "somewhat agree",
    "strongly agree"
]

results = {
    "Fire": {"emoji": "🔥", "type": "FIRE TYPE", "headline": "The Blazing Trailblazer", "tag": "Fire Type", "desc": "You burn bright and inspire everyone around you. Passionate, bold, and impossible to ignore — you lead with your heart and light up every room you enter. You're not afraid to take risks, and that fearless energy is contagious.", "traits": ["Bold", "Passionate", "Inspirational", "Energetic"], "famous": "Blaine — the Volcano Badge gym leader, a fiery quiz master who tests the bold.", "color": "#ff6b35"},
    "Water": {"emoji": "🌊", "type": "WATER TYPE", "headline": "The Deep-Feeling Adaptor", "tag": "Water Type", "desc": "You're fluid, intuitive, and emotionally intelligent. You flow around obstacles rather than crashing through them, and your calm surface hides extraordinary depth. People trust you completely — you always know what someone needs.", "traits": ["Empathetic", "Intuitive", "Calm", "Adaptable"], "famous": "Misty — the Cascade Badge leader, fierce and flowing, always in motion.", "color": "#38b6ff"},
    "Grass": {"emoji": "🌿", "type": "GRASS TYPE", "headline": "The Grounded Nurturer", "tag": "Grass Type", "desc": "You're rooted, reliable, and quietly powerful. You grow slowly but surely, and you bring life wherever you go. People feel safe with you — you're the kind of person who makes every space feel like home.", "traits": ["Nurturing", "Patient", "Grounded", "Resilient"], "famous": "Erika — the Rainbow Badge leader, serene and deeply connected to nature.", "color": "#5cb85c"},
    "Electric": {"emoji": "⚡", "type": "ELECTRIC TYPE", "headline": "The Electric Innovator", "tag": "Electric Type", "desc": "You're sharp, quick, and always a few steps ahead. Your energy crackles — ideas come fast, and you light up conversations. You thrive on stimulation and hate standing still. You make things happen.", "traits": ["Clever", "Quick-witted", "Energetic", "Creative"], "famous": "Lt. Surge — the Thunder Badge leader, loud, loud, and always charged up.", "color": "#f6c90e"},
    "Psychic": {"emoji": "🔮", "type": "PSYCHIC TYPE", "headline": "The Visionary Thinker", "tag": "Psychic Type", "desc": "You live in the world of ideas. Perceptive, philosophical, and quietly powerful — you see patterns others miss and feel things others barely notice. Your mind is your greatest gift.", "traits": ["Perceptive", "Intuitive", "Philosophical", "Strategic"], "famous": "Sabrina — the Marsh Badge leader, mysterious and impossibly perceptive.", "color": "#c975d4"},
    "Rock": {"emoji": "🪨", "type": "ROCK TYPE", "headline": "The Unshakeable Protector", "tag": "Rock Type", "desc": "You are steady, reliable, and unbreakable. You don't bend under pressure — you're the person everyone leans on in a crisis. Your strength isn't loud; it's the kind that makes everyone around you feel safe.", "traits": ["Dependable", "Strong", "Steady", "Protective"], "famous": "Brock — the Boulder Badge leader, steadfast, warm, and unmovable.", "color": "#b5651d"},
    "Ice": {"emoji": "❄️", "type": "ICE TYPE", "headline": "The Cool, Composed Perfectionist", "tag": "Ice Type", "desc": "You're precise, self-possessed, and quietly elegant. You don't rush — you observe, consider, and then act with cool precision. Others may call you reserved, but that's just your standards. You expect a lot, including from yourself.", "traits": ["Precise", "Reserved", "Elegant", "Discerning"], "famous": "Pryce — the Glacier Badge leader, wise from years of quiet contemplation.", "color": "#aee9f0"},
    "Ghost": {"emoji": "👻", "type": "GHOST TYPE", "headline": "The Mysterious Creative", "tag": "Ghost Type", "desc": "You're an enigma — layered, artistic, and endlessly surprising. You see beauty in the strange and meaning in the in-between. People are drawn to your depth even if they can't quite figure you out. That's exactly how you like it.", "traits": ["Creative", "Mysterious", "Perceptive", "Independent"], "famous": "Morty — the Fog Badge leader, serene and hauntingly insightful.", "color": "#9b72cf"},
    "Dragon": {"emoji": "🐉", "type": "DRAGON TYPE", "headline": "The Rare, Ambitious Leader", "tag": "Dragon Type", "desc": "You are extraordinary — and you know it. Ambitious, magnetic, and bigger than life, you set goals others wouldn't dare to dream and then achieve them. Rare to encounter, impossible to forget.", "traits": ["Ambitious", "Magnetic", "Confident", "Visionary"], "famous": "Lance — the Dragon Badge champion, commanding and legendary.", "color": "#7038f8"},
    "Dark": {"emoji": "🌑", "type": "DARK TYPE", "headline": "The Cunning Strategist", "tag": "Dark Type", "desc": "You play the long game. Perceptive, self-reliant, and deeply independent — you trust your own judgment above all else. You're not cynical, just realistic. And when you commit to something, nothing stops you.", "traits": ["Strategic", "Independent", "Perceptive", "Resilient"], "famous": "Karen — Elite Four dark-type master, who plays by her own rules.", "color": "#4a4a6a"},
    "Fighting": {"emoji": "🥊", "type": "FIGHTING TYPE", "headline": "The Fierce Champion", "tag": "Fighting Type", "desc": "You're driven by a burning desire to improve and prove yourself. Discipline, grit, and raw determination are your currency. You push through when everyone else stops, and your passion for growth is truly unstoppable.", "traits": ["Disciplined", "Driven", "Brave", "Tenacious"], "famous": "Chuck — the Storm Badge leader, relentless in his pursuit of strength.", "color": "#c03028"},
    "Steel": {"emoji": "⚙️", "type": "STEEL TYPE", "headline": "The Brilliant Architect", "tag": "Steel Type", "desc": "You build things that last. Meticulous, sharp-minded, and quietly confident — you excel at systems, structure, and making things work perfectly. You're the one everyone turns to when things need to actually get done.", "traits": ["Precise", "Logical", "Reliable", "Sharp"], "famous": "Jasmine — the Mineral Badge leader, methodical and quietly formidable.", "color": "#b8b8d0"},
    "Normal": {"emoji": "⭐", "type": "NORMAL TYPE", "headline": "The Genuine, Versatile Soul", "tag": "Normal Type", "desc": "There's nothing ordinary about being extraordinary at everything. You're adaptable, genuine, and unexpectedly powerful. You don't need a gimmick — you're just authentically, brilliantly yourself, and that's more than enough.", "traits": ["Genuine", "Adaptable", "Warm", "Versatile"], "famous": "Whitney — the Plain Badge leader, sweet on the surface, devastatingly capable underneath.", "color": "#a8a878"},
    "Fairy": {"emoji": "✨", "type": "FAIRY TYPE", "headline": "The Enchanting Heart", "tag": "Fairy Type", "desc": "You lead with love — and don't underestimate how powerful that is. Warm, creative, and quietly fierce, you disarm people with your sweetness and then astonish them with your strength. You make the world more beautiful just by being in it.", "traits": ["Warm", "Empathetic", "Creative", "Fierce"], "famous": "Valerie — the Fairy Badge leader, dreamy, whimsical, and deeply powerful.", "color": "#ee99ac"},
    "Bug": {"emoji": "🦋", "type": "BUG TYPE", "headline": "The Underestimated Overcomer", "tag": "Bug Type", "desc": "People overlook you — at first. Then you quietly outwork everyone in the room. You believe in growth, transformation, and finding the extraordinary in the small and unnoticed. Your journey from underdog to champion is what legends are made of.", "traits": ["Tenacious", "Observant", "Growth-oriented", "Resourceful"], "famous": "Bugsy — the Hive Badge leader, studying endlessly and thriving from it.", "color": "#a8b820"},
    "Ground": {"emoji": "🏜️", "type": "GROUND TYPE", "headline": "The Earthy, Steady Force", "tag": "Ground Type", "desc": "You are immovable when it counts. Practical, warm, and completely trustworthy — you don't make promises you can't keep. You're the foundation that holds everything together, and your quiet strength speaks louder than anyone's noise.", "traits": ["Practical", "Loyal", "Steady", "Dependable"], "famous": "Giovanni — the Earth Badge leader, grounded and ruthlessly effective (in his own way).", "color": "#e0c068"},
}

last_result = None


def cosine_similarity(vector, vectors):
    dot_products = vectors @ vector
    norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(vector)
    return dot_products / norms


def rank_types_by_similarity(new_vector, df):
    vectors = df[[f"Q{i+1}" for i in range(15)]].values
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


@app.post("/submit_answers")
async def submit_answers(answers: List[str]):
    global last_result
    mapping = {
        "strongly disagree": -1.0,
        "somewhat disagree": -0.5,
        "neutral": 0.0,
        "somewhat agree": 0.5,
        "strongly agree": 1.0,
        "0": -1.0,
        "1": -0.5,
        "2": 0.0,
        "3": 0.5,
        "4": 1.0
    }
    new_vector = np.array([
        mapping.get(str(ans).strip().lower(), 0.0)
        for ans in answers
    ])
    ranking = rank_types_by_similarity(new_vector, df)
    top_type = ranking.index[0]
    last_result = results.get(top_type, results['Normal'])
    return {"message": "Answers submitted"}


@app.get("/result")
async def get_result():
    if last_result is None:
        return {"error": "No result available"}
    return last_result
