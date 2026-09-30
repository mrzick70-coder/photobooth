# Photobooth Sky Cinema – dựng phòng bằng Blender

Đây là bộ file dựng phòng photobooth 6 × 3 m (buồng chụp 2 × 1,5 m) theo concept **Sky Cinema** (xanh trời, vàng bơ, nhôm bạc).

## Cách xem hình
- `renders\draft\` – ảnh **nháp** (nhanh, chỉ để duyệt bố cục, màu sắc chưa chuẩn).
- `renders\final\` – ảnh **đẹp** (có ánh sáng và bóng đổ thật, gương phản chiếu).

Các ảnh:
| File | Nội dung |
|---|---|
| 01a / 01b / 01c | Góc máy ảnh nhìn ra rèm phông: xanh trời / xanh đậm / trắng ngà |
| 02 | Toàn cảnh sảnh |
| 03 | Nhìn từ cửa ra vào (tường trái) |
| 04 | Mặt tiền buồng chụp |
| 05 | Mặt bằng, có nhãn A–F và số đo |
| 06 | Góc nhìn của khách ngồi trong buồng |
| 07 | Mặt bằng bố trí đèn, có độ rọi (lux) ước tính (xem `docs\thiet-ke-chieu-sang.md`) |
| 08 | Nhìn thẳng tường trong cùng: sofa, tranh, kệ, gương |

## Cách render lại (không cần gõ lệnh)
- Bấm đúp **`ve-nhap.bat`** → render ảnh nháp.
- Bấm đúp **`ve-dep.bat`** → render ảnh đẹp (mất vài phút).
Hoặc nhờ Claude: "sửa X rồi render lại nháp".

## Đổi phong cách
Trong `thong-so.json`, dòng `"y_tuong"`: `"sky"` (xanh trời) hoặc `"barbie"` (hồng). Ảnh Barbie nằm ở `rendersinal_barbie`, ảnh Sky ở `rendersinal`.

## Tự chỉnh số liệu (không cần Claude)
Mở **`thong-so.json`** bằng Notepad, sửa số (kích thước phòng, vị trí giá đạo cụ/bàn gương/sofa/quầy, chiều cao bàn, mã màu, vị trí đèn…) rồi lưu và bấm `ve-nhap.bat`. Nếu lỡ sửa sai cú pháp, chương trình báo lỗi và dùng số mặc định. Đổi chiều dài/rộng của buồng chụp thì nhờ Claude chỉnh thêm cửa.

## Xem cảnh 3D
Mở `Photobooth_Cinema.blend` bằng Blender 5.2 rồi xoay quanh phòng. Mỗi khu có tên riêng: `A_` sảnh chờ, `B_` giá đạo cụ, `C_` quầy vé, `D_` bàn gương, `F_Rem_` rèm phông, `Booth_` buồng chụp.

## Có gì trong thư mục
| Thư mục / file | Ý nghĩa |
|---|---|
| `scripts\build_scene.py` | "Công thức" dựng phòng – sửa bố cục ở đây (thường nhờ Claude sửa) |
| `scripts\render.py` | Chạy render nháp/đẹp |
| `scripts\extract_design.py` | Đọc chữ từ file HTML thiết kế |
| `scripts\archive\` | Các bản cũ (vintage, bê tông, 8×5 m…) để quay lại khi cần |
| `assetsarbie\` | 3 ảnh minh hoạ trong khung tranh (phong cách Barbie). Muốn dùng ảnh khác: thay file cùng tên, tỉ lệ dọc ~2:3 |
| `docs\` | Chữ trích từ các file thiết kế + nhật ký quyết định |
| `CLAUDE.md` | Ghi nhớ dự án cho Claude ở các lần làm việc sau |
