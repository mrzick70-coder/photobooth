---
name: photobooth-du-an
description: Quy trình trọn gói lập kế hoạch cải tạo photobooth, từ hạng mục, thiết kế aesthetic đến dự toán vừa ngân sách, có người dùng duyệt ở từng mốc. Dùng khi người dùng gõ /photobooth-du-an hoặc muốn lên phương án cải tạo/thiết kế/dự toán cho một photobooth hay studio nhỏ.
---

# Quy trình dự án photobooth

Agent chính chạy toàn bộ quy trình. Chỉ gọi sub agent `khao-gia` khi thiếu giá. Mỗi dự án lưu trong `du-an/<ten-khong-dau>/`.

## Bước 0: Thu thập đầu vào (hỏi một lần, gộp các câu hỏi)
Làm theo mục 1 của skill `photobooth-checklist`: diện tích, chiều cao, tình trạng mặt bằng, vách ngăn, ngân sách và ngân sách đó có gồm thiết bị không, khu vực, phong cách và ảnh tham khảo. Câu nào người dùng đã trả lời thì không hỏi lại.

## Bước 1: Hạng mục
Đọc skill `photobooth-checklist`, chọn các hạng mục áp dụng cho mặt bằng này. Không liệt kê lại toàn bộ checklist cho người dùng.

## Bước 2: Thiết kế
Dùng skill `interior-design-expert` (nếu có) để thiết kế theo phong cách và ảnh tham khảo. Ghi `du-an/<ten>/thiet-ke.md`, **tối đa khoảng 1 trang**, gồm:
- Sơ đồ mặt bằng dạng ASCII, có phân khu và kích thước (khu chụp: máy ảnh cách khách ≥ 2m, khách cách phông ≥ 0,8m; lối đi ≥ 0,9m)
- Bảng màu 60-30-10, vật liệu, 3 lớp chiếu sáng (cùng nhiệt màu)
- Những thứ "lên ảnh", nơi nên dồn tiền

**Mốc duyệt 1:** tóm tắt concept cho người dùng trong 5–7 dòng và chờ đồng ý trước khi sang bước 3. Nếu người dùng muốn sửa thì chỉ sửa phần họ nêu.

## Bước 3: Danh sách vật tư
Sao chép `mau-hang-muc.json` trong thư mục skill `du-toan-ngan-sach` sang `du-an/<ten>/hang-muc.json` rồi sửa theo thiết kế: khối lượng tính từ kích thước thật, `uu_tien` theo mức độ lên ảnh, `bat_buoc`, `cho_phep_nb`. Ưu tiên dùng lại các `ma` đã có trong `du-an/bang-gia.csv` (nếu chưa có file này thì xem `bang-gia-mau.csv` của skill `du-toan-ngan-sach`).

## Bước 4: Dự toán
Làm theo skill `du-toan-ngan-sach`: chạy script và xử lý mã thoát (thiếu giá thì gọi `khao-gia` chỉ cho các mã thiếu; vượt ngân sách thì tối đa 2 vòng đề xuất cắt/thay).

Khi vượt ngân sách, ưu tiên các cách giữ thẩm mỹ:
- Bỏ hoặc thay hạng mục không lên ảnh (cửa thay bằng rèm, quầy thay bằng kệ)
- Một món làm hai việc (sofa vừa là ghế chờ vừa là đạo cụ chụp)
- Hoãn những thứ làm sau được (biển tên, đạo cụ phụ)

Hạng mục an toàn (điện) không được hạ dưới mức TK.

**Mốc duyệt 2:** báo tổng tiền, các mục đã cắt hoặc thay và lý do, đường dẫn `du-toan.xlsx`. Nhắc người dùng lấy 2–3 báo giá thợ địa phương, vì giá nhân công AI ước lượng chỉ mang tính tham khảo.

## Tiết kiệm token
- Không đọc file .xlsx; chỉ đọc phần tóm tắt script in ra
- Không dán lại toàn bộ thiet-ke.md hay bảng giá vào chat; chỉ đưa đường dẫn và phần tóm tắt
- Sub agent chỉ nhận danh sách mã cần khảo, không nhận bối cảnh cả dự án
