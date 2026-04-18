# HiddenDisplay

Công cụ hỗ trợ VALORANT cho Windows: inject mod máu, xóa logo VNG, True Stretch (kéo giãn độ phân giải tùy chỉnh), tối ưu FPS và preset đồ họa thấp.

---

## 1. Tính năng chính

- **Mod Máu (Blood Mod)** — copy `MatureData-WindowsClient.*` vào thư mục Paks để bật Show Mature Content trên VALORANT VNG.
- **Xóa Logo VNG** — xóa `VNGLogo-WindowsClient.*` khi khởi động game, tự khôi phục khi game đóng (chống ban).
- **True Stretch** — preset 4:3 (1440x1080, 1280x960, 1024x768) hoặc custom, đặt NVIDIA scaling = Full-screen, đổi độ phân giải desktop, chỉnh config game.
- **Tối ưu FPS** — registry tweak (Ultimate Performance, tắt Game Bar, Nagle, Prefetch…), tạo Restore Point trước khi áp dụng.
- **Preset đồ họa thấp** — ghi đè `GameUserSettings.ini` bằng preset chất lượng thấp.
- **Chế độ Tray** — đóng cửa sổ = ẩn xuống tray, đảm bảo auto-revert chạy khi game thoát.

---

## 2. Luồng hoạt động (tóm tắt)

Khi click **Play VALORANT**:

1. Lưu trạng thái checkbox mod vào `config.json`.
2. Tự áp dụng lại stretch nếu trước đó đã bật.
3. Tìm và khởi động Riot Client (`--launch-product=valorant --launch-patchline=live`).
4. Đợi Riot Client API sẵn sàng, đọc `lockfile`, POST tới `/product-launcher/v1/products/valorant/patchlines/live` để bấm Play.
5. Đợi process `VALORANT-Win64-Shipping.exe` xuất hiện.
6. Inject mod máu / xóa VNG logo (backup bản gốc vào `.originals_backup`).
7. Spawn watcher thread: đợi game thoát → khôi phục VNG logo, khôi phục độ phân giải desktop.

Chi tiết đầy đủ: xem `docs/PROJECT_FLOW_VI.txt`.

---

## 3. Yêu cầu

- Windows 10 / 11
- Python 3.11+ (nếu chạy từ source)
- Quyền Administrator (app tự xin UAC khi chạy)
- NVIDIA GPU (cho True Stretch — scaling qua registry NVIDIA)

---

## 4. Chạy từ source

```bash
# Clone repo
git clone <repo-url>
cd HiddenDisplay

# Cài dependency
pip install customtkinter pystray Pillow psutil pywin32 pycaw comtypes darkdetect requests

# Chạy
python main.py
```

App sẽ tự xin quyền Administrator khi khởi động.

---

## 5. Build `.exe`

Dùng PyInstaller với file spec có sẵn:

```bash
# Cài PyInstaller
pip install pyinstaller

# Kill exe cũ nếu đang chạy
taskkill /F /IM HiddenDisplay.exe 2>nul

# Build
pyinstaller build.spec --clean --noconfirm
```

Kết quả: `dist/HiddenDisplay.exe` (single-file, khoảng 23 MB).

**Lưu ý:**
- Thư mục `bin/` và `blood/` được bundle vào exe qua `datas` trong `build.spec`.
- `config.json` được tạo tự động cạnh exe ở lần chạy đầu.
- Nếu thêm package mới, thêm vào `hiddenimports` trong `build.spec`.

---

## 6. Cấu trúc thư mục

```
HiddenDisplay/
├── main.py                  Entry point (xin UAC, khởi động MainWindow)
├── build.spec               PyInstaller config
├── bin/                     Icon, asset
├── blood/                   File pak mod máu
│   ├── MatureData-WindowsClient.pak
│   ├── MatureData-WindowsClient.sig
│   ├── MatureData-WindowsClient.ucas
│   └── MatureData-WindowsClient.utoc
├── src/
│   ├── config.py            Đọc/ghi config.json
│   ├── main_window.py       UI chính (CustomTkinter) + tray
│   ├── game_launcher.py     Khởi động Riot Client + inject mod
│   ├── stretch.py           True Stretch (registry + Win32 API)
│   ├── fps_optimizer.py     Tối ưu FPS (registry tweak)
│   └── graphics_preset.py   Preset đồ họa thấp
├── docs/
│   ├── PROJECT_FLOW_EN.txt  Tài liệu flow (English)
│   └── PROJECT_FLOW_VI.txt  Tài liệu flow (Tiếng Việt)
└── dist/HiddenDisplay.exe   Output sau build
```

---

## 7. `config.json`

File tạo tự động cạnh `HiddenDisplay.exe`:

```json
{
  "game_path": "",
  "riot_client_path": "",
  "enable_blood": true,
  "enable_vng_remove": true,
  "minimize_to_tray": true,
  "language": "en",
  "custom_width": "",
  "custom_height": "",
  "last_resolution": ""
}
```

---

## 8. Rủi ro ban

| Tính năng | Mức rủi ro | Ghi chú |
|-----------|------------|---------|
| Mod máu (VNG user) | Rất thấp | File thêm vào, Vanguard không ban "file dư" |
| Mod máu (non-VNG) | Rất thấp | Gốc được khôi phục khi game thoát |
| Xóa VNG logo | Thấp | Có cửa sổ scan nhỏ, rủi ro nếu HD crash giữa session |
| True Stretch | Không | Chỉ chỉnh file user, không đụng file game |

Giảm thiểu: emergency cleanup khi HD đóng, daemon thread tự thoát sạch, backup trước khi sửa.

---

## 9. Ghi chú

- **Đừng force-kill HD giữa game** — sẽ bỏ qua cleanup watcher. Dùng nút Quit ở tray menu thay vì Task Manager.
- **True Stretch yêu cầu NVIDIA GPU** — AMD/Intel chưa được hỗ trợ (registry scaling khác).
- **Độ phân giải không có trong NVIDIA CP** — app sẽ mở NVIDIA Control Panel kèm popup hướng dẫn 9 bước tạo custom resolution.
