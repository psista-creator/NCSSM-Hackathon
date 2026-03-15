"""
fish_detector.py (v2 - improved)
---------------------------------
Fish detection using MobileNetV2 with transfer learning support.
- Confidence threshold to avoid bad guesses
- Detailed species-to-habitat location lookup
- Works with or without fine-tuned weights

Usage:
    from fish_detector import detect_fish
    result = detect_fish("path/to/image.jpg")
    print(result)
"""

import os
import io
import numpy as np
from PIL import Image

import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import (
    MobileNetV2,
    preprocess_input,
    decode_predictions,
)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.30        # Must be >= 30% confident to count as fish
FINE_TUNED_WEIGHTS   = "fish_model_finetuned.h5"   # produced by train_fish_model.py

# ── Detailed species → habitat map ────────────────────────────────────────────
SPECIES_HABITAT = {
    "great white shark": ("Open ocean, coastal waters",         "Worldwide temperate/tropical seas"),
    "tiger shark":        ("Coastal reefs, open ocean",          "Tropical & subtropical oceans"),
    "hammerhead":         ("Coastal & offshore waters",          "Warm temperate to tropical oceans"),
    "whale shark":        ("Open ocean surface",                 "Tropical oceans worldwide"),
    "anemone fish":       ("Coral reefs, sea anemones",          "Indo-Pacific, Red Sea"),
    "clownfish":          ("Coral reefs, sea anemones",          "Indian & Pacific Oceans"),
    "rock beauty":        ("Coral reefs",                        "Western Atlantic, Caribbean"),
    "lionfish":           ("Coral reefs, rocky areas",           "Indo-Pacific (invasive in Atlantic)"),
    "puffer":             ("Coral reefs, estuaries",             "Tropical & subtropical seas"),
    "electric ray":       ("Sandy seabed, shallow water",        "Atlantic & Mediterranean"),
    "stingray":           ("Shallow coastal waters, sandy flats","Worldwide tropical/subtropical"),
    "tuna":               ("Open ocean, pelagic",                "Worldwide tropical & temperate seas"),
    "mackerel":           ("Open ocean, coastal",                "North Atlantic, Mediterranean"),
    "barracouta":         ("Open ocean, coastal",                "Southern Ocean, South Pacific"),
    "herring":            ("Open ocean, coastal",                "North Atlantic, North Pacific"),
    "anchovy":            ("Coastal, estuarine",                 "Worldwide temperate seas"),
    "salmon":             ("Rivers, lakes, open ocean",          "North Atlantic & Pacific"),
    "trout":              ("Cold freshwater rivers & lakes",     "North America, Europe"),
    "bass":               ("Freshwater lakes & rivers",          "North America"),
    "catfish":            ("Freshwater rivers & lakes",          "Worldwide"),
    "carp":               ("Freshwater lakes & slow rivers",     "Europe, Asia"),
    "goldfish":           ("Freshwater ponds / aquariums",       "Worldwide (domesticated)"),
    "tench":              ("Freshwater lakes & ponds",           "Europe, western Asia"),
    "flounder":           ("Sandy/muddy seabed, shallow coastal","Worldwide temperate seas"),
    "sole":               ("Sandy seabed, shallow coastal",      "Eastern Atlantic, Mediterranean"),
    "halibut":            ("Cold deep seabed",                   "North Atlantic & North Pacific"),
    "flatfish":           ("Shallow sandy/muddy seabed",         "Worldwide coastal waters"),
    "eel":                ("Freshwater rivers, coastal sea",     "Europe, North America"),
    "electric eel":       ("Freshwater rivers",                  "South America (Amazon basin)"),
    "sturgeon":           ("Large rivers, coastal sea",          "North America, Europe, Asia"),
    "gar":                ("Freshwater rivers & lakes",          "North & Central America"),
    "coho":               ("Rivers, coastal ocean",              "North Pacific"),
}

FISH_KEYWORDS = [
    "fish", "shark", "ray", "eel", "tuna", "salmon", "trout", "cod",
    "bass", "perch", "pike", "carp", "herring", "anchovy", "mackerel",
    "snapper", "grouper", "flounder", "sole", "halibut", "catfish",
    "tilapia", "barracuda", "lionfish", "puffer", "anemone", "goldfish",
    "sturgeon", "gar", "coho", "tench", "flatfish", "stingray",
]

# ── Load model ────────────────────────────────────────────────────────────────
print("Loading fish detection model…")
if os.path.exists(FINE_TUNED_WEIGHTS):
    print(f"  ✓ Fine-tuned weights found: {FINE_TUNED_WEIGHTS}")
    _model = tf.keras.models.load_model(FINE_TUNED_WEIGHTS)
    _use_fine_tuned = True
else:
    print("  ℹ Using base ImageNet MobileNetV2")
    print("    (run train_fish_model.py for better species accuracy)")
    _model = MobileNetV2(weights="imagenet")
    _use_fine_tuned = False
print("Model ready.\n")


# ── Public API ────────────────────────────────────────────────────────────────

def detect_fish(image_input, top_k: int = 3) -> dict:
    """
    Detect whether an image contains a fish and identify the species.

    Parameters
    ----------
    image_input : str | PIL.Image.Image | np.ndarray | bytes
        File path, PIL Image, NumPy array, or raw bytes.
    top_k : int
        How many top predictions to include in results.

    Returns
    -------
    dict:
        is_fish         : bool
        species         : str
        confidence      : float  (0–1)
        top_predictions : list of (label, confidence)
        habitat         : str
        ocean_region    : str
        model_version   : str
    """
    img  = _load_image(image_input)
    arr  = _preprocess(img)
    preds   = _model.predict(arr, verbose=0)
    decoded = decode_predictions(preds, top=top_k)[0]
    top_predictions = [(label, float(prob)) for (_, label, prob) in decoded]

    # Find the best fish prediction that clears the confidence threshold
    fish_match = None
    for label, conf in top_predictions:
        if _is_fish_label(label) and conf >= CONFIDENCE_THRESHOLD:
            fish_match = (label, conf)
            break

    is_fish = fish_match is not None
    if is_fish:
        species_raw, confidence = fish_match
        species = _clean_label(species_raw)
        habitat, region = _lookup_habitat(species)
    else:
        species    = "unknown"
        confidence = top_predictions[0][1] if top_predictions else 0.0
        habitat    = "N/A"
        region     = "N/A"

    return {
        "is_fish":         is_fish,
        "species":         species,
        "confidence":      round(confidence, 4),
        "top_predictions": [(l, round(c, 4)) for l, c in top_predictions],
        "habitat":         habitat,
        "ocean_region":    region,
        "model_version":   "fine-tuned" if _use_fine_tuned else "base-imagenet",
    }


def detect_fish_from_bytes(image_bytes: bytes) -> dict:
    """Convenience wrapper for raw image bytes (e.g. from a web upload)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return detect_fish(img)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_image(src) -> Image.Image:
    if isinstance(src, str):
        if not os.path.exists(src):
            raise FileNotFoundError(f"Image not found: {src}")
        return Image.open(src).convert("RGB")
    if isinstance(src, bytes):
        return Image.open(io.BytesIO(src)).convert("RGB")
    if isinstance(src, np.ndarray):
        return Image.fromarray(src.astype("uint8")).convert("RGB")
    if isinstance(src, Image.Image):
        return src.convert("RGB")
    raise TypeError(f"Unsupported image input type: {type(src)}")


def _preprocess(img: Image.Image) -> np.ndarray:
    img = img.resize((224, 224))
    arr = np.expand_dims(np.array(img, dtype=np.float32), axis=0)
    return preprocess_input(arr)


def _is_fish_label(label: str) -> bool:
    label_lower = label.lower().replace("_", " ")
    return any(kw in label_lower for kw in FISH_KEYWORDS)


def _clean_label(label: str) -> str:
    return label.replace("_", " ").title()


def _lookup_habitat(species: str) -> tuple:
    s = species.lower()
    if s in SPECIES_HABITAT:
        return SPECIES_HABITAT[s]
    for key, val in SPECIES_HABITAT.items():
        if key in s or s in key:
            return val
    if any(w in s for w in ["shark", "ray", "barracuda", "lionfish"]):
        return ("Open ocean / coral reef", "Tropical seas worldwide")
    if any(w in s for w in ["salmon", "trout", "bass", "carp"]):
        return ("Freshwater river or lake", "North America / Europe")
    return ("Marine environment", "Location unknown — check species range maps")