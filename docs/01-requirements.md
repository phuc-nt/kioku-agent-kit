# Kioku MCP Server — Requirements

## Mục tiêu

Kioku là một MCP Server đóng vai trợ lý lưu trữ ký ức cá nhân (diary/lifelog). Người dùng nhắn bất kỳ suy nghĩ, sự kiện, cảm xúc nào → Kioku lưu trữ, hiểu ngữ nghĩa, và có thể truy vấn lại theo **ý nghĩa sâu** — giúp người dùng lý giải bản thân và không bao giờ quên các ký ức quan trọng.

## Functional Requirements

### FR1 — Lưu trữ ký ức (Save)
- Nhận đầu vào là text tự do (không cần format)
- Tự động gắn timestamp, extract entities (người, nơi chốn, cảm xúc, sự kiện)
- Lưu raw text vào Markdown file (source of truth)
- Index song song vào Vector DB, Graph DB, Keyword Index

### FR2 — Tìm kiếm Tri-hybrid (Search)
- **Keyword Search (BM25):** Tìm chính xác theo từ khóa
- **Vector Search (Semantic):** Tìm theo ý nghĩa tương đồng
- **Graph Search (GraphRAG):** Tìm theo chuỗi liên kết nhân-quả, thời gian, cảm xúc
- Kết hợp 3 kết quả bằng RRF (Reciprocal Rank Fusion) reranker

### FR3 — Truy vấn liên kết (Recall & Explain)
- Từ một entity, đi dọc theo graph edges để tìm các sự kiện liên quan
- Giải thích mối liên hệ giữa 2 sự kiện/thực thể bất kỳ

### FR4 — Xem lại ký ức (Browse)
- Xem timeline các sự kiện trong khoảng thời gian theo thứ tự thời gian
- Xem danh sách các ngày đã ghi chú nhật ký
- Lấy danh sách entities hoặc thống kê cơ bản thông qua MCP resources

### FR5 — Prompt Templates
- `reflect_on_day`: Hồi tưởng cuối ngày
- `weekly_review`: Tổng kết tuần
- `find_why`: Truy vấn nguyên nhân cảm xúc/hành vi

## Non-Functional Requirements

| Yêu cầu | Mục tiêu |
|---|---|
| **Privacy** | 100% local, không gửi dữ liệu lên cloud (trừ LLM API calls) |
| **Latency** | Search < 2s, Save < 3s (bao gồm extraction) |
| **Portability** | MCP protocol → dùng được với OpenClaw, Claude Desktop, Cursor |
| **Durability** | Markdown = source of truth; Graph/Vector chỉ là derived index, rebuild được |
| **Deployment** | Docker Compose cho toàn bộ stack, chạy trên Mac Mini |

## Constraints

- Graph DB: **FalkorDB** (Docker container)
- Vector DB: **ChromaDB** (embedded hoặc Docker)
- Keyword Index: **SQLite FTS5** (file-based, trong container MCP server)
- Embedding: Local via **Ollama** hoặc API (Anthropic/OpenAI)
- Entity Extraction LLM: **Claude Haiku 4.5** via Anthropic API
- MCP Server: **Python + FastMCP**, chạy local
