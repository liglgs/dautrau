"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip } from "@/components/ui";

const TERMS = [
  { term: "hoạt chất", aliases: "active ingredient, generic name", note: "Dùng khi truy vấn PubMed và DailyMed." },
  { term: "biến cố bất lợi", aliases: "adverse event, AE", note: "Không đồng nhất với “tác dụng phụ”." },
  { term: "phù mạch", aliases: "angioedema", note: "Cần ánh xạ sang mã MedDRA khi mở rộng." },
  { term: "nhiễm toan lactic", aliases: "lactic acidosis", note: "Phân biệt với tăng lactate không toan." },
  { term: "quần thể", aliases: "population, subgroup", note: "Gồm tuổi, chức năng thận, thai kỳ." },
];

export default function AdminTerminologyPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Thuật ngữ & từ đồng nghĩa</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Bảng ánh xạ giúp agent dịch nhận định tiếng Việt sang truy vấn tiếng Anh ổn định.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Bảng ánh xạ</CardTitle>
          <Chip tone="caution">Chưa có màn hình sửa trong MVP</Chip>
        </CardHeader>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-[13px]">
            <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Thuật ngữ</th>
                <th className="py-2 pr-4">Từ đồng nghĩa</th>
                <th className="py-2">Ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {TERMS.map((row) => (
                <tr key={row.term} className="border-t border-border">
                  <td className="py-2 pr-4 font-medium text-foreground">{row.term}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{row.aliases}</td>
                  <td className="py-2 text-muted-foreground">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
