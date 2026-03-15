import os, uuid, qrcode
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QR_DIR = os.path.join(BASE_DIR, "data", "rewards")

def generate_qr(total_fish, rewards_earned):
    os.makedirs(QR_DIR, exist_ok=True)
    token = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = "BUOY_REWARD|token=" + token + "|fish=" + str(total_fish) + "|reward_no=" + str(rewards_earned) + "|ts=" + timestamp
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    filename = "reward_" + str(rewards_earned) + "_" + timestamp + ".png"
    filepath = os.path.join(QR_DIR, filename)
    img.save(filepath)
    print("[Rewards] QR #" + str(rewards_earned) + " generated -> " + filepath)
    print("[Rewards] Token: " + token)
    return filepath