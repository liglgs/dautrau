"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip } from "@/components/ui";
import { SourceChip } from "@/components/pv/badges";

const SOURCES = [
  { id: "pubmed" as const, state: "đang bật", note: "Truy vấn theo hoạt chất + biến cố; ghi lại ngày truy vấn.", limit: "Chất lượng thiết kế khác nhau" },
  { id: "dailymed" as const, state: "đang bật", note: "Đọc nhãn thuốc theo mục: cảnh báo, liều, chống chỉ định.", limit: "Văn bản quy định, không phải dịch tễ" },
  { id: "faers" as const, state: "đang bật", note: "Đếm báo cáo theo hoạt chất và biến cố; chỉ dùng làm tín hiệu.", limit: "Không có mẫu số" },
];

export default function AdminSourcesPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Nguồn dữ liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Mỗi nguồn có giới hạn riêng. Giới hạn này hiện trong giao diện khi người dùng chọn nguồn.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {SOURCES.map((source) => (
          <Card key={source.id}>
            <CardHeader>
              <SourceChip source={source.id} />
              <Chip tone="support">{source.state}</Chip>
            </CardHeader>
            <CardBody className="space-y-2 text-[13px] text-muted-foreground">
              <p>{source.note}</p>
              <p className="text-caution-fg">Giới hạn: {source.limit}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quy tắc bắt buộc</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Chỉ FAERS thì không bao giờ tự động kết luận “có bằng chứng ủng hộ”.</p>
          <p>Kết luận “có bằng chứng ủng hộ” cần ít nhất hai nguồn độc lập và một truy vấn phản bác đã chạy.</p>
          <p>Nguồn lỗi hoặc hết hạn mức trở thành khoảng trống dữ liệu, không làm hỏng cả cuộc điều tra.</p>
        </CardBody>
      </Card>
    </div>
  );
}
