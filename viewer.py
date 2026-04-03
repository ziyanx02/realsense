import cv2
import numpy as np
import time
from realsense_shm_sub import CamReader

reader = CamReader()
serials = reader.serials
print(f"Found cameras: {serials}")

prev_times = {s: time.perf_counter() for s in serials}
fps_values = {s: 0.0 for s in serials}
window_created = False

TARGET_FPS = 50
FRAME_INTERVAL = 1.0 / TARGET_FPS
next_frame_time = time.perf_counter()

while True:
    now = time.perf_counter()
    sleep_time = next_frame_time - now
    if sleep_time > 0:
        time.sleep(sleep_time)
    next_frame_time += FRAME_INTERVAL
    imgs = reader.get_latest(serials)

    frames_to_show = []
    for i, img in enumerate(imgs):
        if img is None:
            continue

        image_bgr = img[:, :, ::-1].copy()  # RGB -> BGR
        h, w = image_bgr.shape[:2]
        center_x, center_y = w // 2, h // 2
        cv2.line(image_bgr, (center_x, 0), (center_x, h - 1), (0, 255, 0), 1)
        cv2.line(image_bgr, (0, center_y), (w - 1, center_y), (0, 255, 0), 1)

        serial = serials[i]
        current_time = time.perf_counter()
        dt = current_time - prev_times[serial]
        prev_times[serial] = current_time
        if dt > 0:
            instant_fps = 1.0 / dt
            fps_values[serial] = (
                instant_fps
                if fps_values[serial] == 0.0
                else 0.9 * fps_values[serial] + 0.1 * instant_fps
            )

        cv2.putText(
            image_bgr,
            f"{serial} | FPS: {fps_values[serial]:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        frames_to_show.append(image_bgr)

    if len(frames_to_show) == 2:
        combined = np.hstack(frames_to_show)
        cv2.imshow("RealSense x2 (shm)", combined)
        window_created = True

    if window_created:
        key = cv2.waitKey(1)
        if key == 27 or cv2.getWindowProperty("RealSense x2 (shm)", cv2.WND_PROP_VISIBLE) < 1:
            break

cv2.destroyAllWindows()
