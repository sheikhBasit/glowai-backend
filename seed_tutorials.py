"""
Seed tutorials from real YouTube videos using yt-dlp (no API key needed).
Searches YouTube by category, extracts products from description, steps from transcript.
Run: venv/bin/python3 seed_tutorials.py
"""
import os, re, sys, subprocess, json

CATEGORIES = [
    ("lips",      "how to apply lipstick tutorial step by step",         "beginner",     0),
    ("lips",      "ombre lip gradient tutorial makeup",                   "intermediate", 1),
    ("eyes",      "beginner eye shadow blending tutorial",                "beginner",    10),
    ("eyes",      "smoky eye easy tutorial step by step",                 "intermediate",11),
    ("eyes",      "hooded eyes makeup tutorial tips",                     "intermediate",12),
    ("blush",     "blush placement tutorial makeup",                      "beginner",    20),
    ("contour",   "contouring for beginners tutorial face",               "beginner",    30),
    ("highlight", "how to apply highlighter glow tutorial",               "beginner",    40),
    ("brows",     "natural eyebrow tutorial beginner fill in",            "beginner",    50),
    ("brows",     "soap brows fluffy tutorial",                           "beginner",    51),
    ("lashes",    "how to apply false lashes tutorial beginner",          "beginner",    60),
    ("liner",     "eyeliner tutorial for beginners wing",                 "beginner",    70),
    ("skincare",  "skin prep before makeup routine",                      "beginner",    80),
    ("nails",     "beginner at home manicure tutorial",                   "beginner",    90),
]


def is_available(video_id: str) -> bool:
    """Check if a video is publicly available and embeddable."""
    cmd = ["yt-dlp", "--simulate", "--quiet", "--no-warnings",
           "--match-filter", "!is_live",
           f"https://www.youtube.com/watch?v={video_id}"]
    try:
        subprocess.check_output(cmd, timeout=20, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def ytdlp_search(query: str, n: int = 6) -> list[dict]:
    """Search YouTube, verify availability, return up to 2 good videos."""
    cmd = [
        "yt-dlp", f"ytsearch{n}:{query}",
        "--print", "%(id)s|||%(title)s|||%(channel)s|||%(thumbnail)s|||%(age_limit)s",
        "--match-filter", "!is_live",
        "--no-download", "--quiet", "--no-warnings",
    ]
    try:
        out = subprocess.check_output(cmd, timeout=30, text=True, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"    yt-dlp search failed: {e}")
        return []

    candidates = []
    for line in out.strip().splitlines():
        parts = line.split("|||")
        if len(parts) < 3:
            continue
        age_limit = int(parts[4].strip() or "0") if len(parts) > 4 else 0
        if age_limit > 0:
            continue
        candidates.append({
            "id": parts[0].strip(),
            "title": parts[1].strip(),
            "channel": parts[2].strip(),
            "thumbnail": parts[3].strip() if len(parts) > 3 else None,
        })

    results = []
    for v in candidates:
        if is_available(v["id"]):
            results.append(v)
            if len(results) >= 2:
                break
        else:
            print(f"    skipping unavailable: {v['title'][:40]}")
    return results


def ytdlp_description(video_id: str) -> str:
    """Fetch full description of a video."""
    cmd = [
        "yt-dlp", f"https://www.youtube.com/watch?v={video_id}",
        "--print", "%(description)s",
        "--no-download", "--quiet", "--no-warnings",
    ]
    try:
        return subprocess.check_output(cmd, timeout=20, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def extract_products(desc: str) -> list[str]:
    """Pull product-like lines from a description."""
    # Try to isolate a products/shop section
    section = re.search(
        r'(PRODUCT[S]?\s+USED|SHOP\s+MY|WHAT\s+I\s+USED|LINKS?|TOOLS?\s+USED|ITEMS?\s+MENTIONED)[:\s]*\n(.*?)(\n\n|\Z)',
        desc, re.IGNORECASE | re.DOTALL
    )
    block = section.group(2) if section else desc

    products = []
    for line in block.splitlines():
        line = line.strip()
        if not line or len(line) > 85 or len(line) < 5:
            continue
        if re.search(r'https?://|subscribe|follow|instagram|tiktok|twitter|coupon|@\w|youtube\.com', line, re.I):
            continue
        cleaned = re.sub(r'^[-•*✦✿\d.\)]+\s*', '', line).strip()
        # must have a capital letter and not be a sentence (no verb-like endings)
        if cleaned and re.search(r'[A-Z]', cleaned) and not re.search(r'\b(is|are|was|were|have|has|had|do|does|did)\b', cleaned, re.I):
            products.append(cleaned)
        if len(products) >= 10:
            break
    return products


def extract_steps(video_id: str) -> list[dict]:
    """Get transcript and chunk into tutorial steps (~60s each)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        segs = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
    except Exception as e:
        print(f"    no transcript: {e}")
        return []

    chunks, buf, t0 = [], [], 0.0
    for seg in segs:
        buf.append(seg.text)
        if seg.start - t0 >= 55 or seg is segs[-1]:
            text = re.sub(r'\[.*?\]|\(.*?\)', '', " ".join(buf))
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 25:
                chunks.append(text)
            buf, t0 = [], seg.start

    labels = ["Prep & Tools", "Base Application", "Building Color", "Blending", "Detail Work", "Finishing Touches"]
    return [
        {"title": labels[i] if i < len(labels) else f"Step {i+1}", "instruction": chunk[:350]}
        for i, chunk in enumerate(chunks[:6])
    ]


def seed():
    from database import SessionLocal
    from models import Tutorial

    db = SessionLocal()
    added = 0

    for category, query, difficulty, sort_order in CATEGORIES:
        print(f"\n→ [{category}] {query}")
        videos = ytdlp_search(query, n=2)
        if not videos:
            print("  no results")
            continue

        for i, v in enumerate(videos):
            vid_id = v["id"]
            yt_url = f"https://www.youtube.com/watch?v={vid_id}"

            exists = db.query(Tutorial).filter(Tutorial.video_url == yt_url).first()
            if exists:
                print(f"  skip (exists): {v['title'][:55]}")
                continue

            print(f"  [{i+1}] {v['title'][:60]} — {v['channel']}")
            desc     = ytdlp_description(vid_id)
            products = extract_products(desc)
            steps    = extract_steps(vid_id)
            print(f"      ✓ {len(steps)} steps, {len(products)} products")

            db.add(Tutorial(
                title=v["title"],
                category=category,
                difficulty=difficulty,
                video_url=yt_url,
                sort_order=sort_order * 10 + i,
                content={
                    "thumbnail": v.get("thumbnail"),
                    "channel": v["channel"],
                    "steps": steps,
                    "products": products,
                },
            ))
            added += 1

    db.commit()
    db.close()
    print(f"\nDone — {added} tutorials seeded.")


def backfill_steps():
    """Fill in missing transcript steps for already-seeded tutorials."""
    from database import SessionLocal
    from models import Tutorial
    import re

    db = SessionLocal()
    rows = db.query(Tutorial).all()
    updated = 0

    for t in rows:
        content = t.content or {}
        if content.get("steps"):
            continue  # already has steps
        if not t.video_url or "watch?v=" not in t.video_url:
            continue
        vid_id = t.video_url.split("watch?v=")[-1]
        print(f"  backfill: {t.title[:55]}")
        steps = extract_steps(vid_id)
        if steps:
            content["steps"] = steps
            t.content = content
            updated += 1
            print(f"    ✓ {len(steps)} steps")

    db.commit()
    db.close()
    print(f"Backfilled {updated} tutorials.")


def clean():
    """Remove tutorials whose YouTube URL is no longer available."""
    from database import SessionLocal
    from models import Tutorial

    db = SessionLocal()
    rows = db.query(Tutorial).filter(Tutorial.video_url.isnot(None)).all()
    removed = 0
    for t in rows:
        vid_id = t.video_url.split("watch?v=")[-1] if "watch?v=" in (t.video_url or "") else None
        if not vid_id:
            continue
        print(f"  checking: {t.title[:55]}")
        if not is_available(vid_id):
            print(f"    ✗ unavailable — removing")
            db.delete(t)
            removed += 1
    db.commit()
    db.close()
    print(f"\nRemoved {removed} unavailable tutorials.")


if __name__ == "__main__":
    import sys
    if "backfill" in sys.argv:
        backfill_steps()
    elif "clean" in sys.argv:
        clean()
    else:
        seed()
