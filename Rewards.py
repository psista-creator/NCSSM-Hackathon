from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


SPECIES_BASE_RARITY: dict[str, float] = {
    # Very common / aquarium
    "goldfish": 0.05, "clownfish": 0.10, "anemone fish": 0.10,
    # Common pelagic
    "tuna": 0.20, "mackerel": 0.20, "herring": 0.20, "anchovy": 0.20,
    "salmon": 0.25, "trout": 0.25, "bass": 0.25, "catfish": 0.25, "carp": 0.25,
    # Uncommon
    "flounder": 0.40, "sole": 0.40, "halibut": 0.40, "flatfish": 0.40,
    "eel": 0.45, "puffer": 0.45, "lionfish": 0.45, "stingray": 0.50,
    # Rare
    "barracouta": 0.60, "barracuda": 0.65, "electric ray": 0.65,
    "hammerhead": 0.70, "tiger shark": 0.72, "sturgeon": 0.75,
    "electric eel": 0.75, "gar": 0.75, "coho": 0.70,
    # Legendary
    "great white shark": 0.90, "whale shark": 0.92, "rock beauty": 0.80,
}

RARITY_TIERS = [
    (0.00, 0.30, "common"),
    (0.30, 0.55, "uncommon"),
    (0.55, 0.75, "rare"),
    (0.75, 1.01, "legendary"),
]

MILESTONES = [5, 10, 25, 50, 100]


@dataclass
class RarityResult:
    score: float          # 0–1
    tier: str             # common | uncommon | rare | legendary
    local_proportion: Optional[float]   # fraction of this species in area, if provided

def compute_rarity(
    species: str,
    area_catches: Optional[list[str]] = None,
) -> RarityResult:
    """
    Compute a rarity score for a species, optionally adjusted by local prevalence.

    Parameters
    ----------
    species       : detected species name (lowercase)
    area_catches  : list of species strings from recent catches in the same area. If provided, local proportion lowers rarity for over-represented species and raises it for under-represented ones. """
    base = _base_rarity(species)

    local_proportion: Optional[float] = None
    if area_catches and len(area_catches) > 0:
        total = len(area_catches)
        count = sum(1 for s in area_catches if s.lower() == species.lower())
        local_proportion = count / total
        proportion_rarity = 1.0 - local_proportion
        score = round(0.60 * base + 0.40 * proportion_rarity, 4)
    else:
        score = base

    score = max(0.0, min(1.0, score))
    tier  = _score_to_tier(score)
    return RarityResult(score=score, tier=tier, local_proportion=local_proportion)


def _base_rarity(species: str) -> float:
    s = species.lower()
    if s in SPECIES_BASE_RARITY:
        return SPECIES_BASE_RARITY[s]
    # Fuzzy fallback
    for key, val in SPECIES_BASE_RARITY.items():
        if key in s or s in key:
            return val
    return 0.35  #Unknown Species in the database are seen as uncommon


def _score_to_tier(score: float) -> str:
    for low, high, tier in RARITY_TIERS:
        if low <= score < high:
            return tier
    return "common"


def _generate_token(user_id: int, reward_id: int) -> str:
    import uuid, hashlib, time
    raw = f"{user_id}-{reward_id}-{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
