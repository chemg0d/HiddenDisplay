# HiddenDisplay

Công cụ hỗ trợ VALORANT — hiển thị máu/xác, xóa logo VNG, tối ưu FPS và đồ họa.

## Tính năng

- **Hiển thị Máu & Xác** — Bật nội dung người lớn (máu, xác chết) mỗi phiên chơi
- **Xóa Logo VNG** — Xóa logo nhà phát hành VNG khi khởi động game
- **Khởi động nhanh** — Khởi động VALORANT qua Riot Client và tự động áp dụng mod trước khi game tải
- **Tối ưu FPS** — Ultimate Performance, tắt hiệu ứng hình ảnh, Game Bar/DVR, Nagle's algorithm, Prefetch/Superfetch, GPU scheduling, và nhiều hơn
- **Giảm đồ họa** — Áp dụng cài đặt đồ họa thấp nhất (720p, tất cả tối thiểu) cho mọi tài khoản
- **Điểm khôi phục** — Tự động tạo System Restore Point trước khi tối ưu

## Yêu cầu

- Windows 10/11
- VALORANT đã cài đặt
- Riot Client đã cài đặt

## Cách sử dụng

### Bước 1: Giải nén
Giải nén file zip vào một thư mục bất kỳ.

### Bước 2: Chạy ứng dụng
Mở `HiddenDisplay.exe` — không cần cài đặt.

### Bước 3: Cài đặt đường dẫn (nếu cần)

Ứng dụng tự động tìm VALORANT và Riot Client. Nếu không tìm thấy:

- **Thư mục game**: Nhấn **Chọn** ở mục **THƯ MỤC GAME** để trỏ đến thư mục VALORANT (ví dụ: `D:\Riot Games\VALORANT`)
- **Riot Client**: Nhấn **Chọn** ở mục **KHỞI ĐỘNG** để trỏ đến file `RiotClientServices.exe` (ví dụ: `D:\Riot Games\Riot Client\RiotClientServices.exe`)

> Chỉ cần làm 1 lần, ứng dụng sẽ lưu lại đường dẫn.

### Bước 4: Chọn mod
Tích chọn **Hiển thị Máu & Xác** và/hoặc **Xóa Logo VNG** tùy theo nhu cầu.

### Bước 5: Khởi động game
Nhấn **CHƠI VALORANT** — ứng dụng sẽ tự động:
1. Tắt Riot Client cũ (nếu đang chạy)
2. Khởi động game qua Riot Client
3. Đợi Riot Client kiểm tra file xong
4. Áp dụng mod ngay khi game bắt đầu chạy

### Lần đầu sử dụng (Máu/Xác)
1. Khởi động game bằng nút **CHƠI VALORANT**
2. Trong game: **Settings > General > Show Mature Content > ON**
3. Tắt game rồi chơi lại
4. Kiểm tra: **Show Blood** và **Show Corpse** đã xuất hiện

> **Quan trọng:** Giữ thư mục `blood/` cùng chỗ với file exe.

## Miễn trách nhiệm

Công cụ này chỉnh sửa file game VALORANT khi chạy. Tác giả không chịu trách nhiệm về bất kỳ hành động nào từ phía Riot Games mặc dù chưa có trường hợp nào ghi nhận bị ban.
