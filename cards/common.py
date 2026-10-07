"""Shared card helpers, footer, and interactive card sanitizers."""
from datetime import datetime
import re
from typing import Optional, Dict, Any, List

from cards.locales import BRAND_FOOTER_PREFIX


def create_footer():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"{BRAND_FOOTER_PREFIX} | 🕒 {now}"
            }
        ]
    }


def normalize_markdown_for_feishu(text: str) -> str:
    """Normalize model markdown output for optimal rendering in Feishu cards.

    1. Converts markdown ATX headings (# Title, ## Title, ### Title) to **Title**
       outside of fenced code blocks, preventing code comments from being corrupted.
    2. Ensures clean paragraph separation after headings.
    3. Normalizes multiple excessive empty lines.
    """
    if not text:
        return text

    # Split by fenced code blocks (```...```) to keep code blocks intact
    parts = re.split(r'(```[\s\S]*?```)', text)
    transformed = []
    for i, part in enumerate(parts):
        # Even indices are outside code blocks; odd indices are code blocks
        if i % 2 == 0:
            # Transform ATX headings (# Title) to bold
            part = re.sub(r'(?m)^#{1,6}\s+(.+?)\s*$', r'**\1**', part)
            # Ensure line break separation after converted headings
            part = re.sub(r'(\*\*[^\n]+\*\*)\n(?!\n)', r'\1\n\n', part)
            # Normalize excessive empty lines (max 2)
            part = re.sub(r'\n{3,}', '\n\n', part)
            # Normalize curly quotes to bracket quotes outside inline backticks
            sub_parts = re.split(r'(`[^`\n]+`)', part)
            for j, sub_p in enumerate(sub_parts):
                if j % 2 == 0:
                    sub_parts[j] = sub_p.replace('“', '「').replace('”', '」').replace('‘', '『').replace('’', '』')
            part = "".join(sub_parts)
        transformed.append(part)

    return "".join(transformed)



def build_card(
    header: Optional[Dict[str, Any]] = None,
    elements: Optional[List[Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standard Feishu Interactive Card structure."""
    card = {
        "config": config or {"wide_screen_mode": True},
        "elements": elements or []
    }
    if header:
        card["header"] = header
    return card


def sanitize_card_for_feishu(card: Any) -> Any:
    """Ensure card structure strictly conforms to Feishu Interactive Card schema,
    unwrapping any accidental schema 2.0 / body wrapping that causes ErrCode 200861."""
    if not isinstance(card, dict):
        return card

    card_clean = dict(card)
    card_clean.pop("schema", None)
    if "body" in card_clean and isinstance(card_clean["body"], dict):
        if "elements" in card_clean["body"]:
            card_clean["elements"] = card_clean["body"]["elements"]
        card_clean.pop("body", None)
    return card_clean


# Backwards compatibility alias
ensure_schema2 = sanitize_card_for_feishu

