# PCB Check

Ứng dụng kiểm tra PCB bằng camera và mô hình YOLO. Dự án có hai chế độ:

- `app.py`: nhận diện PCB lỗi/không lỗi bằng camera.
- `dobot_pcb_sorter.py`: nhận diện và điều khiển Dobot Magician Lite để phân loại PCB vào hai khay.

Mô hình đã huấn luyện nằm trong `best.pt`.

## Yêu cầu

- Python 3.10–3.12
- Camera tương thích OpenCV
- Với chế độ robot: Dobot Magician Lite, DobotLab và môi trường có thư viện `DobotEDU`

## Cài đặt

```powershell
git clone https://github.com/phuchungharry-byte/PCBcheck.git
cd PCBcheck
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Chạy nhận diện bằng camera

```powershell
python app.py
```

Nếu camera mặc định không đúng, đổi camera index:

```powershell
python app.py --camera 1
```

Ví dụ truyền đầy đủ tham số:

```powershell
python app.py --model best.pt --camera 0 --conf 0.85 --imgsz 640
```

## Chạy bộ phân loại với Dobot

Chạy file sau trong môi trường DobotLab đã kết nối robot:

```powershell
python dobot_pcb_sorter.py
```

Chỉ thử phần camera/nhận diện, không điều khiển robot:

```powershell
python dobot_pcb_sorter.py --no-robot
```

## Tham số dòng lệnh

| Tham số | Mặc định | Ý nghĩa |
| --- | ---: | --- |
| `--model` | `best.pt` | Đường dẫn đến mô hình YOLO |
| `--camera` | `0` | Camera index |
| `--conf` | `0.85` | Ngưỡng độ tin cậy |
| `--imgsz` | `640` | Kích thước ảnh đưa vào YOLO |

Ngưỡng `conf` cao giúp giảm báo nhầm nhưng có thể bỏ sót lỗi. Các tọa độ robot trong `dobot_pcb_sorter.py` cần được hiệu chỉnh theo vị trí lắp đặt thực tế trước khi chạy tự động.

## Cấu trúc dự án

```text
PCBcheck/
├── app.py                 # GUI nhận diện bằng camera
├── dobot_pcb_sorter.py    # Nhận diện và phân loại bằng Dobot
├── best.pt                # Trọng số mô hình YOLO
├── requirements.txt       # Thư viện Python
└── README.md              # Hướng dẫn sử dụng
```
