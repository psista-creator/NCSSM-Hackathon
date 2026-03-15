import cv2, json, os, uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FISH_IMAGE_DIR = os.path.join(BASE_DIR, "data", "fish")
DB_FILE = os.path.join(BASE_DIR, "data", "database.json")
REWARD_THRESHOLD = 10

class Database:
    def __init__(self):
        os.makedirs(FISH_IMAGE_DIR, exist_ok=True)
        self.db = self._load()

    def _load(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return json.load(f)
        return {"total_collected": 0, "rewards_earned": 0, "fish": []}

    def _save(self):
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump(self.db, f, indent=2)

    def save_fish(self, frame, detection):
        fish_id = str(uuid.uuid4())[:8]
        filename = "fish_" + fish_id + ".jpg"
        filepath = os.path.join(FISH_IMAGE_DIR, filename)
        bbox = detection.get("bbox")
        if bbox:
            x1, y1, x2, y2 = bbox
            crop = frame[y1:y2, x1:x2]
            cv2.imwrite(filepath, crop if crop.size > 0 else frame)
        else:
            cv2.imwrite(filepath, frame)
        self.db["fish"].append({"id": fish_id, "filename": filename, "label": detection.get("label", "fish"), "confidence": round(detection.get("confidence", 0.0), 3)})
        self.db["total_collected"] += 1
        reward_triggered = self.db["total_collected"] % REWARD_THRESHOLD == 0
        if reward_triggered:
            self.db["rewards_earned"] += 1
        self._save()
        print("[Database] Saved fish #" + str(self.db["total_collected"]))
        if reward_triggered:
            print("[Database] Reward triggered!")
        return {"fish_id": fish_id, "total": self.db["total_collected"], "reward_triggered": reward_triggered}

    def get_stats(self):
        total = self.db["total_collected"]
        return {"total_collected": total, "rewards_earned": self.db["rewards_earned"], "next_reward_in": REWARD_THRESHOLD - (total % REWARD_THRESHOLD)}

    def get_collection(self):
        return self.db["fish"]