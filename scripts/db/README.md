# Cơ sở dữ liệu cho ELT và RAG

Kho ELT dùng PostgreSQL riêng, tên `vigilens_elt`, tách khỏi cơ sở dữ liệu VMEC (`medreview`).

## Cách 1 (khuyến nghị): Docker Compose

```bash
docker compose -f docker-compose.elt.yml up -d --wait
```

- Cổng mặc định: `127.0.0.1:5433` (tránh trùng cụm VMEC ở cổng 5432).
- Biến: `POSTGRES_USER` (mặc định `medreview`), `POSTGRES_PASSWORD` (mặc định `medreview`),
  `ELT_DB_NAME` (mặc định `vigilens_elt`), `ELT_DB_PORT` (mặc định `5433`).
- Dữ liệu lưu trong volume `elt_postgres_data`.

## Cách 2: dùng cụm PostgreSQL đang có

```bash
docker exec -i <container> psql -U medreview -d postgres -v ON_ERROR_STOP=1 < scripts/db/init-elt.sql
```

Sau đó đặt `ELT_DATABASE_URL` trong `.env`, ví dụ:

```
ELT_DATABASE_URL=postgresql+psycopg://medreview:medreview@localhost:5432/vigilens_elt
```

## Kiểm tra nhanh

```bash
python -m scripts.elt.check_warehouse
```

Lệnh này in số bản ghi theo bảng, trạng thái chất lượng tài liệu và trạng thái chỉ mục ChromaDB.
