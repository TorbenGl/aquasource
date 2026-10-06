"""Map a licence string (name, SPDX id or URL) to a project tier.

Tiers:
    A  public domain, CC0, US-government work, DL-DE-ZERO
    B  CC BY 3.0/4.0 (any port), OGL-Canada, OGL-UK v3, Etalab / Licence Ouverte 2.0,
       DL-DE-BY-2.0, NLOD
    C  CC BY-SA (separate share-alike shard, off by default)
    U  unknown, unread, or contradictory
    X  excluded: any NC or ND term, research-only, academic-only, no redistribution

Anything that is not clearly recognised is U. NC/ND checks run first, so
"CC BY-NC-SA" is X, never C.
"""

from __future__ import annotations

import re

from .schema import Licence

_EXCLUDE_PATTERNS = [
    r"\bnc\b",
    r"-nc\b",
    r"\bnc-",
    r"non[\s-]?commercial",
    r"\bnd\b",
    r"-nd\b",
    r"\bnd-",
    r"no[\s-]?deriv",
    r"research[\s-]+(use[\s-]+)?only",
    r"academic[\s-]+(use[\s-]+)?only",
    r"non[\s-]?profit[\s-]+(use[\s-]+)?only",
    r"not\s+for\s+commercial",
    r"personal\s+use\s+only",
    r"all\s+rights\s+reserved",
    r"no\s+redistribution",
]

_TIER_A_PATTERNS = [
    r"\bcc0\b",
    r"cc[\s-]?zero",
    r"publicdomain/zero",
    r"public[\s-]+domain",
    r"publicdomain/mark",
    r"\bpdm\b",
    r"u\.?s\.?\s+government\s+work",
    r"us[\s-]+gov(ernment)?\s+work",
    r"not\s+subject\s+to\s+copyright",
    r"dl-de[\s/-]*zero",
    r"datenlizenz\s+deutschland\s+.?\s*zero",
]

_TIER_C_PATTERNS = [
    r"by[\s-]?sa\b",
    r"licenses/by-sa/",
    r"share[\s-]?alike",
]

_TIER_B_PATTERNS = [
    r"\bcc[\s-]?by\b",
    r"creative\s+commons\s+attribution\b",
    r"licenses/by/",
    r"attribution\s+[34]\.0",
    r"open\s+government\s+licen[cs]e\s*[-–—]?\s*canada",
    r"\bogl[\s-]?(canada|ca)\b",
    r"open\s+government\s+licen[cs]e(\s+v(ersion)?\s*3(\.0)?)?",
    r"\bogl[\s-]?uk",
    r"nationalarchives\.gov\.uk/doc/open-government-licence",
    r"open\.canada\.ca/en/open-government-licence",
    r"licence\s+ouverte",
    r"open\s+licen[cs]e\s+2\.0",
    r"\betalab",
    r"dl-de[\s/-]*by",
    r"datenlizenz\s+deutschland\s+.?\s*namensnennung",
    r"\bnlod\b",
    r"norwegian\s+licen[cs]e\s+for\s+open\s+government\s+data",
    r"data\.norge\.no/nlod",
]


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(licence: str | None) -> str:
    """Return the tier letter (A, B, C, U or X) for a licence string."""
    if not licence or not licence.strip():
        return "U"
    text = licence.strip().lower().replace("_", "-")
    if _matches(_EXCLUDE_PATTERNS, text):
        return "X"
    if _matches(_TIER_C_PATTERNS, text):
        return "C"
    if _matches(_TIER_A_PATTERNS, text):
        return "A"
    if _matches(_TIER_B_PATTERNS, text):
        return "B"
    return "U"


def combine(*tiers: str) -> str:
    """Combine tiers read from several sources for the same item.

    Any X wins; otherwise contradictory known tiers make the item U (the spec
    says to hold contradictions until resolved). Unknowns are ignored when a
    more specific level gave an answer, so pass tiers most-specific first and
    use :func:`most_specific` for the usual file > record > collection rule.
    """
    known = [t for t in tiers if t and t != "U"]
    if "X" in known:
        return "X"
    if not known:
        return "U"
    if len(set(known)) > 1:
        return "U"
    return known[0]


def most_specific(*levels: tuple[str, str | None]) -> tuple[str, str]:
    """Pick the licence from the most specific level that states one.

    ``levels`` are ``(level_name, licence_string_or_None)`` ordered
    file -> record -> collection. Returns ``(level_name, licence_string)``, or
    ``("unknown", "")`` when nothing is stated.
    """
    for level, text in levels:
        if text and text.strip():
            return level, text.strip()
    return "unknown", ""


def make_licence(
    name: str | None,
    *,
    level: str,
    url: str | None,
    attribution: str,
    tier: str | None = None,
) -> Licence:
    """Build a :class:`Licence`, classifying ``name`` unless ``tier`` is forced."""
    name = (name or "").strip() or "not stated"
    return Licence(
        name=name,
        tier=tier or classify(name),
        level=level if level in ("file", "record", "collection") else "unknown",
        url=url,
        attribution=attribution,
    )
