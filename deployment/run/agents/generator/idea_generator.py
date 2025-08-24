from __future__ import annotations

import os
import random
from typing import List

try:
    import google.generativeai as genai
except Exception:
    genai = None

SYSTEM_PROMPT = (
    "You are a creative merch ideation assistant. Generate short, catchy, PG-13 safe shirt slogans (2-6 words) tailored to the given trend/audience. Avoid trademarks and brand names."
)


def generate_ideas(trend_terms: List[str], num_ideas: int = 8) -> List[str]:
    """Generate slogan ideas using Gemini if configured; otherwise rule-based fallback."""
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    if genai and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            prompt = (
                f"Trend terms: {', '.join(trend_terms)}\n"
                "Generate a list of unique, punchy t-shirt slogans, 2-6 words, no brands/trademarks. One per line."
            )
            res = model.generate_content(SYSTEM_PROMPT + "\n\n" + prompt)
            text = res.candidates[0].content.parts[0].text if res and res.candidates else ""
            ideas = [line.strip("- \n\t") for line in text.splitlines() if line.strip()]
            cleaned = [i for i in ideas if 2 <= len(i.split()) <= 6][: num_ideas * 3]
            seen = set()
            result: List[str] = []
            for idea in cleaned:
                k = idea.lower()
                if k not in seen:
                    seen.add(k)
                    result.append(idea)
                if len(result) >= num_ideas:
                    break
            if result:
                return result
        except Exception:
            pass

    # Fallback: simple templates
    seeds = [t for t in trend_terms if t]
    if not seeds:
        seeds = ["vibes", "adventure", "coffee", "cats", "books", "retro", "minimal"]

    templates = [
        "Powered by {seed}",
        "Less talk, more {seed}",
        "I need {seed}",
        "Trust me, I'm {seed}",
        "Born for {seed}",
        "Keep it {seed}",
        "Just add {seed}",
        "Made of {seed}",
        "Future of {seed}",
        "Certified {seed}",
    ]

    out: List[str] = []
    random.shuffle(seeds)
    for seed in seeds:
        token = seed.split()[0].lower()
        token = token.replace("#", "").replace("@", "")
        for tmpl in random.sample(templates, k=min(3, len(templates))):
            out.append(tmpl.format(seed=token))
            if len(out) >= num_ideas:
                return out
    return out[:num_ideas]
