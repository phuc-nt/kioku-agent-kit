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
2. **List Tools:** Gọi lệnh lấy toàn bộ danh sách Tools có thể dùng (8 tools).
3. **Execution: Mảng Tools**
   - **`save_memory`**: Lưu một câu ký ức tiếng Việt phức tạp (VD: `"Cuối tuần đi cà phê với Mai, thảo luận về dự án OpenClaw rất thú vị."`).
   - **`search_memories`**: Tìm kiếm thử một từ khóa (VD: `"Dự án OpenClaw"`) để test tính năng Tri-hybrid search (BM25 + Vector + Graph).
   - **`get_timeline`**: Lấy về mảng thời gian các sự kiện gần đây.
   - **`recall_related`**: Test thuật toán duyệt Knowledge Graph (Graph Traversal) dựa trên entity `"Mai"` để tìm thấy các topic và product quan hệ mật thiết.
4. **List Resources:** Yêu cầu server trả về các URI patterns (Ví dụ: `kioku://entities/*`).
5. **Execution: Mảng Resources**
   - **`kioku://entities/Mai`**: Test khả năng tự tổng hợp file Profile Entity Markdown cho nhân vật "Mai" từ Graph DB.
6. **List Prompts:** Cập nhật danh sách Prompt Templates.
7. **Execution: Mảng Prompts**
   - **`analyze_relationships`**: Test khả năng sinh Prompt gắn thông số động của LLM dựa trên Entity đút vào.
