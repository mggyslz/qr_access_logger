# apps/scanner_app.py
import cv2
from pyzbar import pyzbar
import threading
import time
import tkinter as tk

from core.database import get_user_by_qr, log_access, last_action_for_user
from core.error_utils import log_error
from core.security import verify_pin
from core.gui_utils import PinPad, show_feedback
from config.settings import CAMERA_INDEX

seen_tokens = {}

def process_token(qr_data):
    user = get_user_by_qr(qr_data)
    if not user:
        print("[DENIED] Unknown QR code.")
        root = tk.Tk(); root.withdraw()
        show_feedback(False, "Unknown User")
        root.destroy()
        return

    user_id, name, role, pin_hash, pin_salt, status = user
    if status != "Active":
        root = tk.Tk(); root.withdraw()
        show_feedback(False, f"{name} (Inactive)")
        root.destroy()
        return

    last = last_action_for_user(user_id)

    if last == "IN":
        log_access(user_id, "OUT")
        root = tk.Tk(); root.withdraw()
        show_feedback(True, name)
        root.destroy()
        print(f"[OUT] {name} logged OUT")
        return

    # Otherwise, need PIN for IN
    root = tk.Tk()
    root.withdraw()
    pad = PinPad(name)
    root.wait_window(pad)
    entered_pin = pad.result
    root.destroy()

    if entered_pin is None:
        print(f"[CANCELLED] {name}")
        return

    if verify_pin(entered_pin, pin_salt, pin_hash):
        log_access(user_id, "IN")
        print(f"[IN] {name} logged IN")
        root = tk.Tk(); root.withdraw()
        show_feedback(True, name)
        root.destroy()
    else:
        print(f"[DENIED] Incorrect PIN for {name}")
        root = tk.Tk(); root.withdraw()
        show_feedback(False, name)
        root.destroy()

def scanner_loop():
    try:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            print("Cannot open camera.")
            return
    except Exception as e:
        log_error(e, "Opening camera")
        return

    print("Scanner ready. Press 'q' to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            barcodes = pyzbar.decode(frame)
            for barcode in barcodes:
                qr_data = barcode.data.decode("utf-8")
                x, y, w, h = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, qr_data[:16], (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                now = time.time()
                if qr_data not in seen_tokens or (now - seen_tokens[qr_data]) > 2:
                    seen_tokens[qr_data] = now
                    threading.Thread(target=process_token, args=(qr_data,), daemon=True).start()

            cv2.imshow("QR Access Logger - Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        log_error(e, "Scanner loop crash")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        
if __name__ == "__main__":
    scanner_loop()
