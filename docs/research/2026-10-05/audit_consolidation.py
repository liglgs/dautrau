"""Read-only integrity checks for the consolidated report and its handoff briefs."""
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parent
docs = root.parents[1]
main = docs / 'phan-cong-vong-2' / 'NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md'
body = main.read_text(encoding='utf-8')
assert '\ufffd' not in body
assert 'D:/create/vin/research-2026-10-05' not in body
assert not Path('D:/create/vin/research-2026-10-05').exists()
assert hashlib.sha256((root/'archive'/'agent-original.md').read_bytes()).hexdigest() == '02a6e9c459ca43f0cfeb0f80f07c482cbb952082f71d58decdc3e1b816dc9bab'
ids = re.findall(r'^#### (R2-\d-\d\d) ', body, re.M)
assert len(ids) == 33 and len(set(ids)) == 33
for number in range(1, 5):
    section = re.search(rf'### 15\.{number} .*?(?=\n### 15\.|\n## 16\.)', body, re.S).group(0).strip()
    brief = (docs/'phan-cong-vong-2'/f'nguoi-{number}'/'README.md').read_text(encoding='utf-8')
    assert brief.endswith(section+'\n'), f'Brief {number} drift'
    tasks = re.split(r'\n#### ', section)[1:]
    assert len(tasks) == (9 if number == 2 else 8)
    for task in tasks:
        for field in ['**Bàn giao:**', '**Phụ thuộc:**', '**Nghiệm thu:**', '**Review:**']:
            assert field in task, (task[:30], field)

broken = []
checked = 0
for file in [main, *list((docs/'phan-cong-vong-2').rglob('*.md')), root/'README.md', root/'BACKLOG_VA_TIEU_CHI_NGHIEM_THU.md', root/'KIEM_TRA_DELIVERABLE.md']:
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
        if re.match(r'https?://', target) or target.startswith('#'):
            continue
        checked += 1
        target = target.split('#')[0]
        if not (file.parent / target).resolve().exists():
            broken.append((str(file), target))
assert not broken, broken
manifest = json.loads((root/'data-real'/'manifest.json').read_text(encoding='utf-8'))
valid = [row for row in manifest if row['verified_payload']]
assert len(valid) == 18 and len(manifest) - len(valid) == 1
for row in valid:
    assert hashlib.sha256((root/'data-real'/row['file']).read_bytes()).hexdigest() == row['sha256']
article = ET.parse(root/'data-real'/'pubmed-35799184.xml').getroot()
abstract = '\n'.join(''.join(x.itertext()) for x in article.findall('.//AbstractText'))
assert '2017' in abstract and '2018' in abstract
print('Canonical report and four briefs match: 33 tasks with handoff/dependency/acceptance/reviewer.')
print(f'{checked} local links valid; original preserved; outside folder absent; UTF-8 valid.')
print('18 payload hashes valid, 1 source failure retained; clinical-pharmacy survey dates checked.')
