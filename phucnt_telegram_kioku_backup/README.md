# Telegram Kioku Backup

**Lý do Backup:**
Mọi dữ liệu cốt lõi (Single Source of Truth) của Kioku Agent thông qua Telegram Bot đều được lưu dưới dạng file Markdown. Các database khác (ChromaDB, FalkorDB, SQLite) chỉ là cache phục vụ tìm kiếm. Do đó, trước khi refactor hoặc nâng cấp hệ thống lớn, chỉ cần backup thư mục Markdown này là có thể đảm bảo an toàn 100% dữ liệu gốc, không lo mất mát lịch sử trò chuyện hay kiến thức.

**Cách 1: Khôi phục Toàn Bộ (Full Restore - Chạy `restore.py`)**

Đây là cách dùng khi anh muốn chuyển đổi máy, khởi tạo lại từ một hệ thống database trắng trơn hoặc bị corrupt toàn bộ DB.
1. Đảm bảo OpenClaw Gateway/Bot đang dừng tạm thời (hoặc ít nhất không thao tác).
2. Chạy lệnh (từ thư mục gốc `kioku-mcp`):

```bash
KIOKU_USER_ID=telegram uv run python phucnt_telegram_kioku_backup/restore.py
```

*Script này sẽ làm 3 việc khốc liệt:*
- Tự động copy chép đè CÁC file `.md` trả lại vào `~/.kioku/users/telegram/memory/`.
- **Tiêu hủy sạch sẽ các database cũ** (SQLite db, Chroma collection, Falkor graph).
- Quét qua TẤT CẢ các ngày, kích hoạt LLM và Embedder để nạp/re-index lại 100% dữ liệu vào DB.

---

**Cách 2: Khôi phục Cục Bộ (Incremental Restore - Chạy `restore_today.py`)**

Dùng khi hệ thống anh đang chạy ngon lành nhưng vô tình có 1 dịch vụ bị tắt (ví dụ Docker tắt khiến Ollama/FalkorDB không chạy), khiến dữ liệu của **Ngay Hôm Nay (2026-02-23)** bị "miss" ở tầng Vector/Graph, trong khi file Markdown (Single Source Of Truth) trên ổ cứng vẫn ghi nhận.

1. Hãy bật lại các công cụ cần thiết (Docker, Ollama, FalkorDB).
2. Chạy lệnh (từ thư mục gốc `kioku-mcp`):

```bash
KIOKU_USER_ID=telegram uv run python phucnt_telegram_kioku_backup/restore_today.py
```

*Khác biệt:* Script này **KHÔNG xóa DB cũ!** Nó chỉ đọc riêng mỗi file Markdown của ngày hôm nay (`2026-02-23.md`), gọi LLM và tự động Re-index (Upsert) những data bị thiếu để trám lỗ hổng vào hệ thống Vector/Knowledge Graph một cách an toàn nhất. Mọi Cấu trúc và Knowledge Graph của những ngày trước sẽ không hề bị ảnh hưởng.
