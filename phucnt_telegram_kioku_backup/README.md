# Telegram Kioku Backup

**Lý do Backup:**
Mọi dữ liệu cốt lõi (Single Source of Truth) của Kioku Agent thông qua Telegram Bot đều được lưu dưới dạng file Markdown. Các database khác (ChromaDB, FalkorDB, SQLite) chỉ là cache phục vụ tìm kiếm. Do đó, trước khi refactor hoặc nâng cấp hệ thống lớn, chỉ cần backup thư mục Markdown này là có thể đảm bảo an toàn 100% dữ liệu gốc, không lo mất mát lịch sử trò chuyện hay kiến thức.

**Cách Tái Thiết Lập (Restore):**
1. Đảm bảo OpenClaw Gateway/Bot đang dừng tạm thời (hoặc ít nhất không thao tác).
2. Chạy thư mục script tự động (từ thư mục gốc `kioku-mcp`):

```bash
KIOKU_USER_ID=telegram uv run python phucnt_telegram_kioku_backup/restore.py
```

*Script này sẽ làm 3 việc:*
- Tự động copy chép đè file `.md` trả lại vào `~/.kioku/users/telegram/memory/`.
- Tiêu hủy các database cũ (SQLite db, Chroma collection, Falkor graph).
- Kích hoạt lại LLM và Embedder để nạp/re-index lại 100% Vector DB, Knowledge Graph, và Keyword Index y như cũ.
