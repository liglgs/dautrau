#!/usr/bin/env bash
# Cài đặt và nạp kho dữ liệu VigiLens (P-066) trên một máy mới — một lệnh duy nhất.
#
#   ./scripts/setup_elt.sh                # cài đặt đầy đủ, dùng dữ liệu đã đóng băng + dữ liệu tham chiếu
#   ./scripts/setup_elt.sh --offline      # không tải gì từ mạng (dùng bản thô đã có sẵn)
#   ./scripts/setup_elt.sh --live         # tải thêm dữ liệu trực tiếp từ PubMed/DailyMed/openFDA
#   ./scripts/setup_elt.sh --no-rag       # bỏ bước dựng chỉ mục vector
#   ./scripts/setup_elt.sh --reset        # xoá sạch bảng trong kho rồi nạp lại
#   ./scripts/setup_elt.sh --skip-install # bỏ bước tạo venv và cài phụ thuộc
#
# Script có thể chạy lại nhiều lần: bước nào đã xong sẽ được bỏ qua.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE="all"
OFFLINE=0
LIVE=0
SKIP_INSTALL=0
RESET=0
DO_RAG=1
PYTHON_BIN="${PYTHON_BIN:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --offline) OFFLINE=1 ;;
    --live) LIVE=1 ;;
    --no-rag) DO_RAG=0 ;;
    --reset) RESET=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    --help|-h)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Tham số không hợp lệ: $1 (xem --help)" >&2; exit 2 ;;
  esac
  shift
done

log()  { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31mxx %s\033[0m\n' "$*" >&2; exit 1; }

# Chọn trình thông dịch tạo được môi trường ảo: python3.12 trước, rồi python3.11,
# rồi python3. Trên Ubuntu thiếu gói python3.X-venv thì `-m venv` sẽ hỏng, nên
# phải thử bằng `import ensurepip` chứ không chỉ kiểm tra phiên bản.
python_ok() {
  command -v "$1" >/dev/null 2>&1 || return 1
  "$1" -c 'import sys, ensurepip; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}
if [ -n "${PYTHON_BIN:-}" ] && python_ok "$PYTHON_BIN"; then
  :
elif [ -n "${PYTHON_BIN:-}" ] && command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  die "$PYTHON_BIN không tạo được môi trường ảo (thiếu ensurepip/venv). Cài python3-venv hoặc đặt PYTHON_BIN khác."
else
  for candidate in python3.12 python3.11 python3; do
    if python_ok "$candidate"; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
  python_ok "${PYTHON_BIN:-python3}" \
    || die "Không tìm thấy Python 3.11+ tạo được môi trường ảo. Cài python3-venv (hoặc python3.11-venv) rồi chạy lại."
fi
echo "Dùng trình thông dịch: $PYTHON_BIN ($("$PYTHON_BIN" -V 2>&1))"

# ---------------------------------------------------------------------------
# 1. Môi trường ảo và phụ thuộc
# ---------------------------------------------------------------------------
if [ "$SKIP_INSTALL" -eq 0 ]; then
  log "Bước 1/6: môi trường ảo và phụ thuộc Python"
  if [ -d .venv ] && [ ! -x .venv/bin/python ]; then
    warn "Thấy .venv hỏng (thiếu bin/python) — xoá để tạo lại."
    rm -rf .venv
  fi
  [ -d .venv ] || "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt -r requirements-elt.txt
else
  log "Bước 1/6: bỏ qua cài đặt (--skip-install)"
fi
[ -x .venv/bin/python ] || die "Thiếu .venv/bin/python. Bỏ --skip-install hoặc tạo venv thủ công."

PY=".venv/bin/python"

# ---------------------------------------------------------------------------
# 2. Tệp .env
# ---------------------------------------------------------------------------
log "Bước 2/6: cấu hình .env"
if [ ! -f .env ]; then
  [ -f .env.example ] || die "Không có .env.example để tạo .env."
  cp .env.example .env
  echo "Đã tạo .env từ .env.example."
fi
ensure_env() {
  local key="$1" value="$2"
  if ! grep -q "^${key}=" .env; then
    printf '\n%s=%s\n' "$key" "$value" >> .env
    echo "Đã thêm ${key} vào .env."
  fi
}
ensure_env ELT_DATABASE_URL "postgresql+psycopg://medreview:medreview@localhost:5433/vigilens_elt"
ensure_env ELT_DB_PORT "5433"
ensure_env ELT_DB_NAME "vigilens_elt"
ensure_env RAG_ENABLED "true"
ensure_env RAG_CHROMA_DIR "./data/chroma"
ensure_env RAG_COLLECTION "vigilens_docs"
ensure_env RAG_EMBEDDING_PROVIDER "auto"
ensure_env RAG_EMBEDDING_MODEL "gemini-embedding-001"
ensure_env RAG_TOP_K "6"
if ! grep -q "^INVESTIGATOR_TOKEN=." .env; then
  ensure_env INVESTIGATOR_TOKEN "dev-investigator"
fi
if ! grep -q "^REVIEWER_TOKEN=." .env; then
  ensure_env REVIEWER_TOKEN "dev-reviewer"
fi

# ---------------------------------------------------------------------------
# 3. PostgreSQL
# ---------------------------------------------------------------------------
log "Bước 3/6: PostgreSQL (docker compose -f docker-compose.elt.yml)"
DB_CONTAINER="vigilens-elt-db"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
      echo "Container $DB_CONTAINER đang chạy — bỏ qua docker compose."
    elif docker compose -f docker-compose.elt.yml up -d --wait; then
      echo "Đã dựng PostgreSQL bằng docker compose."
    else
      warn "docker compose không dựng được PostgreSQL (có thể do cổng 5433 đã bị chiếm"
      warn "bởi một container cùng tên từ thư mục khác). Vẫn tiếp tục các bước sau."
      warn "Kiểm tra: docker compose -f docker-compose.elt.yml up -d --wait"
    fi
  else
    warn "Docker chưa chạy hoặc không có quyền. Bỏ qua bước dựng PostgreSQL."
    warn "Chạy lại: docker compose -f docker-compose.elt.yml up -d --wait"
  fi
else
  warn "Không tìm thấy docker. Bỏ qua bước dựng PostgreSQL."
  warn "Chạy lại: docker compose -f docker-compose.elt.yml up -d --wait"
fi

# ---------------------------------------------------------------------------
# 4. Tải dữ liệu (gói đóng băng + tài liệu tham chiếu)
# ---------------------------------------------------------------------------
log "Bước 4/6: tải dữ liệu và ghi manifest"
# `--profile live` gọi API PubMed/DailyMed/openFDA; `all` = gói đóng băng + tham chiếu + trực tiếp.
if [ "$LIVE" -eq 1 ]; then
  PROFILE="live"
fi
FETCH_ARGS=(--profile "$PROFILE")
if [ "$OFFLINE" -eq 1 ]; then
  FETCH_ARGS+=(--offline)
fi
"$PY" -m scripts.elt.run_elt "${FETCH_ARGS[@]}" || die "Bước tải/phân tích dữ liệu thất bại."

# ---------------------------------------------------------------------------
# 5. Nạp kho và dựng chỉ mục vector
# ---------------------------------------------------------------------------
log "Bước 5/6: nạp PostgreSQL và dựng chỉ mục ChromaDB"
LOAD_ARGS=(--profile "$PROFILE")
[ "$RESET" -eq 1 ] && LOAD_ARGS+=(--reset-db)
[ "$DO_RAG" -eq 0 ] && LOAD_ARGS+=(--skip-rag)
[ "$OFFLINE" -eq 1 ] && LOAD_ARGS+=(--offline)
"$PY" -m scripts.elt.run_elt "${LOAD_ARGS[@]}" || die "Bước nạp kho thất bại."

# ---------------------------------------------------------------------------
# 6. Kiểm tra và sinh tài liệu
# ---------------------------------------------------------------------------
log "Bước 6/6: kiểm tra kho và sinh tài liệu mô tả dữ liệu"
if "$PY" -m scripts.elt.check_warehouse; then
  echo "Kho đạt kiểm tra."
else
  warn "Kho chưa đạt kiểm tra — đọc kỹ phần cảnh báo ở trên (thường do PostgreSQL chưa chạy)."
fi
"$PY" -m scripts.elt.docs_data || warn "Chưa sinh được docs/data/bao-cao-chat-luong.md."

log "Hoàn tất"
cat <<'EOF'
Bước tiếp theo:
  1. Chạy API:      .venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
  2. Chạy giao diện: cd frontend && npm ci && npm run dev
  3. Kiểm tra lại:   .venv/bin/python -m scripts.elt.check_warehouse
EOF
