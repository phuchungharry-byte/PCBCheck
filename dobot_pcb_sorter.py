import argparse
import asyncio
import inspect
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    import cv2
    from PIL import Image, ImageTk
    from ultralytics import YOLO
except ModuleNotFoundError as exc:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Thieu thu vien",
        f"Python dang thieu thu vien: {exc.name}\n\n"
        "Cai dat bang lenh:\n"
        "pip install -r requirements.txt",
    )
    root.destroy()
    raise SystemExit(1) from exc

try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.LANCZOS

try:
    from DobotEDU import *  # noqa: F403

    DOBOT_AVAILABLE = True
except ModuleNotFoundError:
    DOBOT_AVAILABLE = False

try:
    m_lite  # noqa: B018,F405
except NameError:
    m_lite = None


MODEL_PATH = str(Path(__file__).resolve().with_name("best.pt"))
CAMERA_INDEX = 0
CONF_THRESHOLD = 0.85
OBSERVE_SECONDS = 5.0
MOVE_DELAY_SECONDS = 1.0
SUCTION_HOLD_SECONDS = 0.5

OBSERVATION_POSE = {"x": 239.4, "y": 0, "z": 150.1, "r": 0}
PICK_POSE = {"x": 280, "y": 0, "z": 63.5, "r": 0}
TRANSFER_AFTER_PICK_POSE = {"x": 218.55, "y": -1, "z": 109.16, "r": 0}
RETURN_STEP_1_POSE = {"x": 143.62, "y": 165.11, "z": 89.45, "r": 0}
RETURN_STEP_2_POSE = {"x": 218.76, "y": 5.56, "z": 88.9, "r": 0}

KHAY_LOI_POSE = {"x": 49.6, "y": 281.63, "z": -14.77, "r": 0}
KHAY_KHONG_LOI_POSE = {"x": -40.73, "y": 292.14, "z": -2.95, "r": 0}

R_PICK = 0
R_PLACE = 0


def run_dobot_command(command_result):
    if not inspect.isawaitable(command_result):
        return command_result

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(command_result, loop).result()

    return loop.run_until_complete(command_result)

CLASS_TEXT = {
    "error": ("LOI", "#d92d20", (0, 0, 255)),
    "defect": ("LOI", "#d92d20", (0, 0, 255)),
    "ng": ("LOI", "#d92d20", (0, 0, 255)),
    "bad": ("LOI", "#d92d20", (0, 0, 255)),
    "done": ("KHONG LOI", "#079455", (0, 180, 0)),
    "ok": ("KHONG LOI", "#079455", (0, 180, 0)),
    "good": ("KHONG LOI", "#079455", (0, 180, 0)),
    "normal": ("KHONG LOI", "#079455", (0, 180, 0)),
    "pass": ("KHONG LOI", "#079455", (0, 180, 0)),
    0: ("LOI", "#d92d20", (0, 0, 255)),
    1: ("KHONG LOI", "#079455", (0, 180, 0)),
}


class DobotSorter:
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.lock = threading.Lock()
        self.busy = False

    def log(self, text):
        self.log_callback(text)

    def get_robot(self):
        return m_lite  # noqa: F405

    def is_ready(self):
        return self.get_robot() is not None

    def go_observation(self):
        robot = self.get_robot()
        if robot is None:
            raise RuntimeError("Dobot chua ket noi: m_lite is None.")
        run_dobot_command(
            robot.set_ptpcmd(
                ptp_mode=1,
                x=OBSERVATION_POSE["x"],
                y=OBSERVATION_POSE["y"],
                z=OBSERVATION_POSE["z"],
                r=OBSERVATION_POSE["r"],
            )
        )

    def move_pose(self, pose, r_value=None):
        robot = self.get_robot()
        run_dobot_command(
            robot.set_ptpcmd(
                ptp_mode=1,
                x=pose["x"],
                y=pose["y"],
                z=pose["z"],
                r=pose.get("r", 0) if r_value is None else r_value,
            )
        )
        time.sleep(MOVE_DELAY_SECONDS)

    def suction(self, on):
        robot = self.get_robot()
        run_dobot_command(robot.set_endeffector_suctioncup(enable=True, on=on))

    def sort_async(self, label):
        if self.busy:
            return False
        if m_lite is None:  # noqa: F405
            self.log("Da nhan dien nhung robot chua san sang: m_lite is None.")
            print("!!! Robot chua san sang: m_lite is None.")
            return False

        print(f">>> BAT DAU GAP: {label}")
        self.busy = True
        self.sort(label)
        return True

    def sort(self, label):
        with self.lock:
            try:
                self._sort(label)
            except Exception as exc:
                self.log(f"Loi robot: {exc}")
            finally:
                self.busy = False

    def _sort(self, label):
        if not self.is_ready():
            raise RuntimeError("Robot chua ket noi: m_lite is None.")

        target_pose = KHAY_LOI_POSE if label == "LOI" else KHAY_KHONG_LOI_POSE
        if target_pose is None:
            raise RuntimeError("Chua dien toa do KHAY_LOI_POSE va KHAY_KHONG_LOI_POSE.")

        safe_z = OBSERVATION_POSE["z"]
        pick_above = {**PICK_POSE, "z": safe_z}
        place_above = {**target_pose, "z": safe_z}

        self.log(f"Dobot: gap mach {label}")

        print(f">>> Di len tren vi tri gap: {pick_above}")
        self.move_pose(pick_above, R_PICK)

        print(f">>> Di xuong PICK_POSE de gap: {PICK_POSE}")
        self.move_pose(PICK_POSE, R_PICK)

        print(">>> Bat hut tai PICK_POSE")
        self.suction(True)
        time.sleep(SUCTION_HOLD_SECONDS)

        print(">>> Nhac mach len")
        self.move_pose(pick_above, R_PICK)

        print(f">>> Di qua vi tri trung gian sau khi gap: {TRANSFER_AFTER_PICK_POSE}")
        self.move_pose(TRANSFER_AFTER_PICK_POSE)

        print(f">>> Di len tren khay dich: {place_above}")
        self.move_pose(place_above, R_PLACE)

        print(f">>> Ha xuong khay dich: {target_pose}")
        self.move_pose(target_pose, R_PLACE)

        print(">>> Tat hut")
        self.suction(False)
        time.sleep(SUCTION_HOLD_SECONDS)

        print(">>> Nhac len khoi khay")
        self.move_pose(place_above, R_PLACE)

        print(f">>> Di qua vi tri sau khi tha 1: {RETURN_STEP_1_POSE}")
        self.move_pose(RETURN_STEP_1_POSE)

        print(f">>> Di qua vi tri sau khi tha 2: {RETURN_STEP_2_POSE}")
        self.move_pose(RETURN_STEP_2_POSE)

        print(f">>> Ve vi tri nhin mach: {OBSERVATION_POSE}")
        self.go_observation()
        self.log("Dobot: da gap xong va ve toa do goc")

    def test_pick_sequence_only(self):
        if not self.is_ready():
            raise RuntimeError("Robot chua ket noi: m_lite is None.")

        safe_z = OBSERVATION_POSE["z"]
        pick_above = {**PICK_POSE, "z": safe_z}

        self.go_observation()
        time.sleep(OBSERVE_SECONDS)
        self.move_pose(pick_above, R_PICK)
        self.move_pose(PICK_POSE, R_PICK)
        self.suction(True)
        time.sleep(0.5)
        self.move_pose(pick_above, R_PICK)
        self.go_observation()
        self.suction(False)
        self.log("Dobot: test gap va ve goc xong")


class PcbSorterApp:
    def __init__(self, root, model_path, camera_index, conf, imgsz, auto_robot):
        self.root = root
        self.model_path = Path(model_path)
        self.camera_index = camera_index
        self.conf = conf
        self.imgsz = imgsz
        self.auto_robot = auto_robot
        self.running = False
        self.cap = None
        self.photo = None
        self.model = None
        self.predict_lock = threading.Lock()
        self.sorter = DobotSorter(self.set_info)
        self.current_label = None
        self.current_label_started_at = None
        self.last_robot_label = None

        self.root.title("Dobot PCB Sorter")
        self.root.geometry("980x720")
        self.root.minsize(760, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()
        self.load_model()

    def build_ui(self):
        self.root.configure(bg="#101418")

        header = tk.Frame(self.root, bg="#101418")
        header.pack(fill="x", padx=16, pady=(14, 8))

        title = tk.Label(
            header,
            text="Dobot PCB Sorter",
            bg="#101418",
            fg="#f4f4f5",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(side="left")

        self.status_label = tk.Label(
            header,
            text="SAN SANG",
            bg="#344054",
            fg="#ffffff",
            font=("Segoe UI", 18, "bold"),
            width=16,
            padx=12,
            pady=8,
        )
        self.status_label.pack(side="right")

        self.camera_label = tk.Label(self.root, bg="#000000")
        self.camera_label.pack(fill="both", expand=True, padx=16, pady=8)

        footer = tk.Frame(self.root, bg="#101418")
        footer.pack(fill="x", padx=16, pady=(8, 16))

        self.info_label = tk.Label(
            footer,
            text="Camera dang dung",
            bg="#101418",
            fg="#d0d5dd",
            font=("Segoe UI", 11),
        )
        self.info_label.pack(side="left")

        ttk.Style().configure("Accent.TButton", font=("Segoe UI", 11))

        self.start_button = ttk.Button(
            footer,
            text="Bat camera",
            style="Accent.TButton",
            command=self.start_camera,
        )
        self.start_button.pack(side="right", padx=(8, 0))

        self.stop_button = ttk.Button(
            footer,
            text="Dung",
            command=self.stop_camera,
            state="disabled",
        )
        self.stop_button.pack(side="right")

    def set_info(self, text):
        self.root.after(0, lambda: self.info_label.config(text=text))

    def load_model(self):
        if not self.model_path.exists():
            messagebox.showerror("Khong thay model", f"Khong tim thay model:\n{self.model_path}")
            self.root.destroy()
            return

        try:
            self.model = YOLO(str(self.model_path))
            self.info_label.config(text=f"Da load model: {self.model_path}")
        except Exception as exc:
            messagebox.showerror("Loi model", str(exc))
            self.root.destroy()

    def start_camera(self):
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0
        self.cap = cv2.VideoCapture(self.camera_index, backend)
        if not self.cap.isOpened():
            messagebox.showerror("Loi camera", f"Khong mo duoc camera {self.camera_index}")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if self.auto_robot and self.sorter.is_ready():
            try:
                self.sorter.go_observation()
            except Exception as exc:
                self.info_label.config(text=f"Khong dua robot ve goc duoc: {exc}")

        self.running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.info_label.config(text="Camera dang chay")
        self.update_frame()

    def stop_camera(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="DA DUNG", bg="#344054")
        self.info_label.config(text="Camera dang dung")

    def update_frame(self):
        if not self.running or self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.info_label.config(text="Khong doc duoc hinh tu camera")
            self.root.after(30, self.update_frame)
            return

        display_frame = self.detect_and_draw(frame)
        self.show_frame(display_frame)
        self.root.after(10, self.update_frame)

    def detect_and_draw(self, frame):
        status_text = "KHONG PHAT HIEN"
        label_bg = "#f79009"
        box_color = (0, 255, 255)
        detected_label = None

        with self.predict_lock:
            results = self.model.predict(source=frame, conf=self.conf, imgsz=self.imgsz, verbose=False)

        result = results[0]
        if result.boxes is not None and len(result.boxes) > 0:
            best_box = max(result.boxes, key=lambda box: float(box.conf[0]))
            class_id = int(best_box.cls[0])
            confidence = float(best_box.conf[0])
            class_name = self.get_class_name(result, class_id)
            label, label_bg, box_color = self.get_display_label(class_id, class_name)
            detected_label = label
            status_text = f"{label} {confidence:.2f}"

            x1, y1, x2, y2 = [int(v) for v in best_box.xyxy[0]]
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.putText(
                frame,
                status_text,
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                box_color,
                2,
                cv2.LINE_AA,
            )

        self.update_detection_timer(detected_label)
        self.status_label.config(text=status_text, bg=label_bg)
        return frame

    def update_detection_timer(self, detected_label):
        if detected_label is None:
            self.current_label = None
            self.current_label_started_at = None
            return

        now = time.monotonic()
        if detected_label != self.current_label:
            self.current_label = detected_label
            self.current_label_started_at = now
            self.last_robot_label = None
            return

        elapsed = now - self.current_label_started_at
        self.info_label.config(text=f"Nhan dien {detected_label}, dang doi {elapsed:.1f}/{OBSERVE_SECONDS:.1f}s")

        if not self.auto_robot or elapsed < OBSERVE_SECONDS or self.last_robot_label == detected_label:
            return

        if not self.sorter.is_ready():
            self.info_label.config(text=f"Da nhan {detected_label} nhung robot chua san sang: m_lite is None")
            return

        if self.sorter.sort_async(detected_label):
            self.last_robot_label = detected_label

    def get_class_name(self, result, class_id):
        names = getattr(result, "names", None) or getattr(self.model, "names", None) or {}
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, list) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)

    def get_display_label(self, class_id, class_name):
        normalized_name = class_name.strip().lower().replace("-", "_").replace(" ", "_")
        for key, value in CLASS_TEXT.items():
            if isinstance(key, str) and key in normalized_name:
                return value
        return CLASS_TEXT.get(class_id, (class_name.upper(), "#667085", (255, 255, 255)))

    def show_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)

        view_w = max(self.camera_label.winfo_width(), 1)
        view_h = max(self.camera_label.winfo_height(), 1)
        image.thumbnail((view_w, view_h), RESAMPLE_FILTER)

        self.photo = ImageTk.PhotoImage(image=image)
        self.camera_label.config(image=self.photo)

    def on_close(self):
        self.stop_camera()
        robot = self.sorter.get_robot()
        if robot is not None and hasattr(robot, "disconnect"):
            run_dobot_command(robot.disconnect())
        self.root.destroy()


def parse_args():
    parser = argparse.ArgumentParser(description="Dobot PCB sorter with camera detection.")
    parser.add_argument("--model", default=MODEL_PATH, help="Path to trained YOLO model.")
    parser.add_argument("--camera", type=int, default=CAMERA_INDEX, help="Camera index.")
    parser.add_argument("--conf", type=float, default=CONF_THRESHOLD, help="Confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO image size.")
    parser.add_argument("--no-robot", action="store_true", help="Only show camera detection.")
    args, unknown_args = parser.parse_known_args()
    if unknown_args:
        print(f">>> Bo qua tham so DobotLab: {unknown_args}")
    return args


def main():
    args = parse_args()
    root = tk.Tk()
    PcbSorterApp(root, args.model, args.camera, args.conf, args.imgsz, auto_robot=not args.no_robot)
    root.mainloop()


if __name__ == "__main__":
    main()
