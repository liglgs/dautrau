# Kịch bản demo Người 4

Cập nhật 03/10/2026. Seed/replay ở [PR P26 #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12), chỉ chạy sau checkout PR hoặc sau merge. Chạy từ gốc repo: `python scripts/seed_demo.py --output data/demo/person4`. Thuốc/biến cố, nhãn và recording đều authored synthetic; không có source/model live, phê duyệt thật hoặc benchmark chuyên môn.

| Scenario | Fixture | Điều cần trình bày | Dossier tạo bởi seed |
|---|---|---|---|
| Claim quá rộng | TestDrugA/TestEventA | Evidence người lớn không tự suy rộng mọi quần thể | `dossiers/broad.md` |
| Mâu thuẫn biểu kiến | TestDrugB/TestEventB | Khác quần thể cần chuyên viên, không kết luận chỉ từ hai stance | `dossiers/apparent.md` |
| FAERS diễn giải quá mức | TestDrugC/TestEventC | Báo cáo tự nguyện không cho incidence/causality | `dossiers/faers.md` |
| Replanning | TestDrugD/TestEventD | Trình bày gap/đổi nguồn/contrary search cần trace agent | `dossiers/replan.md`; chưa chứng minh replanning thật |

Seed còn hai heldout fixture riêng; manifest/snapshots/labels/recordings ở cùng output directory. UI có bộ mock riêng, seed eval không tự nạp vào UI.

## Demo thao tác và nghiệm thu

Chạy local theo [runbook](runbook.md) và [frontend README](../vigilens/README.md). Ghi rõ mock, API synthetic hay nguồn live ở từng bước. Nhánh frontend vẫn Draft vì browser regression lỗi: không coi các bước create/poll/review/export tự động đã nghiệm thu.

Khi browser ổn định: tạo claim → theo dõi timeline/gaps → mở evidence/quote/version → so sánh scope → review theo version/409 → approve dossier/export → sửa evidence và kiểm approval invalidation. Role demo không phải phiên đăng nhập server. Không export nháp hoặc dùng điểm fixture làm thành tích sản phẩm.

Media/screenshots, video UI fixture và pitch outline từ VinhDang chưa được nhập trong gói ba PR này. Bản live/narration/PPTX/deploy URL và clone sạch bởi reviewer chưa nghiệm thu; hoàn thiện sau phần chức năng và dữ liệu cần thiết. Không có link tới media chưa hiện diện trên main.
