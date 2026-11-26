"""Public quotes and replay choices derived from persisted, server-generated cards."""
import re


def excerpt(text, limit=220):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def card_preview(card, text):
    data = card.get("data") or card
    program = data.get("course") or data.get("program_name") or data.get("program")
    amount = data.get("payable_confirmed") or data.get("first_year_total") or data.get("first_year_total_payable")
    scholarship = data.get("scholarship") or {}
    label = scholarship.get("label") if isinstance(scholarship, dict) else None
    percent = data.get("scholarship_percent", data.get("merit_percent"))
    if percent is not None and not label:
        label = f"{percent}% scholarship"
    if amount and program:
        return excerpt(" · ".join(str(v) for v in (program, label, f"First-year estimate {amount}") if v))
    title = data.get("title") or card.get("title") or program or card.get("type", "").replace("_", " ").title()
    detail = data.get("subtitle") or data.get("description") or text
    return excerpt(" · ".join(str(v) for v in (title, detail) if isinstance(v, str) and v))


def offered_choices(event):
    choices = set(event.get("suggestions") or [])
    for card in event.get("cards") or []:
        data = card.get("data") or card
        for key, field in (("options", "label"), ("programs", "name"), ("schools", "name")):
            choices.update(item[field] for item in data.get(key) or []
                           if isinstance(item, dict) and isinstance(item.get(field), str))
        if card.get("type") == "get_special_concessions":
            if data.get("allow_none"):
                choices.add("None of these apply")
            items = list(data.get("concessions") or [])
            for group in data.get("groups") or []:
                items.extend(group.get("items") or [])
            choices.update(f'Apply the "{item["category"]}" concession to my fee' for item in items
                           if isinstance(item, dict) and item.get("category"))
    return choices
