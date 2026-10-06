# Bàn giao dữ liệu offline — Người 1

**Trạng thái:** checklist và dữ liệu kiểm thử kỹ thuật; **không có dữ liệu bệnh viện thật** trong repository này.

## Inventory hiện tại

| Hạng mục cần từ bệnh viện | Trạng thái | Được phép dùng? | Ghi chú/hành động |
| --- | --- | --- | --- |
| SOP tiếp nhận DI/ADR | Chưa có | Không | Xin phiên bản, chủ sở hữu, ngày hiệu lực và phạm vi sử dụng. |
| Mẫu phiếu DI/ADR | Chưa có | Không | Xin bản trống hoặc mẫu đã khử định danh; không lấy hồ sơ ca. |
| Danh mục thuốc nội bộ | Chưa có | Không | Xin CSV theo đặc tả bên dưới; chưa coi dữ liệu synthetic là danh mục BV. |
| Quy tắc khử định danh | Chưa có | Không | Đơn vị xác nhận trường cấm, quy trình rà soát và người chịu trách nhiệm. |
| Quyền sử dụng/lưu trữ/tái phân phối | Chưa có | Không | Cần văn bản phạm vi, thời hạn, nơi lưu, bên được truy cập và điều kiện xoá. |
| Đầu mối nghiệp vụ, CNTT và pháp chế | Chưa có | Không | Ghi tên/chức danh/kênh liên lạc theo kênh được bệnh viện cho phép; không ghi thông tin liên hệ vào repo. |
| Snapshot công khai PubMed/DailyMed/FAERS | Đã có | Theo điều khoản từng nguồn | Chỉ dùng cho pipeline/bằng chứng công khai; PubMed là `abstract_only`, FAERS không chứng minh nhân quả. |
| CSV kiểm thử danh mục thuốc | Đã có — synthetic | Chỉ kiểm thử kỹ thuật | `data/dictionaries/hospital-drug-catalog.synthetic.csv`; file và từng bản ghi đều gắn nhãn `synthetic`. |

## Checklist xin và nhận dữ liệu

1. Xác định đầu mối được uỷ quyền của bệnh viện và mục đích DI/ADR cụ thể.
2. Xin SOP, mẫu DI/ADR, danh mục thuốc và văn bản quyền sử dụng **trước** khi nhận bất kỳ hồ sơ ca nào.
3. Chốt trường được phép, trường phải bỏ/che, nơi lưu, thời hạn lưu, thành viên được truy cập và quy trình thu hồi/xoá.
4. Với tài liệu nhận được, ghi provenance: nguồn, chủ sở hữu, phiên bản, ngày phát hành, ngày hiệu lực, ngày nhận, phạm vi quyền, checksum và vị trí lưu được phép.
5. Kiểm tra khử định danh trước ingest: không có định danh trực tiếp, định danh liên kết hoặc free text chưa được rà soát. Nếu chưa chắc chắn, dừng ingest và hỏi đầu mối.
6. Đối chiếu CSV danh mục bằng `scripts.elt.hospital_catalog.import_hospital_catalog`; lỗi validation phải được trả về cho bên cung cấp, không tự đoán giá trị thiếu.
7. Mapping DailyMed chỉ tạo `candidate` khi hoạt chất, hàm lượng, dạng bào chế **và** đường dùng khớp. Không tự `approved`; dược sĩ phải xác nhận.
8. Lưu snapshot/version và report diff theo đoạn khi tài liệu thay đổi. Nội dung cùng SHA-256 không tạo công việc review mới.

## Đặc tả CSV danh mục thuốc

Header và thứ tự cột bắt buộc:

```text
hospital_code,brand_name,active_ingredient,strength,dosage_form,route,manufacturer,synthetic_label
```

- Bảy cột đầu không rỗng; `hospital_code` là duy nhất trong mỗi file.
- Dữ liệu thật dùng `synthetic_label` rỗng. Chỉ import sau khi quyền sử dụng đã được xác nhận.
- Dữ liệu synthetic phải có dòng đầu `# synthetic: true` và mọi record có `synthetic_label=SYNTHETIC`.
- Không đưa mã bệnh nhân, tên, ngày sinh, số hồ sơ, địa chỉ hoặc free text ca bệnh vào CSV này.

## Giới hạn mapping DailyMed

DailyMed là nhãn sản phẩm Hoa Kỳ để đối chiếu ứng viên, không chứng minh sản phẩm đang lưu hành tại Việt Nam hoặc trong bệnh viện. Pipeline bắt buộc kiểm bốn thuộc tính: hoạt chất, hàm lượng, dạng bào chế và đường dùng. Do đó pantoprazole tiêm không khớp viên uống, và ciprofloxacin nhỏ tai không khớp sản phẩm uống. `candidate` vẫn cần dược sĩ xác nhận; `approved` luôn `false` ở bước import.

## SourceResult và diff version

`src.services.sources.result.SourceResult` là adapter additive cho `SourceSearchResult` hiện có. Nó phân biệt `timeout`, `http_error`, `empty`, `rate_limited` và `partial`; HTTP 404 là `source_gap`, không phải kết luận không có bằng chứng. Metadata giữ `version`, `published_date`, `effective_time` và `retrieved_at`; PubMed vẫn được biểu diễn `abstract_only` bởi metadata tài liệu.

`src.services.warehouse.version_diff.diff_versions` tạo `ChangeSet` theo đoạn, giữ provenance cũ/mới và chỉ yêu cầu review khi SHA-256 nội dung đổi. Module này chưa tạo FollowUp/WorkItem khi contract liên quan chưa được chốt.
