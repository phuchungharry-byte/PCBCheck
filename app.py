import argparse
import threading
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


MODEL_PATH = str(Path(__file__).resolve().with_name("best.pt"))
CONF_THRESHOLD = 0.85

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


class CircuitCameraApp:
    def __init__(self, root, model_path, camera_index, conf, imgsz):
        self.root = root
        self.model_path = Path(model_path)
        self.camera_index = camera_index
        self.conf = conf
        self.imgsz = imgsz
        self.running = False
        self.cap = None
        self.photo = None
        self.model = None
        self.predict_lock = threading.Lock()

        self.root.title("Nhan dien mach PCB")
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
            text="Nhan dien mach PCB",
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

        button_style = ttk.Style()
        button_style.configure("Accent.TButton", font=("Segoe UI", 11))

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

        with self.predict_lock:
            results = self.model.predict(
                source=frame,
                conf=self.conf,
                imgsz=self.imgsz,
                verbose=False,
            )

        result = results[0]
        if result.boxes is not None and len(result.boxes) > 0:
            best_box = max(result.boxes, key=lambda box: float(box.conf[0]))
            class_id = int(best_box.cls[0])
            confidence = float(best_box.conf[0])
            class_name = self.get_class_name(result, class_id)
            label, label_bg, box_color = self.get_display_label(class_id, class_name)
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

        self.status_label.config(text=status_text, bg=label_bg)
        return frame

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
        self.root.destroy()


def parse_args():
    parser = argparse.ArgumentParser(description="GUI camera app for PCB OK/defect detection.")
    parser.add_argument("--model", default=MODEL_PATH, help="Path to trained YOLO model.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index.")
    parser.add_argument("--conf", type=float, default=CONF_THRESHOLD, help="Confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO image size.")
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    CircuitCameraApp(root, args.model, args.camera, args.conf, args.imgsz)
    root.mainloop()


if __name__ == "__main__":
    main()
