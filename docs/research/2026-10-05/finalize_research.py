"""Consolidate the authorized research document and export four task briefs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import httpx

root = Path(__file__).resolve().parent
docs = root.parents[1]
target = docs / 'phan-cong-vong-2' / 'NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md'
original = root / 'archive' / 'agent-original.md'
expected = '02a6e9c459ca43f0cfeb0f80f07c482cbb952082f71d58decdc3e1b816dc9bab'
assert hashlib.sha256(original.read_bytes()).hexdigest() == expected
assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, 'Target changed: reread before replacing'

# The clinical-pharmacy survey was cited in the first report but not in its packet.
data = root / 'data-real'
manifest_path = data / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
pmid = '35799184'
if not any(row['id'] == 'pubmed-' + pmid for row in manifest):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    params = {'db': 'pubmed', 'id': pmid, 'retmode': 'xml'}
    response = httpx.get(url, params=params, timeout=30)
    response.raise_for_status()
    article = ET.fromstring(response.content).find('PubmedArticle')
    assert article is not None
    assert article.findtext('MedlineCitation/PMID') == pmid
    title = ''.join(article.find('MedlineCitation/Article/ArticleTitle').itertext())
    assert 'clinical pharmacy' in title.lower(), title
    print('Additional source verified:', pmid, title)
    file = data / ('pubmed-' + pmid + '.xml')
    file.write_bytes(response.content)
    manifest.append({'id': 'pubmed-' + pmid, 'requested_url': url, 'params': params,
                     'final_url': str(response.url), 'kind': 'hospital_workflow_primary_survey',
                     'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                     'status': response.status_code, 'file': file.name, 'bytes': len(response.content),
                     'sha256': hashlib.sha256(response.content).hexdigest(), 'verified_payload': True,
                     'coverage': 'PubMed metadata and abstract only; not full paper or respondent-level data'})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

body = (root / 'archive' / 'research-initial.md').read_text(encoding='utf-8')
body = body.replace('# VigiLens sau MVP: bàn làm việc thông tin thuốc và an toàn thuốc bệnh viện',
                    '# Nghiên cứu chuyên sâu và giải pháp E2E: VigiLens cho dược sĩ bệnh viện')
intro = '''

**Bản hợp nhất trong P-066:** nghiên cứu sản phẩm, thẩm định báo cáo agent khác và phân công vòng hai. Tài liệu này là bản chính để nhóm đọc và cập nhật; hai bản ban đầu được lưu trong `docs/research/2026-10-05/archive/` để đối chiếu. Kế hoạch chưa phải tính năng đã triển khai hoặc tiến độ đã xác nhận của từng người.

**Đọc nhanh:** mục 1–9: công việc/pain/dữ liệu/luồng/giao diện; mục 10–13: nền MVP và pilot; mục 14: phần giữ/sửa/loại từ bản agent; mục 15: từng task của bốn người; mục 16: phụ thuộc và thứ tự bàn giao; mục 17–18: ownership và định nghĩa xong; mục 19: việc kế tiếp của Người 2.

**Tài liệu kèm:** [manifest nguồn](../research/2026-10-05/data-real/manifest.json), [backlog theo feature](../research/2026-10-05/BACKLOG_VA_TIEU_CHI_NGHIEM_THU.md), [prototype đã render](../research/2026-10-05/preview.html), [kết quả kiểm tra](../research/2026-10-05/KIEM_TRA_DELIVERABLE.md). Bốn phiếu giao việc nằm trong các thư mục `nguoi-1/` đến `nguoi-4/` ngay cạnh plan, là bản trích từ mục 15, không phải kế hoạch độc lập.
'''
lines = body.splitlines()
body = '\n'.join(lines[:3]) + intro + '\n' + '\n'.join(lines[3:])
body = body.replace('17 snapshot nguồn công khai', '18 snapshot nguồn công khai')
body = body.replace('Sáu snapshot PubMed', 'Bảy snapshot PubMed')
body = body.replace('(3 nghiên cứu thuốc và 3 khảo sát workflow)', '(3 nghiên cứu thuốc và 4 khảo sát workflow)')
body = body.replace('Không thay nội dung của tài liệu đang tồn tại.',
                    'Bản agent trong file này đã được thẩm định và thay bằng bản hợp nhất; quyết định giữ/sửa/loại ghi ở mục 14. Tài liệu chuyên môn khác trong repo được giữ nguyên.')
body = body.replace('Không ấn định số tuần khi chưa biết nhân lực, mẫu dữ liệu và thời gian chuyên viên.',
                    'Phân công theo đúng bốn vai cũ, từng task và thứ tự phụ thuộc được cụ thể hóa ở mục 15–19. Không ấn định số tuần khi chưa biết nhân lực, mẫu dữ liệu và thời gian chuyên viên.')
appendix = (root / 'PHAN_CONG_VONG_2.md').read_text(encoding='utf-8')
appendix = appendix[appendix.index('## 14.'):]
combined = body.rstrip() + '\n\n' + appendix.rstrip() + '\n'
assert 'D:/create/vin/research-2026-10-05' not in combined
target.write_text(combined, encoding='utf-8')

# Readable handoff briefs are derived from the same canonical document.
brief_dir = docs / 'phan-cong-vong-2'
brief_dir.mkdir(exist_ok=True)
titles = ['DU_LIEU_HA_TANG_DEPLOY', 'AGENT_WORKFLOW_API', 'BANG_CHUNG_HO_SO_CHUYEN_MON', 'UI_EVALUATION_DEMO']
for number, title in enumerate(titles, 1):
    pattern = rf'### 15\.{number} .*?(?=\n### 15\.|\n## 16\.)'
    section = re.search(pattern, combined, re.S)
    assert section, number
    header = (f'# Phiếu giao việc vòng hai — Người {number}\n\n'
              'Đề xuất ngày 05/10/2026. Bản trích để nhận việc; cập nhật kế hoạch tại '
              '[báo cáo chính](../NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). '
              'Đọc thêm mục 16–18 trong báo cáo để biết handoff, thứ tự tích hợp và ba mức nghiệm thu. '
              'A = DI/tiếp nhận ADR ngắn; B = ca ADR đầy đủ; C = cập nhật/tái sử dụng. '
              'B/C phụ thuộc dữ liệu/SOP/reviewer; không chặn lát cắt A.\n\n')
    (brief_dir / f'nguoi-{number}').mkdir(exist_ok=True)
    (brief_dir / f'nguoi-{number}' / 'README.md').write_text(header + section.group(0).strip() + '\n', encoding='utf-8')

backlog = root / 'BACKLOG_VA_TIEU_CHI_NGHIEM_THU.md'
text = backlog.read_text(encoding='utf-8')
text = text[:text.index('## Chia công việc toàn nhóm')]
text += ('## Phân công và phụ thuộc\n\nPhân công đúng bốn vai cũ, từng task, bàn giao và định nghĩa xong nằm tại '
         '[báo cáo chính, mục 15–19](../../phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). '
         'Không dùng bảng feature này thay cho phân công cá nhân.\n')
backlog.write_text(text, encoding='utf-8')

qa_path = root / 'KIEM_TRA_DELIVERABLE.md'
qa = qa_path.read_text(encoding='utf-8')
qa = qa.replace('17 snapshot công khai', '18 snapshot công khai')
qa = qa.replace('D:/create/vin/research-2026-10-05/', './')
qa = qa.replace('Các artifact nghiên cứu nằm ngoài repo P-066. Tài liệu untracked đã tồn tại trong repo được giữ nguyên. Không sửa code sản phẩm hoặc đẩy commit cho đề xuất này.',
                'Bộ nghiên cứu đã chuyển vào `P-066/docs/research/2026-10-05`. Báo cáo chính hợp nhất tại `P-066/docs/phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md`; bản agent gốc và bản nghiên cứu ban đầu được lưu trong archive. Có bốn phiếu giao việc trích từ kế hoạch chính. Không sửa code sản phẩm, commit hoặc push ở lượt hợp nhất này.')
qa_path.write_text(qa, encoding='utf-8')

prepare = root / 'prepare_research_packet.py'
text = prepare.read_text(encoding='utf-8').replace('["41943791", "31486525", "35615486"]', '["41943791", "31486525", "35615486", "35799184"]')
prepare.write_text(text, encoding='utf-8')
verify = root / 'verify_packet.py'
text = verify.read_text(encoding='utf-8').replace('assert len(verified) == 17', 'assert len(verified) == 18').replace('17 payload hashes OK', '18 payload hashes OK')
verify.write_text(text, encoding='utf-8')

archive_note = '''# Bản lưu để đối chiếu

- `agent-original.md`: nguyên bản 351 dòng của agent khác, SHA-256 `02a6e9c459ca43f0cfeb0f80f07c482cbb952082f71d58decdc3e1b816dc9bab`. Có số liệu/khẳng định bị bác ở mục 14 của báo cáo chính; không dùng làm nguồn seed hoặc kế hoạch hiện hành.
- `research-initial.md`: bản nghiên cứu trước hợp nhất. Số snapshot và vị trí artifact trong bản này phản ánh thời điểm cũ.
- Kế hoạch và nghiên cứu hiện hành nằm tại `docs/phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md`.
'''
(root / 'archive' / 'README.md').write_text(archive_note, encoding='utf-8')
(root / 'README.md').write_text('''# Bộ nghiên cứu 05/10/2026

Báo cáo chính: [nghiên cứu E2E và phân công](../../phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md).

`data-real/manifest.json` chứa 18 payload công khai đã kiểm hash và 1 lần lấy thất bại. Không chứa hồ sơ người bệnh hay nhãn gold chuyên gia. Tài liệu public/index/abstract/SPL có loại nguồn khác nhau; không coi toàn bộ là nghiên cứu lâm sàng.

`preview.html` là prototype độc lập đã render, không phải frontend sản phẩm. `archive/` giữ bản ban đầu để đối chiếu. Các script thu thập có thể thay payload/manifest khi chạy lại; không chạy lại trên bộ đóng băng để đánh giá. `verify_packet.py` kiểm bộ hiện tại và health các dịch vụ, không refetch nguồn.

Các phiếu giao việc riêng nằm ở `docs/phan-cong-vong-2/`; cập nhật bản chính trước, rồi đồng bộ phiếu trích. `PHAN_CONG_VONG_2.md` là bản nguồn dùng khi hợp nhất, không phải nguồn tiến độ.
''', encoding='utf-8')
print('Canonical report:', target, len(combined.splitlines()), 'lines')
print('Four task briefs exported; originals preserved; runtime code untouched.')
