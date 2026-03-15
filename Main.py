import argparse
import time
import cv2
import numpy as np
import random
 
from fish_classifier import FishClassifier
from db import Database
from Rewards import generate_qr
 
COOLDOWN_SECONDS = 3  # Prevents saving duplicates from one fish pass
 
 
def main():
    parser = argparse.ArgumentParser(description="Buoy Fish Scanner")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    args = parser.parse_args()
 
    classifier = FishClassifier(sim_mode=args.sim)
    db = Database()
 
    stats = db.get_stats()
    print("\n🐠 Buoy Fish Scanner")
    print(f"   Mode           : {'SIMULATION' if args.sim else 'LIVE CAMERA'}")
    print(f"   Fish collected : {stats['total_collected']}")
    print(f"   Rewards earned : {stats['rewards_earned']}")
    print(f"   Next reward in : {stats['next_reward_in']} fish\n")
 
    if args.sim:
        run_simulation(classifier, db)
    else:
        run_camera(classifier, db, args.camera)
 
 
def run_camera(classifier: FishClassifier, db: Database, camera_index: int):
    cap = cv2.VideoCapture(camera_index)
 
    if not cap.isOpened():
        print(f"[Error] Could not open camera {camera_index}.")
        return
 
    print("Scanning... Press 'q' to quit.\n")
    last_saved = 0
 
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Error] Failed to read frame.")
            break
 
        result = classifier.classify(frame)
        cv2.imshow("Buoy Fish Scanner", result["annotated_frame"])
 
        now = time.time()
        if result["is_fish"] and (now - last_saved) > COOLDOWN_SECONDS:
            last_saved = now
            save_result = db.save_fish(frame, result)
            handle_reward(save_result, db)
 
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
 
    cap.release()
    cv2.destroyAllWindows()
    print_stats(db)
 
 
def run_simulation(classifier: FishClassifier, db: Database):
    """Runs 15 fake frames to demo the full pipeline."""
    print("Running simulation (15 frames)...\n")
 
    for i in range(15):
        frame = make_fake_frame()
        result = classifier.classify(frame)
 
        status = f"Frame {i+1:02d}: {'🐟 FISH DETECTED' if result['is_fish'] else '   No fish'}"
        if result["is_fish"]:
            status += f" ({result['confidence']:.0%})"
        print(status)
 
        if result["is_fish"]:
            save_result = db.save_fish(frame, result)
            handle_reward(save_result, db)
 
        time.sleep(0.3)
 
    print_stats(db)
 
 
def handle_reward(save_result: dict, db: Database):
    if save_result.get("reward_triggered"):
        stats = db.get_stats()
        qr_path = generate_qr(
            total_fish=stats["total_collected"],
            rewards_earned=stats["rewards_earned"],
        )
        print(f"   → QR saved: {qr_path}\n")
 
 
def make_fake_frame() -> np.ndarray:
    """Generate a fake ocean-colored frame for simulation."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (
        random.randint(100, 200),  # blue
        random.randint(100, 180),  # green
        random.randint(10, 60),    # red
    )
    return frame
 
 
def print_stats(db: Database):
    stats = db.get_stats()
    print("\n--- Session Complete ---")
    print(f"Total fish collected : {stats['total_collected']}")
    print(f"Rewards earned       : {stats['rewards_earned']}")
    print(f"Next reward in       : {stats['next_reward_in']} fish")
 
 
if __name__ == "__main__":
    main()