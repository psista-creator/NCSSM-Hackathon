import cv2
import numpy as np
import os
import random
 
# Point this env var to a fish-trained YOLOv8 .pt file for real detection
FISH_MODEL_PATH = os.environ.get("FISH_MODEL_PATH", None)
CONFIDENCE_THRESHOLD = 0.50
FISH_LABELS = {"fish"}  # expand for species-specific models
 
 
class FishClassifier:
    def __init__(self, sim_mode: bool = False):
        """
        sim_mode: skips model loading and fakes detections.
                  Use for testing the pipeline without a GPU or camera.
        """
        self.sim_mode = sim_mode
        self.model = None
 
        if not sim_mode:
            self._load_model()
 
    def _load_model(self):
        try:
            from ultralytics import YOLO
 
            if FISH_MODEL_PATH and os.path.exists(FISH_MODEL_PATH):
                print(f"[Classifier] Loading custom fish model: {FISH_MODEL_PATH}")
                self.model = YOLO(FISH_MODEL_PATH)
            else:
                print("[Classifier] No custom model found — loading YOLOv8n (COCO).")
                print("[Classifier] ⚠ Supply a fish-trained model for real accuracy.")
                self.model = YOLO("yolov8n.pt")
 
        except ImportError:
            print("[Classifier] ultralytics not installed. Switching to sim mode.")
            self.sim_mode = True
 
    def classify(self, frame: np.ndarray) -> dict:
        """
        Run classification on a single frame.
 
        Returns:
            {
                "is_fish": bool,
                "confidence": float,
                "bbox": (x1, y1, x2, y2) or None,
                "label": str or None,
                "annotated_frame": np.ndarray,
            }
        """
        if self.sim_mode:
            return self._simulate(frame)
 
        results = self.model(frame, verbose=False)[0]
        annotated = results.plot()
 
        for box in results.boxes:
            label = self.model.names[int(box.cls)]
            confidence = float(box.conf)
 
            if label.lower() in FISH_LABELS and confidence >= CONFIDENCE_THRESHOLD:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                return {
                    "is_fish": True,
                    "confidence": confidence,
                    "bbox": (x1, y1, x2, y2),
                    "label": label,
                    "annotated_frame": annotated,
                }
 
        return {
            "is_fish": False,
            "confidence": 0.0,
            "bbox": None,
            "label": None,
            "annotated_frame": annotated,
        }
 
    def _simulate(self, frame: np.ndarray) -> dict:
        """Fake a fish detection ~40% of the time for pipeline testing."""
        annotated = frame.copy()
        detected = random.random() < 0.4
 
        if detected:
            h, w = frame.shape[:2]
            x1, y1 = random.randint(0, w // 2), random.randint(0, h // 2)
            x2, y2 = random.randint(w // 2, w), random.randint(h // 2, h)
            confidence = round(random.uniform(0.55, 0.98), 2)
 
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"Fish [{confidence:.0%}]",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
 
            return {
                "is_fish": True,
                "confidence": confidence,
                "bbox": (x1, y1, x2, y2),
                "label": "fish (simulated)",
                "annotated_frame": annotated,
            }
 
        return {
            "is_fish": False,
            "confidence": 0.0,
            "bbox": None,
            "label": None,
            "annotated_frame": annotated,
        }
 
