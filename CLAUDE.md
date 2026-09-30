# Photobooth "Sky Cinema" – dựng cảnh 3D bằng Blender

Người dùng không rành kỹ thuật: trả lời tiếng Việt, giải thích đơn giản, đừng bắt họ gõ lệnh (tự chạy giúp).
Luôn render **nháp** để duyệt bố cục trước; chỉ render bản đẹp khi được đồng ý (hoặc khi họ yêu cầu rõ).

## Quy trình làm lại nội thất TỪNG MÓN (người dùng yêu cầu)
Mỗi lần chỉ làm **một món**, xong báo cáo và chờ nhận xét trước khi sang món kế:
1. Ảnh mẫu ở `refs/<mon>/` (kèm `ghi-chu.md`), số đo/màu ở `specs.md`.
2. Mỗi món một file script riêng (`scripts/sofa_togo.py`, …), chạy lặp được (xoá object cũ cùng tên rồi dựng lại), gọi từ `build_scene.py`.
3. Render xem trước: `--only s1,s2,s3` (view `preview=True`, ẩn đồ không liên quan bằng `hide=(...)`, ảnh ra `renders/items/<phong cách>/`).
4. Mở ảnh, so với `refs/`, tự sửa tối đa ~3 vòng, rồi báo điểm còn lệch; món hữu cơ (đệm, vải) chỉ xấp xỉ — nếu cần sát hơn thì import file .glb/.fbx có sẵn.
Thứ tự món: sofa (đã dựng lần 2 = `scripts/sofa_cloud.py`, mẫu bouclé đám mây `refs/sofa/boucle-dam-may-CHINH.webp`; dáng Togo bị bỏ vì quá phức tạp; chờ nhận xét) → giá đạo cụ (đã dựng = `scripts/ke_dao_cu.py`, 5 tầng kệ nổi KHÔNG khung bao (bỏ tấm hông + tấm đỉnh), mép trước lượn sóng, **GIỮ tấm lưng viền sóng** (người dùng chốt để dễ thi công: xưởng làm nguyên khối rồi treo lên tường sẵn có), mẫu `refs/ke_dao_cu/ke-luon-song-CHINH.webp`; chờ nhận xét) → bàn gương + gương → quầy vé → đèn → khung tranh/ghế đẩu/gối → rèm cửa buồng.

## Chạy
Blender 5.2 tại `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`.
```
blender -b -P scripts/render.py -- --mode draft          # Eevee, 50%, ra renders/draft/
blender -b -P scripts/render.py -- --mode final          # Cycles 128 spl + OIDN, cạnh dài 1600 px, ra renders/final/
blender -b -P scripts/render.py -- --mode final --only 02,05 --save-blend
blender -b -P scripts/build_scene.py                     # chỉ dựng + lưu Photobooth_Cinema.blend
```
`--only` nhận id view: 01a 01b 01c (buồng, 3 rèm) 02 (toàn cảnh) 03 (từ lối vào) 04 (mặt tiền buồng) 05 (mặt bằng) 06 (góc nhìn khách) 07 (mặt bằng bố trí đèn + lux) 08 (tường trong cùng); xem trước từng món: s1–s7.
Sửa bố cục = sửa `scripts/build_scene.py` rồi render lại. Trước khi sửa lớn, chép bản cũ vào `scripts/archive/*.bak`.

## Thông số nằm ở `thong-so.json`
Kích thước phòng/buồng, vị trí giá đạo cụ, bàn gương (và chiều cao bàn), sofa, quầy, bảng màu, vị trí/lumen đèn âm trần, cài đặt render đọc từ `thong-so.json` (khoá tiếng Việt không dấu; thiếu/lỗi thì dùng mặc định trong `_load_cfg()` ở build_scene.py). Người dùng sửa số ở đó rồi bấm `ve-nhap.bat`. Khi thêm thông số mới: thêm vào `default` trong `_load_cfg()` VÀ vào thong-so.json.
Giới hạn: cửa rèm/khe ảnh/cửa bảo trì của buồng đặt theo x0 với buồng dài 2,0 m — đổi chiều dài buồng (x1−x0) thì phải chỉnh lại cửa trong `build_booth()`. Vị trí camera, đèn thanh treo/tuýp, tên/kiểu đồ đạc vẫn nằm trong code.

## Toạ độ (quan trọng)
Mét. Số liệu theo brief: X 0→6 (trái→phải nhìn từ lối vào), Y 0 (tường trong cùng)→3 (tường lối vào), Z cao.
Blender tay phải nên **Y_blender = −Y_brief**. Mọi hàm trong `build_scene.py` (`box`, `cyl`, `ell`, `txt`, `light`, `V`…) nhận toạ độ THEO BRIEF và tự đảo Y. Đừng nhập Y đã đảo.
Hướng chữ: `face=(nx, ny)` theo brief, (0,1) = quay về phía lối vào.

## Rèm phông = RÈM CUỐN (kéo lên / kéo xuống)
3 rèm cuốn trơn, ống cuốn ở X = CX0+0,05/0,12/0,19 trong hộp che kem sát trần buồng (`BLIND_TOP` = 2,08). Rèm đang dùng kéo xuống sát sàn có thanh đáy; 2 rèm kia cuộn lên (chỉ lộ thanh đáy dưới hộp che). `set_backdrop()` bật/tắt biến thể spread/bunched.

## Tránh mối ghép chồng góc
Khung tranh dùng `frame_ring()` (một khối liền), quầy chữ L dùng `prism_xy()` (khối chữ L liền). Không ghép nhiều hộp chồng lên nhau ở góc: chỗ chồng + cạnh vát làm góc bị sẫm màu.

## Chất liệu Barbie
Bàn gương và khung gương: sơn bóng hồng `M["lacquer"]` (màu `mau.quay`) + mặt đá trắng `M["marble"]`, KHÔNG dùng chrome (người dùng muốn đồng bộ với quầy). Chrome/nhôm chỉ còn ở khe ảnh, cửa bảo trì.

## Cửa ra vào + quầy – cập nhật MỚI NHẤT
Cửa ra vào ở **tường trái** (X = 0), Y 1,8–2,9 (gần góc với tường trước), cao 2,2 m; Barbie là ô cửa vòm (`_prism_yz`). Tường trước (Y = 3) kín. Hằng số `DOOR_Y0/DOOR_Y1/DOOR_H/DOOR_YC` (từ `phong.cua_vao_*` trong thong-so.json). Quầy vé **chữ L** (`build_C`): cạnh dài X 1,3–2,9 mặt khách Y 1,6; cạnh ngắn phía cửa X 1,3–1,9 chạy tới tường trước; mặt giao dịch 1,10 m + mặt làm việc 0,90 m; chỗ nhân viên 1,0 × 0,8 m. Chữ nổi thương hiệu ở tường trước sau lưng quầy. Đèn tuýp ở tường trái Y 1,3. Trái tim trên cửa buồng KHÔNG có đèn; mọi đèn đặt `visible_glossy = False` để không hiện đốm sáng giả trong gương. View 03 = từ cửa mới; view 08 = nhìn thẳng tường trong cùng (góc 03 cũ).

## Buồng chụp – cập nhật MỚI NHẤT (thay cho mô tả kích thước buồng cũ bên dưới)
Buồng **rộng 1,2 m lọt lòng (ngoài 1,31 m), dài 3,0 m = suốt chiều rộng phòng**, đặt **dọc tường phải, sát góc trong cùng** (X 4,69–6,0; Y 0–3,0), mặt cửa rèm/khe ảnh/cửa bảo trì quay ra sảnh (hướng −X). Dựng trong khung cục bộ (x = dọc mặt cửa, y = lưng→cửa; hằng CX0, PX0, PX1, TX1, CY0, CY1, YC, BX0 là toạ độ CỤC BỘ) rồi `orient_booth()` xoay −90° gắn vào `Booth_Root`; đổi sang toạ độ phòng bằng `TB(x, y, z)`. Khoang chụp lọt lòng 2,0 m dài, khoang kỹ thuật ~0,83 m phía gần lối vào, khách cách ống kính 1,2 m. Bàn gương (X 3,44–4,69) và giá đạo cụ (X 2,04–3,44) xếp sát mặt buồng. Ảnh cabin dùng ống 16 mm (thay 12 mm). Các mô tả buồng 2×1,5 m bên dưới là CŨ.

## Sofa – cập nhật MỚI NHẤT
Có thêm kiểu `sofa_kieu: "bang"` = băng ghế đóng liền tường, lưng 3 vòm, bọc simili, hộc chứa dưới (`scripts/bang_ghe.py`, sâu `bang_do_sau` 0,55 m). Đang cho người dùng so sánh (`renders/items/barbie/so_sanh_ghe/`); mặc định vẫn là "cloud".
Sofa đám mây bouclé 2 chỗ (1,4 × 0,9 m) đặt **áp tường trong cùng** (Y=0), cạnh kệ đạo cụ, tâm X = `sofa_vi_tri_x` (1,0 → X 0,3–1,7), quay mặt ra sảnh (`sofa_tuong: "sau"`; dựng trong khung cục bộ rồi xoay −90° quanh empty `A_Sofa`). Ba khung tranh treo trên tường trong cùng phía trên sofa. Đã BỎ ghế đẩu hồng và chồng gối. Đèn tuýp nghiêng dời ra tường trái giữa (Y 1,6), chữ nổi tên thương hiệu ở tường trái Y 1,5. (Mô tả sofa sát tường trái ở dưới là CŨ.)

## Kích thước đã chốt
- Phòng 6 × 3 m, cao 3,0 m (đã trừ bì). Lối vào tường Y=3, X 2,4–3,5 (rộng 1,1 m), cao 2,2 m.
- Buồng chụp 2,0 × 1,5 m **kích thước ngoài toàn bộ** (gồm khoang kỹ thuật), vách khung + ván 2 mặt dày 55 mm, cao 2,3 m. Đẩy **sát góc phải trong cùng**: X 4,0–6,0, Y 0–1,5 (`BOOTH` trong build_scene.py; các hằng CX0, PX0, PX1, TX1, CY0, CY1, YC, BX0 suy ra từ đó).
  - Khoang chụp lọt lòng ≈ 1,43 × 1,39 m; khoang kỹ thuật sâu 0,40 m (`TECH_D`) ở phía phải; vách ngăn máy ảnh giữa hai khoang.
  - Cửa rèm mặt trước X 4,7–5,48 (rộng ~0,78 m); khe ảnh inox và **cửa bảo trì ở mặt trước** (buồng sát tường phải nên không mở được đầu hồi).
- Hàng sát tường trong cùng, từ trái: giá đạo cụ X 1,35–2,75 (dài 1,4) → bàn gương X 2,75–4,0 (1,25) → buồng. Bàn gương là **bàn đứng** cao 0,95 m, **không ghế**, gương khung nhôm viền bóng đèn tròn 2700K (gương z 1,2–2,2).
- Sofa "đám mây" bouclé 1,4 × 0,9 m (cao lưng 0,78) **áp sát tường trái** (X 0,02–0,92), Y 0,4–1,8 (`sofa_kieu` trong thong-so.json: cloud | thang). Quầy vé 1,25 × 0,45 m, X 1,05–2,3, Y 1,8–2,25, cạnh lối vào; chỗ nhân viên đứng sâu 0,75 m (Y 2,25–3,0) để trống. Kích thước và lý do: `docs/kich-thuoc-noi-that.md`.
- Khu xếp hàng trước buồng Y ≥1,5, để trống.

## CONCEPT HIỆN TẠI: "Kem – Trắng" (`y_tuong: "kem_go"`) – xem `docs/concept-kem-go.md`
Người dùng đổi từ Barbie sang màu cơ bản, dễ mua ở mọi nơi, và muốn dự toán thấp nhất mà vẫn đẹp (~61 tr + 10% dự phòng ≈ 67 tr, trừ thiết bị điện tử). Giữ nguyên bố cục/hình khối Barbie (cờ `IS_BARBIE` giờ = barbie hoặc kem_go); `IS_KEM` đổi vật liệu: vỏ buồng, quầy, bàn gương, khung gương/tranh = melamine **màu trơn** `mau.do_go` (mặc định trắng #F4F2EE) — người dùng KHÔNG chấp nhận vân gỗ, đừng đề xuất lại (`oak_mat()` còn trong code nhưng không dùng); kệ trắng (`mau.ke`); tường kem #EFE9E0; sofa be #D9CBB5; rèm phông trắng/be/taupe; chữ + trái tim + khung tranh đen than; tranh trừu tượng be-nâu-đen `scripts/kem_prints.py` → `assets/kem/`. Người dùng yêu cầu: dù màu gì cũng phải hài hoà tổng thể → theo quy tắc 60-30-10 ghi trong concept-kem-go.md. Ảnh ra `renders/final_kem_go/`. Barbie và Sky vẫn giữ để so sánh.

### Đang cân nhắc: 4 bảng màu TÔNG TRẦM (vợ người dùng thích tông trầm, tối) – xem `docs/moodboard-toi.md`
Khoá `mocha`, `xanh_reu` (gợi ý số 1), `navy`, `dem_than` – cùng hình khối kem_go (nằm trong `PLAIN_CONCEPTS`, cờ `DARK_CONCEPTS` cho exposure 0). Mới render 3 góc 03/08/04 mỗi bảng; đã gửi trang so sánh https://claude.ai/artifact/Krr29BwXrem7WNzacFnxcu. Chờ người dùng chọn → đặt `y_tuong`, render đủ bộ final, cập nhật dự toán. `thong-so.json` hiện vẫn `kem_go`.

## Phong cách chọn trong `thong-so.json` (`y_tuong`)
`"sky"` = Sky Cinema (V3, dưới đây); `"barbie"` = Barbie aesthetic (hồng pastel, chrome, ô cửa vòm, gương tròn viền bóng đèn, đèn cầu, phào chỉ, trái tim vàng-hồng, ghế đẩu hồng "chân dày"). Palette mỗi phong cách ở `mau_theo_y_tuong`; các nhánh hình học riêng dùng cờ `IS_BARBIE` trong build_scene.py. Ảnh phong cách khác sky ghi vào `renders/final_<tên>` / `draft_<tên>` (không đè ảnh Sky). Barbie: đèn âm trần 6000K (Blender 4000K + tường hồng ra cam), exposure −0,6 cho ảnh sảnh. 3 khung tranh trên tường sau sofa (Barbie) dán ảnh người dùng gửi `assets/barbie/tranh-1..3.*` (trái→phải nhìn từ trong phòng; ảnh được cắt vừa khung, không méo; nếu thiếu file thì dùng ảnh búp bê tự vẽ bằng code (`scripts/barbie_photos.py` → `assets/barbie/*.png`, không dùng ảnh/nhân vật có bản quyền; xoá PNG để vẽ lại; thay PNG cùng tên để dùng ảnh khác cùng tỉ lệ 0,34×0,52). Người dùng đang "thử" Barbie, chưa chốt.

## Concept hiện tại: V3 "Sky Cinema" (nguồn: `docs/sky-cinema.txt`)
| Vai trò | Màu |
|---|---|
| Tường sảnh, vỏ ngoài buồng | Xanh trời #A2CFFE (mờ) |
| Trần, dải sát trần (cao 0,35) | Xanh nhạt #D6E9FF |
| Chân tường (cao 0,25), sofa, quầy, rèm phông đậm | Xanh đậm #6FA8E8 |
| Sàn | Xám lạnh #D9DEE4 |
| **Trong buồng** (vách, trần) | Trắng ngà #F4F1EA (bắt buộc, không xanh) |
| Rèm nhung cửa buồng, chữ nổi | Vàng bơ #FFE98A |
| Ánh sáng ấm (bóng tròn gương, đèn viền chữ, đèn tuýp) | 2700K / #FFFFC5 |
| Nhôm bạc (khung gương, kệ, mặt quầy, bàn) | #B4B8BD |
Rèm phông 3 tấm vải trơn: xanh trời, xanh đậm, trắng ngà (không hoạ tiết). Chỉ 3 điểm nhấn vàng: rèm cửa, chữ nổi có đèn viền, gương bóng đèn. Sofa xanh đậm, ghế băng trong buồng trắng ngà.
Các concept cũ (vintage, minimal concrete, Minimal Cinema rượu vang) đã bỏ; chỉ còn trong `scripts/archive/`.

### Tên khoá vật liệu cũ (dễ nhầm)
Trong code `MATS`: `"walnut"` = sơn xanh trời (tường), `"brass"` = **nhôm bạc**, `"velvet"` = nhung xanh đậm (sofa), `"gold"` = vàng bơ, `"butter"` = rèm cửa, `"seat"` = simili trắng ngà, `"sky"`/`"deepblue"`/`"skyfaint"` = các lớp sơn xanh, `"melamine"` = ván trắng, `"cream"` = trong buồng. Tên đối tượng theo khu: `A_*` sảnh chờ, `B_*` giá đạo cụ, `C_*` quầy vé, `D_*` bàn gương, `F_Rem_*` rèm phông, `Booth_*` buồng, `Room_*` phòng. (Khu E check-in đã bỏ, `build_E()` không còn.)

## Chiếu sáng (đã tính, xem `docs/thiet-ke-chieu-sang.md`)
Sảnh 15 m² (18 − buồng 3). 7 đèn âm trần LED 15 W / 1.500 lm / **4000K** CRI≥90 (`DOWNLIGHTS`, `DL_LUMEN`, `calc_lux()` trong build_scene.py) + đèn thanh treo T1/T2 + tuýp + 26 bóng gương 2700K. Trung bình ≈340 lx, min ≈180 lx. 4000K chọn để tường xanh không bị xám vàng (PDF khuyên 2700K nhưng thử render thấy 3000K làm xanh xám); người dùng chưa xác nhận chốt màu đèn.

## Cài đặt render (đã chốt, đừng đổi bừa)
- Color Management: View Transform **Standard**, Look **None** (AgX/Filmic làm xỉn màu, đừng dùng).
- Đèn "trắng" phải là **6500K** (`NEUTRAL_K`). Blender coi 5000–5500K là vàng cam → từng làm trần/vách kem thành nâu cam. Chỉ dùng 2700K cho đèn ấm.
- `LIGHT_SCALE = 0.125`: công suất đèn phòng nhỏ hơn giá trị Eevee cho hợp Cycles (flash và Plan_Sun không nhân).
- Đèn chụp trong buồng: tấm đèn **hình viên thuốc nằm ngang 0,6 × 0,18 m gắn phẳng trên vách camera**, tâm cao 1,65 m ngay trên ống kính (`pill_panel()`, `buong.den_chup_*`), đèn Blender 5 W 6500K (45 W làm cháy sáng). Hai dải đèn dọc hai bên màn hình cũng là viên thuốc phẳng. **Không có đèn trần trong cabin** và không còn octabox; đã bỏ 2 đèn giả lập hắt sáng.
- Gương Glossy (metallic 1, rough 0,02); world môi trường nhẹ.
- Người nộm: hình đơn giản, một màu xám trung tính (không đánh lừa màu da).
- Mặt bằng (view 05): ortho, Workbench flat, nền trắng, nét mảnh, chữ đen. Ẩn trần (collection `Ceiling`). Workbench cần `diffuse_color` – hàm `sync_viewport_colors()` lo việc này.
- Cabin 01a–c: camera trong buồng, APS-C 23,5 mm, khung dọc, dùng **12 mm** (không phải 17 mm brief) để vừa 3 người ở khoảng cách ~0,9 m.
- Bản nháp Eevee **chưa hiệu chỉnh lại độ sáng** sau khi đổi sang Cycles/LIGHT_SCALE; đừng dùng nháp để đánh giá màu.

## Những thứ người dùng đã quyết (không đề xuất lại)
Bỏ khu check-in; quầy vé chỉ là quầy, không khung/hộp trên; bỏ ring light quanh camera; bỏ tấm hắt foam trắng dưới màn hình; bỏ xà gồ trần và đèn ray (chỉ đèn thanh treo + đèn tuýp); bỏ poster; bỏ màn nhỏ trên mặt tiền buồng; bàn gương đứng không ghế; sofa dáng cuộn kiểu Togo đã thử và **bị từ chối** (quay lại sofa thẳng).

## Vấn đề còn mở (đã báo người dùng)
2. Khoảng cách máy–khách chỉ ~0,9 m (brief cũ 1,2 m).
3. Cửa rèm hẹp ~0,78 m; khoang kỹ thuật 0,40 m và cửa bảo trì ~0,45 m khá chật.
4. Màu xanh bị hắt màu giữa các mặt (trần hơi tím) – nên sơn thử mảng lớn ngoài đời như PDF khuyên.
5. Nên xem người dùng có muốn đảo chiều buồng (khoang kỹ thuật về trái, cửa bảo trì ở đầu hồi trái) không.
6. Thông gió cho PC/máy in/UPS vì buồng sát tường.
7. Chưa có font Playfair Display; đang dùng Segoe UI Light (bỏ font vào `fonts/display.ttf` để đổi).
Ngân sách 150 triệu (PDF): không cần cho việc dựng cảnh.

## Tài liệu
`docs/quan-ly-mau.md` = cách giữ đúng màu concept khi thi công thật (3 tầng màu nền/trung/nhấn, gốc hồng LẠNH, mua vải/vật liệu khó trước – sơn pha theo mẫu vật sau cùng; khi người dùng gửi mã màu vật liệu thật thì cập nhật `mau_theo_y_tuong.barbie` rồi render lại).
`docs/du-toan-mat-bang.md` = dự toán mặt bằng + vỏ buồng (trừ thiết bị điện tử) phương án TIẾT KIỆM: tổng ~55–95 triệu (thường ~67, +10% dự phòng ≈ 60–105); buồng dùng 3 mặt tường phòng làm vách, chỉ dựng mặt tiền + nóc + vách ngăn (~16–29 tr). (người dùng chọn: rẻ nhất mà vẫn ra concept; phòng 6×3 được NGĂN RA từ mặt bằng lớn hơn nên dựng vách thạch cao 3 phía (tường trong cùng sau sofa là tường sẵn có) + trần thạch cao bắt buộc để lắp đèn âm trần: ~37–64 triệu (+10% dự phòng ≈ 41–70), thường ~45; bản đầy đủ ~80–150). Khi đổi thiết kế nội thất, cập nhật file này.
`docs/` chứa chữ trích từ file HTML/PDF của người dùng (`thiet-ke.txt` = concept vintage gốc, `vat-lieu.txt` = V2 Minimal Cinema, `sky-cinema.txt` = V3). Trích lại bằng `python scripts/extract_design.py <file.html> <ra.txt>` (HTML đóng gói lồng nhau; PDF thì dùng `pdftotext`, dấu tiếng Việt có thể mất).
`docs/quyet-dinh-thiet-ke.md` = nhật ký quyết định. `README.md` = hướng dẫn cho người dùng.

## Render qua runner GitHub Actions (nhánh `claude/modest-galileo-vtuecz`) – ĐANG DÙNG
Phiên Claude trên cloud không chạy được Blender, nên render bằng máy của người dùng qua runner tự host:
- `.github/workflows/blender.yml` chạy trên runner nhãn `blender` (máy Windows của người dùng, runner ở
  `C:\actions-runner\actions-runner`, bật bằng `./run.cmd`). Nó chạy script ghi trong `blender/run.txt`
  lên file cảnh ở biến repo `BLEND_FILE`, rồi commit ảnh vào `blender/output/<script>/` (commit `[skip ci]`).
- Push có đụng `blender/scripts/**` hoặc `blender/run.txt` là tự render. Chờ commit
  "Add Blender output from run N" trên nhánh rồi `git pull`.
- `blender/scripts/apply_palette.py` dựng concept hiện tại (`DEFAULT_PALETTE`, đang là `soft_minimal`:
  tường trắng ấm, sàn SPC gỗ sồi sáng lát so le, sofa bouclé dáng Julep, bàn thạch cao, đèn thả vải,
  đèn hắt trần, gương đèn bulb có probe phản chiếu) và lưu `<tên>_<palette>.blend` cạnh file gốc,
  không ghi đè file gốc. EEVEE + AgX, đèn ~3000K.
- Những yêu cầu mới nhất của người dùng trong luồng này (sàn vân gỗ SPC, AgX, sofa Julep, bỏ quầy vé,
  bỏ đèn cầu/đèn tuýp/thảm/chậu cây/kệ QR) được ưu tiên hơn các ghi chú cũ phía trên về pipeline
  `build_scene.py`.

## Quy tắc gửi ảnh render
- Mỗi lần runner render xong: kéo ảnh về và GỬI NGAY cho người dùng bằng `SendUserFile`
  (`display: "render"`), không chờ nhắc. Gửi các góc chính (Cam_03, Cam_02, Cam_04, Cam_08, Cam_s8,
  Cam_s2, Cam_s7 và góc liên quan đến thay đổi), xem ảnh trước, nói một dòng đã đổi gì và còn gì chưa ổn.
