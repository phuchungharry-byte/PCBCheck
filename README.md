# PCB Check

PCB Check is a camera-based PCB defect detection application powered by a trained YOLO model. It can run as a standalone inspection tool or integrate with a Dobot Magician Lite to automatically sort defective and non-defective PCBs.

## Features

- Real-time PCB inspection using an OpenCV-compatible camera
- YOLO-based defect detection
- Clear OK/defect status display with confidence scores
- Automatic PCB sorting with a Dobot Magician Lite
- Configurable model path, camera index, confidence threshold, and inference image size
- Camera-only mode for testing without a connected robot

## Project Structure

```text
PCBcheck/
├── app.py                 # Standalone camera inspection GUI
├── dobot_pcb_sorter.py    # Camera inspection and Dobot sorting
├── best.pt                # Trained YOLO model weights
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## Requirements

- Python 3.10–3.12
- An OpenCV-compatible camera
- A Windows, Linux, or macOS environment for camera-only inspection
- Dobot Magician Lite, DobotLab, and the `DobotEDU` library for robot sorting

## Installation

Clone the repository:

```bash
git clone https://github.com/phuchungharry-byte/PCBcheck.git
cd PCBcheck
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Camera Inspection

Start the standalone inspection application:

```bash
python app.py
```

If the default camera is not correct, specify another camera index:

```bash
python app.py --camera 1
```

Example with all commonly used options:

```bash
python app.py --model best.pt --camera 0 --conf 0.85 --imgsz 640
```

## Dobot Sorting

Run the sorter inside a DobotLab environment with the robot connected:

```bash
python dobot_pcb_sorter.py
```

To test the camera and detection workflow without controlling the robot:

```bash
python dobot_pcb_sorter.py --no-robot
```

## Command-Line Options

| Option | Default | Description |
| --- | ---: | --- |
| `--model` | `best.pt` | Path to the trained YOLO model |
| `--camera` | `0` | Camera device index |
| `--conf` | `0.85` | Minimum detection confidence |
| `--imgsz` | `640` | YOLO inference image size |
| `--no-robot` | Disabled | Runs `dobot_pcb_sorter.py` without robot control |

A higher confidence threshold can reduce false positives, but it may also miss some defects.

## Robot Configuration

The following positions are configured in `dobot_pcb_sorter.py`:

- Observation position
- PCB pickup position
- Transfer positions
- Defective PCB tray
- Non-defective PCB tray

These coordinates depend on the physical installation. Carefully recalibrate every position before enabling automatic operation.

## Safety

- Test the complete motion sequence at a reduced speed before normal operation.
- Keep the robot workspace clear during operation.
- Confirm pickup and tray coordinates before enabling the suction cup sequence.
- Use `--no-robot` when testing detection without a connected Dobot.

## Model

The included `best.pt` file contains the trained YOLO weights used by both applications. You can use another compatible model by passing its path through the `--model` option.
