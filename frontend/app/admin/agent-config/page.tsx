"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip, Label, Select } from "@/components/ui";

export default function AdminAgentConfigPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Cấu hình agent</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Ngân sách và ngưỡng dừng. Trần cứng do máy chủ giữ, cấu hình ở đây không thể vượt trần.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ngân sách mặc định</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            <div>
              <Label htmlFor="default-steps">Số bước tối đa</Label>
              <Select id="default-steps" defaultValue="8">
                {[4, 6, 8, 12, 16, 20].map((value) => (
                  <option key={value} value={value}>
                    {value} bước
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="default-docs">Số tài liệu tối đa</Label>
              <Select id="default-docs" defaultValue="50">
                {[10, 25, 50, 75, 100].map((value) => (
                  <option key={value} value={value}>
                    {value} tài liệu
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="default-calls">Số lượt gọi model tối đa</Label>
              <Select id="default-calls" defaultValue="80">
                {[20, 40, 60, 80].map((value) => (
                  <option key={value} value={value}>
                    {value} lượt
                  </option>
                ))}
              </Select>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ngưỡng dừng</CardTitle>
            <Chip tone="ai">Máy chủ quyết định</Chip>
          </CardHeader>
          <CardBody className="space-y-2 text-[13px] text-muted-foreground">
            <p>Bão hoà bằng chứng: dừng khi hai vòng liên tiếp không thêm tài liệu mới.</p>
            <p>Checkpoint bắt buộc: dừng trước khi tạo hồ sơ để người duyệt xem bằng chứng.</p>
            <p>Từ chối kết luận: dừng khi phạm vi còn thiếu hoặc chưa chạy được truy vấn phản bác.</p>
            <p className="text-caution-fg">Cấu hình trên màn hình này chưa nối vào backend; giá trị thật nằm trong mã máy chủ.</p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
