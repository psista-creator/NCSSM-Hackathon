from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import io
import base64
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw, ImageFont


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

REDEMPTION_BASE_URL = "http://localhost:8000/redeem"
QR_DARK_COLOR  = (15, 82, 130)
QR_LIGHT_COLOR = (240, 248, 255)

def generate_qr(token: str, reward_title: str) -> str:
    """Generate a branded QR code. Returns base64-encoded PNG string."""
    url = f"{REDEMPTION_BASE_URL}/{token}"
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(
            front_color=QR_DARK_COLOR,
            back_color=QR_LIGHT_COLOR,
        ),
    ).convert("RGB")

    img = _add_qr_label(img, reward_title)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _add_qr_label(img: Image.Image, title: str, max_chars: int = 36) -> Image.Image:
    label = title if len(title) <= max_chars else title[:max_chars - 1] + "…"
    bar_height = 44
    new_img = Image.new("RGB", (img.width, img.height + bar_height), QR_DARK_COLOR)
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    x = (new_img.width - text_w) // 2
    y = img.height + (bar_height - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), label, fill=(240, 248, 255), font=font)
    return new_img
