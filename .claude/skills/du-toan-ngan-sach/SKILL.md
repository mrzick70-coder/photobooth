---
name: du-toan-ngan-sach
description: Tính dự toán cải tạo theo ngân sách bằng script (không để AI tự cộng). Tự chọn mức giá TK/CB/NB cho từng hạng mục, xuất Excel có công thức và gợi ý cắt giảm khi vượt. Dùng sau bước thiết kế, khi đã có hang-muc.json.
---

# Dự toán theo ngân sách

Mọi phép cộng và kiểm tra ngân sách đều do script làm. Không tự tính tay và không đọc file Excel (tốn token); chỉ đọc phần tóm tắt script in ra.

## Tệp
Các file dưới đây nằm trong **thư mục của skill này** (đường dẫn thật được báo khi skill được nạp):
- `bang-gia-mau.csv`: bảng giá mẫu, gồm 3 mức giá, khu vực, ngày cập nhật và nguồn
- `mau-hang-muc.json`: mẫu đầu vào (photobooth 3×6m). Sao chép file này rồi sửa
- `scripts/du_toan.py`: script tính

Bảng giá dùng thật của repo là `du-an/bang-gia.csv`. Lần chạy đầu, script tự chép nó từ `bang-gia-mau.csv`. Sub agent `khao-gia` bổ sung giá vào file này, nên mỗi repo có bảng giá riêng và giá không mất khi cập nhật skill.

## Định dạng hang-muc.json
Mỗi hạng mục có các trường:
- `ma`: phải trùng với một mã trong bang-gia.csv. Mã mới đặt dạng kebab-case, không dấu
- `nhom`, `khoi_luong`, `ghi_chu`
- `uu_tien`: 1 = lên ảnh / tạo thẩm mỹ nhiều nhất … 5 = không lên ảnh (điện, điều hòa)
- `bat_buoc`: đặt `false` nếu hạng mục có thể bỏ
- `cho_phep_nb`: đặt `true` nếu hạng mục đáng chi lên mức nổi bật
- `muc` (tùy chọn): ép cố định một mức, dùng khi người dùng đã chốt

## Chạy
```bash
python3 <thư-mục-skill>/scripts/du_toan.py du-an/<ten-du-an>
```
(Cần `openpyxl`; nếu thiếu thì chạy `pip install openpyxl`.)

| Mã thoát | Ý nghĩa | Việc tiếp theo |
|---|---|---|
| 0 | ĐẠT | Báo tổng, mức chọn và đường dẫn du-toan.xlsx cho người dùng duyệt |
| 1 | VƯỢT | Script in danh sách ứng viên cắt/thay. Đề xuất 2–3 phương án cho người dùng chọn, sửa hang-muc.json rồi chạy lại. **Tối đa 2 vòng**; sau 2 vòng mà vẫn vượt thì trình bày thẳng các đánh đổi để người dùng quyết |
| 2 | THIẾU GIÁ | Gọi sub agent `khao-gia`, **chỉ gửi các mã còn thiếu** kèm quy cách, rồi chạy lại |

Script cũng cảnh báo khi giá cũ hơn 120 ngày. Khi đó hỏi người dùng có muốn khảo giá lại không.

## Thuật toán chọn mức
Bắt đầu từ mức TK cho các hạng mục bắt buộc. Sau đó thêm hạng mục tùy chọn, rồi nâng lên CB, rồi NB (chỉ với hạng mục `cho_phep_nb`), theo thứ tự `uu_tien`, miễn là tổng (kể cả dự phòng) vẫn nằm trong ngân sách. Nhờ vậy tiền được dồn vào những thứ lên ảnh.
