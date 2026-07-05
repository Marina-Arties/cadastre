from math import ceil


def _make_trigrams(text: str) -> set[str]:
    padded = "  " + text + " "
    return {padded[i:i + 3] for i in range(len(padded) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    if not a.strip() and not b.strip():
        return 0.0
    ta = _make_trigrams(a)
    tb = _make_trigrams(b)
    if not ta or not tb:
        return 0.0
    intersection = ta & tb
    union = ta | tb
    if not union:
        return 0.0
    return len(intersection) / len(union)
