"""
AI service — Groq (text + vision via llama-4-scout) + Gemini Flash (vision fallback).

Vision tasks:  uses Gemini 2.0 Flash (GOOGLE_API_KEY) if set, else Groq llama-4-scout (GROQ_API_KEY).
Text tasks:    always uses Groq (fastest inference, llama-3.3-70b).
"""
import base64
import io
import json
import os
import httpx

from fastapi import HTTPException

# ── Lazy clients ──────────────────────────────────────────────────────────────

def _groq():
    import groq as _groq_lib
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise HTTPException(503, "GROQ_API_KEY not set — add to backend/.env")
    return _groq_lib.Groq(api_key=key)


def _gemini_model(model_name: str = "gemini-2.0-flash"):
    import google.generativeai as genai
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise HTTPException(503, "GOOGLE_API_KEY not set — add to backend/.env")
    genai.configure(api_key=key)
    return genai.GenerativeModel(model_name)


# ── Vision helper — Gemini preferred, Groq fallback ───────────────────────────

def _vision(prompt: str, image_b64: str) -> str:
    if os.getenv("GOOGLE_API_KEY"):
        try:
            return _gemini_vision(prompt, image_b64)
        except Exception as e:
            msg = str(e)
            # Fall back to Groq on rate-limit or quota errors
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                if os.getenv("GROQ_API_KEY"):
                    return _groq_vision(prompt, image_b64)
            raise
    if os.getenv("GROQ_API_KEY"):
        return _groq_vision(prompt, image_b64)
    raise HTTPException(503, "Set GOOGLE_API_KEY (Gemini) or GROQ_API_KEY (Groq) in backend/.env")


def _gemini_vision(prompt: str, image_b64: str) -> str:
    from PIL import Image
    model = _gemini_model("gemini-2.0-flash")
    img = Image.open(io.BytesIO(base64.b64decode(image_b64)))
    response = model.generate_content([prompt, img])
    return response.text


def _groq_vision(prompt: str, image_b64: str) -> str:
    client = _groq()
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }],
        max_tokens=1024,
    )
    return response.choices[0].message.content


# ── Text helper — Groq only ───────────────────────────────────────────────────

def _groq_text(prompt: str) -> str:
    client = _groq()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _parse_json(raw: str, opener: str = "{", closer: str = "}") -> dict | list:
    try:
        start = raw.index(opener)
        end = raw.rindex(closer) + 1
        return json.loads(raw[start:end])
    except Exception:
        raise HTTPException(500, f"AI returned unparseable response: {raw[:200]}")


# ── Public functions ──────────────────────────────────────────────────────────

def score_look(photo_b64: str, occasion: str, makeup: dict) -> dict:
    makeup_desc = ", ".join(f"{k}: {v}" for k, v in makeup.items() if v)
    prompt = f"""You are a professional makeup artist and beauty consultant.
Analyse this selfie and rate the makeup look for a {occasion} occasion.
Active makeup zones: {makeup_desc or "natural/no makeup"}.

Respond ONLY with a JSON object, no markdown, no explanation:
{{
  "overall": <0-10 float>,
  "color_harmony": <0-10 float>,
  "skin_match": <0-10 float>,
  "occasion_match": <0-10 float>,
  "vibe": "<2-4 word vibe label>",
  "tip": "<one actionable improvement tip, max 15 words>",
  "recommendation": "<one product or technique recommendation, max 20 words>"
}}"""
    return _parse_json(_vision(prompt, photo_b64))


def scan_face(photo_b64: str) -> dict:
    prompt = """You are a certified dermatologist and skincare AI.
Analyse this facial photo and return a detailed skin analysis.

Respond ONLY with a JSON object, no markdown:
{
  "skin_tone": "<fair|light|medium|tan|deep>",
  "undertone": "<warm|cool|neutral>",
  "skin_type": "<dry|oily|combination|normal>",
  "concerns": ["<concern1>", "<concern2>"],
  "hydration": "<low|medium|high>",
  "texture": "<smooth|slightly_uneven|uneven>",
  "pores": "<minimal|moderate|visible>",
  "recommendations": ["<tip1>", "<tip2>", "<tip3>"],
  "best_makeup_shades": {
    "foundation": "<shade description>",
    "blush": "<shade description>",
    "lips": "<shade description>"
  },
  "summary": "<2-3 sentence friendly summary>"
}"""
    return _parse_json(_vision(prompt, photo_b64))


def scan_nails(photo_b64: str) -> dict:
    prompt = """You are a professional nail technician and beauty consultant.
Analyse this nail photo and return a detailed nail analysis.

Respond ONLY with a JSON object, no markdown:
{
  "nail_shape": "<round|oval|square|almond|stiletto|coffin>",
  "nail_length": "<short|medium|long>",
  "nail_condition": "<healthy|slightly_damaged|damaged>",
  "cuticle_condition": "<well_maintained|needs_care|dry>",
  "concerns": ["<concern1>"],
  "recommended_shapes": ["<shape1>", "<shape2>"],
  "recommended_colors": ["<color1>", "<color2>", "<color3>"],
  "care_tips": ["<tip1>", "<tip2>"],
  "summary": "<2-3 sentence friendly summary>"
}"""
    return _parse_json(_vision(prompt, photo_b64))


async def analyze_and_generate(
    ar_b64: str,
    active_zones: list,
    colors: dict,
    occasion: str = "Everyday",
    skin_tone: str | None = None,
    undertone: str | None = None,
) -> dict:
    """Gemini Vision analyzes face → returns occasion-appropriate color recommendations + score."""
    tone_ctx = ""
    if skin_tone:
        tone_ctx += f"Skin tone: {skin_tone}. "
    if undertone:
        tone_ctx += f"Undertone: {undertone}. "

    # Occasion intensity guide so Gemini picks the right number of zones
    occasion_guides = {
        "Everyday": "minimal, 1-2 zones max (lips or blush only)",
        "Work": "polished but subtle, 2 zones (brows + lips or blush)",
        "Date Night": "romantic and elevated, 3-4 zones",
        "Party": "bold and full glam, 3-5 zones",
        "Wedding": "timeless and luminous, 4-5 zones",
        "Festival": "creative and expressive, 3-5 zones with color",
    }
    intensity = occasion_guides.get(occasion, "appropriate for the occasion, 2-3 zones")

    palette_ctx = ""
    if colors:
        palette_ctx = f"\nUser's selected palette: {colors}. Use these as the base — stay in the same color family but refine shades to perfectly suit their features and the occasion."

    prompt = f"""You are a world-class professional makeup artist AI. Create a COMPLETE makeover for this person.

Person details: {tone_ctx or "analyze from image."}
Occasion: {occasion} — {intensity}.
{palette_ctx}

Study this person's face carefully: skin tone, undertone, face shape, eye shape, lip shape, brow shape.

Create a FULL look appropriate for {occasion}. Always include AT MINIMUM: lips + eyes + blush. Add contour, highlight, brows, lipliner as the occasion demands. A complete makeover means all relevant zones are activated.

Respond ONLY with JSON (no markdown):
{{
  "zones": ["lips", "eyes", "blush"],
  "colors": {{
    "lips": "#hex",
    "blush": "#hex",
    "eyes": "#hex",
    "contour": "#hex",
    "highlight": "#hex",
    "brows": "#hex",
    "lipliner": "#hex",
    "liner": "#hex"
  }},
  "analysis": "<2 sentences: their notable features + why this complete look suits them for {occasion}>",
  "applied": ["<specific product e.g. 'Smoky taupe eye shadow'>", "<product 2>", "<product 3>"],
  "why": "<max 25 words: why these specific choices create the perfect {occasion} look for this person>",
  "score": <0.0-10.0 float: how well this complete look matches {occasion} and their features>
}}

Rules:
- "zones" must have AT LEAST lips + eyes + blush for any occasion
- "colors" must include a hex for every zone listed plus contour and highlight
- Stay true to the user's selected color palette family while refining for their features
- Colors must work for their undertone: warm → warm/golden; cool → cool/rosy; neutral → either
- All hex values must be valid 6-digit hex (e.g. "#C2856A")"""

    raw = _vision(prompt, ar_b64)
    data = _parse_json(raw)

    return {
        "zones": data.get("zones", active_zones or ["lips"]),
        "colors": data.get("colors", {}),
        "analysis": data.get("analysis", ""),
        "applied": data.get("applied", []),
        "why": data.get("why", ""),
        "score": float(data.get("score", 7.0)),
    }


def get_recommendations(profile: dict, occasion: str) -> list:
    skin_tone = profile.get("skin_tone") or "medium"
    undertone = profile.get("undertone") or "neutral"
    skin_type = profile.get("skin_type") or "normal"
    concerns = profile.get("concerns") or []

    prompt = f"""You are a professional makeup artist.
Suggest 3 makeup palettes for:
- Skin tone: {skin_tone}, undertone: {undertone}, skin type: {skin_type}
- Concerns: {", ".join(concerns) or "none"}
- Occasion: {occasion}

Respond ONLY with a JSON array, no markdown:
[
  {{
    "name": "<palette name>",
    "emoji": "<single emoji>",
    "occasion": "{occasion}",
    "colors": {{
      "lips": "<hex>", "blush": "<hex>", "eyes": "<hex>",
      "contour": "<hex>", "highlight": "<hex>", "brows": "<hex>",
      "gloss": "<hex>", "liner": "<hex>", "lashes": "<hex>"
    }},
    "zones": ["lips", "blush"],
    "why": "<one sentence why this suits them>"
  }}
]"""
    return _parse_json(_groq_text(prompt), "[", "]")
