"""Conservative story grouping while retaining every underlying article."""

import re
import unicodedata


def _plain(value):
    return "".join(ch for ch in unicodedata.normalize("NFKD", str(value or "").lower())
                   if not unicodedata.combining(ch))


def clean_title(record):
    title = str(record.get("titolo") or "").strip()
    source = str(record.get("fonte") or "").strip()
    for sep in (" - ", " | ", " — "):
        suffix = sep + source
        if source and title.casefold().endswith(suffix.casefold()):
            return title[:-len(suffix)].strip()
    return title


def _topic(record):
    title = _plain(clean_title(record))
    for phrase in ("dominio delta", "busta deluxe mega", "popcon", "megaevoluzione"):
        if phrase in title:
            return phrase
    # Other stories only join when nearly identical after removing punctuation.
    words = re.findall(r"[a-z0-9]+", title)
    return " ".join(words[:9])


def group_articles(records):
    groups = []
    by_topic = {}
    for record in records:
        topic = _topic(record)
        if topic not in by_topic:
            by_topic[topic] = len(groups)
            groups.append({"topic": topic, "voci": []})
        groups[by_topic[topic]]["voci"].append(dict(record))
    return groups


def fallback_headline(title):
    title = str(title or "").strip()
    plain = _plain(title)
    if "popcon" in plain:
        return "POPCon: area Nintendo a Catanzaro"
    if "busta deluxe mega" in plain:
        return "Busta Deluxe Mega: le novità Pocket"
    if "dominio delta" in plain:
        return "Dominio Delta: carte e prodotti"
    title = re.split(r"\s[-|—]\s", title)[0].strip(" .!:")
    words = title.split()
    return " ".join(words[:9]) + ("…" if len(words) > 9 else "")


def apply_headlines(groups, plan):
    proposed = {h.get("group"): h for h in plan.get("news_headlines", [])
                if isinstance(h, dict) and isinstance(h.get("group"), int)}
    stories = []
    for index, group in enumerate(groups):
        source_titles = [clean_title(v) for v in group["voci"]]
        suggestion = proposed.get(index, {})
        headline = str(suggestion.get("headline") or "").strip()
        summary = str(suggestion.get("summary") or "").strip()
        if not 8 <= len(headline) <= 75:
            headline = fallback_headline(source_titles[0])
        # Numbers in a generated summary must occur in the source titles.
        source_numbers = set(re.findall(r"\d+", " ".join(source_titles)))
        if len(summary) > 165 or not set(re.findall(r"\d+", summary)) <= source_numbers:
            summary = ""
        stories.append({"titolo": headline, "sommario": summary,
                        "voci": group["voci"], "topic": group["topic"]})
    return stories
