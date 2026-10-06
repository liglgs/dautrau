-- Tạo cơ sở dữ liệu kho ELT trên một cụm PostgreSQL đã có sẵn (không dùng docker-compose.elt.yml).
-- Cách dùng:
--   docker exec -i <container> psql -U medreview -d postgres -v ON_ERROR_STOP=1 < scripts/db/init-elt.sql
-- hoặc: psql "postgresql://medreview:medreview@localhost:5432/postgres" -f scripts/db/init-elt.sql
SELECT 'CREATE DATABASE vigilens_elt OWNER medreview'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'vigilens_elt')\gexec

\connect vigilens_elt
CREATE SCHEMA IF NOT EXISTS public AUTHORIZATION medreview;
GRANT ALL PRIVILEGES ON DATABASE vigilens_elt TO medreview;
