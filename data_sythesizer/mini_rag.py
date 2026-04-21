import requests
from bs4 import BeautifulSoup
import re


def _clean_text(text: str) -> str:
    """Removes wiki citations and strips whitespace."""
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()


def _get_all_section_contents(soup: BeautifulSoup, section_name: str, max_paragraphs: int = 2) -> list[str]:
    """
    Finds all sections matching the header name, returning a list of strings.
    Limits the number of paragraphs per section to avoid episodic plot bloat.
    """
    # Find all *header tags* whose text contains the section name.
    # Note: do not match nested <span> elements inside headers, otherwise we'll
    # double-count the same section (e.g. both the <h2> and its child <span>).
    headlines = [
        h
        for h in soup.find_all(["h2", "h3", "h4"])
        if section_name.lower() in h.get_text().lower()
    ]

    all_sections = []

    for header_tag in headlines:

        content = []
        p_count = 0

        for sibling in header_tag.find_next_siblings():
            # Stop if we hit a new header of the same or higher level
            if sibling.name in ['h2', 'h3', 'h4']:
                break

            if sibling.name in ['p', 'ul', 'ol']:
                text = _clean_text(sibling.get_text(separator=' '))

                # Skip empty paragraphs or highly specific trivia bullet points
                if not text or len(text) < 15:
                    continue

                content.append(text)
                p_count += 1

                # Truncate to avoid the TV episode recap bloat
                if p_count >= max_paragraphs:
                    break

        if content:
            all_sections.append("\n".join(content).strip())

    return all_sections


def scrape_wiki_entity(url: str) -> dict:
    headers = {
        'User-Agent': 'MiniRagBot/1.0 (contact@example.com)'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # 1. Extract Summary (Lead Paragraph)
    first_p = None
    for p in soup.select('.mw-parser-output > p'):
        if p.get_text(strip=True):
            first_p = _clean_text(p.get_text(separator=' '))
            break

    # 2. Extract Specific Sections (Returning Lists)
    appearances = _get_all_section_contents(
        soup, "Appearance", max_paragraphs=2)
    histories = _get_all_section_contents(soup, "History", max_paragraphs=2)
    quotes = _get_all_section_contents(soup, "Quotes", max_paragraphs=3)

    return {
        "url": url,
        "summary": first_p or "Summary not found.",
        "appearances": appearances,
        "histories": histories,
        "quotes": quotes
    }

# Helper to join the lists cleanly for the prompt


def format_list(lst): return "\n\n".join(lst) if lst else "None"


# --- Formatting the Prompt ---
if __name__ == "__main__":
    target_url = "https://bulbapedia.bulbagarden.net/wiki/Erika"
    try:
        entity_data = scrape_wiki_entity(target_url)

        llm_prompt = f"""
You are an expert lore master. Use the following character profile to answer the user's question. Stay true to the character's core demeanor and history.

--- CONTEXT ---
Summary:
{entity_data['summary']}

Appearance:
{format_list(entity_data['appearances'])}

History:
{format_list(entity_data['histories'])}

Notable Quotes:
{format_list(entity_data['quotes'])}
--- END CONTEXT ---

User Question: Based on her history and appearance, how would Erika likely react to a formal royal banquet?
"""
        print(llm_prompt)

    except Exception as e:
        print(f"Extraction failed: {e}")
