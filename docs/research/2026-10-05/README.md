# Bộ nghiên cứu 05/10/2026

Báo cáo chính: [nghiên cứu E2E và phân công](../../phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md).

`data-real/manifest.json` chứa 18 payload công khai đã kiểm hash và 1 lần lấy thất bại. Không chứa hồ sơ người bệnh hay nhãn gold chuyên gia. Tài liệu public/index/abstract/SPL có loại nguồn khác nhau; không coi toàn bộ là nghiên cứu lâm sàng.

`preview.html` là prototype độc lập đã render, không phải frontend sản phẩm. `archive/` giữ bản ban đầu để đối chiếu. Các script thu thập có thể thay payload/manifest khi chạy lại; không chạy lại trên bộ đóng băng để đánh giá. `verify_packet.py` kiểm bộ hiện tại và health các dịch vụ, không refetch nguồn.

Các phiếu giao việc riêng nằm ở `docs/phan-cong-vong-2/nguoi-1/` đến `nguoi-4/`; cập nhật bản chính trước, rồi đồng bộ phiếu trích. `PHAN_CONG_VONG_2.md` là bản nguồn dùng khi hợp nhất, không phải nguồn tiến độ.
