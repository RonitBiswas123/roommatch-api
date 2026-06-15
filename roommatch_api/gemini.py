import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_traits(text: str) -> list:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
You are analyzing a student's self-description to extract personality traits for a roommate matching app.

Student's description:
"{text}"

Extract exactly 3-5 personality traits from this description.
Choose traits from these categories:
- Sleep style: Night Owl, Early Bird, Flexible Sleeper
- Social style: Introvert, Extrovert, Ambivert
- Study style: Heavy Studier, Moderate Studier, Light Studier
- Lifestyle: Coder, Gamer, Athlete, Artist, Musician, Reader
- Cleanliness: Neat Freak, Organized, Relaxed
- Noise: Quiet Person, Social Person, Party Person

Return ONLY a JSON array of strings. No explanation. No markdown. No backticks.
Example: ["Night Owl", "Introvert", "Coder", "Organized"]
"""

        response = model.generate_content(prompt)
        text_response = response.text.strip()
        text_response = text_response.replace('```json', '').replace('```', '').strip()
        traits = json.loads(text_response)

        if isinstance(traits, list):
            return [str(t) for t in traits[:5]]
        return []

    except Exception as e:
        print(f"Gemini error: {e}")
        return ["Student", "Roommate Seeker"]