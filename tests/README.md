# Kioku MCP Test Suite

Thư mục này chứa toàn bộ các bài Test (Integration và End-to-End) dành cho Kioku MCP Server.

## 1. Pytest Integration Tests

Kiểm thử logic của hệ thống với các mock/stub (FakeEmbedder, FakeExtractor, InMemoryGraphStore) hoặc với dữ liệu và Service thật tùy theo cấu hình biến môi trường.

### Chạy bằng Mô phỏng (Mock/Stub)
Mặc định bài test sẽ chạy các components ảo (Fake) ngay trên bộ nhớ, không cần DB thật. Cực kỳ nhanh.
```bash
make test
# Hoặc: pytest tests/
```

### Chạy bằng Mode E2E (Dữ liệu thật)
Kiểm thử kết nối với các container thực sự (ChromaDB, FalkorDB, Ollama) và API Anthropic thực sự.
```bash
# 1. Đảm bảo docker compose up -d đã chạy các services
# 2. Đảm bảo .env đã có đủ KIOKU_ANTHROPIC_API_KEY
KIOKU_E2E=1 pytest tests/test_server.py -v
```

## 2. MCP Client E2E Test

Kịch bản Python độc lập `e2e_mcp_client.py` đóng vai trò là một MCP Client thực thụ (giống như ứng dụng Cursor hoặc Claude Desktop). Nó giao tiếp với Kioku MCP Server qua đường ống tiêu chuẩn (stdio) mô phỏng chính xác môi trường và flow làm việc thực tế.

### Cách chạy
```bash
export $(grep -v '^#' ../.env | xargs) && python tests/e2e_mcp_client.py
```

### Các Test Case được thực thi tự động trong `e2e_mcp_client.py`:

1. **Server Initialization:** Cài đặt kết nối Stdio và chạy lệnh `initialize` handshake với server.
2. **List Tools:** Gọi lệnh lấy toàn bộ danh sách Tools có thể dùng (6 tools).
3. **Execution: Mảng Tools (6 Tools)**
   - **`save_memory`**: Lưu một câu ký ức tiếng Việt phức tạp (VD: `"Cuối tuần đi cà phê với Mai, thảo luận về dự án OpenClaw rất thú vị."`).
   - **`search_memories`**: Tìm kiếm thử một từ khóa (VD: `"Dự án OpenClaw"`) để test tính năng Tri-hybrid search (BM25 + Vector + Graph).
   - **`get_timeline`**: Lấy về mảng thời gian các sự kiện gần đây theo giới hạn số lượng.
   - **`recall_related`**: Test nền tảng Knowledge Graph (Graph Traversal) dựa trên entity `"Mai"`.
   - **`list_memory_dates`**: Xác thực tính năng gọi mảng các ngày có dữ liệu ghi chú.
   - **`explain_connection`**: Xét tính năng giải thích đường dẫn shortest-path giữa 2 entity tự do bằng cách thử nối 2 node có sẵn (VD: Giữa "Mai" và "OpenClaw").
4. **List Resources:** Yêu cầu server trả về các URI patterns (Ví dụ: `kioku://entities/*`).
5. **Execution: Mảng Resources (2 Resources)**
   - **`kioku://entities/Mai`**: Đọc Profile Entity Markdown cho nhân vật "Mai" từ Graph DB.
   - **`kioku://memories/{today}`**: Đọc toàn bộ nhật ký theo định dạng Markdown trực tiếp trong một ngày nhất định.
6. **List Prompts:** Cập nhật danh sách Prompt Templates.
7. **Execution: Mảng Prompts (3 Prompts)**
   - **`analyze_relationships`**: Phân tích quan hệ của Entity bằng cách inject vào message LLM tham số entity truyền vào.
   - **`reflect_on_day`**: Kêu gọi LLM đóng vai "người bạn" viết một nhận xét, tổng hợp cuối ngày cho thông tin {date}.
   - **`weekly_review`**: Trải qua 7 ngày nhật ký để LLM giúp review tuần vừa qua (nhận xét ups, downs).
