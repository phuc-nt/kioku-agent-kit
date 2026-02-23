# Kioku MCP — Restructure Plan Phase 7

## Mục tiêu (Objectives)
Tập trung nâng cấp chất lượng dữ liệu và khả năng truy vết của hệ thống ở cấp độ ngữ nghĩa sâu hơn. Phase 7 giải quyết hai bài toán kinh điển trong phân tích dữ liệu (Data Analytics) và Đồ thị tri thức (Knowledge Graph):
1. **Bi-temporal Modeling (Mô hình lưỡng cực thời gian)**
2. **Entity Resolution & Disambiguation (Đồng nhất & Khử thực thể trùng lặp)**

---

## 1. Bi-temporal Time: Event Time vs Processing Time

### Khái niệm
Trong thế giới dữ liệu, có 2 trục thời gian cực kì quan trọng:
- **Processing Time (Transaction Time):** Thời điểm hệ thống ghi nhận sự việc. Trong Kioku, đây chính là trường `time` (ví dụ `2026-02-23T22:42:09`) khi người dùng gõ phím.
- **Event Time (Valid Time):** Thời điểm sự việc THỰC SỰ xảy ra ngoài đời thực. Ví dụ, câu nói *"Sài Gòn, 8.7.2024, con trai 3 tuổi..."* thì Event Time là `2024-07-08`.

**Tại sao cần thiết?**
Hiện tại mọi `timeline` của Kioku được xếp theo Processing Time. Điều này tạo ra một "Nhật ký hồi tưởng" (biết được hôm nay mình đã nhớ về chuyện gì), nhưng KHÔNG vẽ ra được "Nhật ký cuộc đời" (tuổi thơ - lúc 22 tuổi - lúc 30 tuổi). 

### Kế hoạch Triển khai (Implementation)
1. **Cập nhật Markdown Frontmatter:**
   Thêm trường `event_time: "YYYY-MM-DD"` (Optional).
   ```yaml
   ---
   time: "2026-02-23T22:47:14+07:00"
   event_time: "2024-07-08"
   mood: "loving"
   tags: ['siblings']
   ---
   ```
2. **Cập nhật AI Extractor Prompt:**
   Dạy LLM tự động trích xuất `event_time` từ nội dung văn bản (nếu có nhắc đến "năm 2020", "hôm qua", "tuổi 22", "8/7/2024"). 
   Cần cẩn thận prompt để xử lý Relative Time ("hôm qua") dựa vào Processing Time hiện tại.
3. **Cập nhật DB Schema:**
   - **SQLite:** Thêm cột `event_time` vào bảng `memories`.
   - **ChromaDB:** Thêm metadata `event_time` vào các payload vector.
   - **FalkorDB (Knowledge Graph):** Cập nhật các Node và Edge để mang thêm thuộc tính `event_time` thay vì chỉ lưu `processing_time`.
   - **Tool `timeline`:** Mở rộng tham số để cho phép người dùng muốn xem Timeline theo `processing_time` hay `event_time`.

---

## 2. Entity Resolution & Disambiguation (Đồng nhất Thực thể)

### Bài toán
Ngôn ngữ tự nhiên rất đa dạng: `Mẹ`, `Mom`, `Mother`, `Bà ngoại`, `Bà Vinh`... về mặt ngữ nghĩa đều trỏ về 1 người. Cảm xúc (Mood): `vui`, `happy`, `cheerful` thực chất là 1.
Nếu Knowledge Graph trích xuất mỗi từ thành 1 Node riêng biệt, đồ thị sẽ bị phân mảnh gãy vụn (Fragmented), mất đi sức mạnh của mối quan hệ bắc cầu (`A -> B -> C`).

### Kế hoạch Triển khai (Implementation)

Cần áp dụng kỹ thuật **Entity Resolution (ER) & Node Merging**.

**Bảo lưu tính gốc (Raw) vs Tính đồng bộ (Normalized)**
Không nên xoá từ gốc của người dùng vì nó chứa sắc thái cảm xúc, nhưng trong DB cần "gom" lại.

*Giải pháp Đề xuất:*

1. **In-Prompt LLM Disambiguation (Dùng AI trên đường bay):**
   - **Cách làm:** Trước khi gọi LLM trích xuất Event (ClaudeExtractor), hệ thống sẽ Query (câu lệnh phụ) lấy danh sách Top 50 Entities đang tồn tại trong Graph của người dùng.
   - **Prompt:** *"Dưới đây là các thực thể đã biết: [Mẹ, Vy, Phong, Hùng]. Hãy ưu tiên sử dụng lại các Entity (Canonical Name) này nếu thực thể trong đoạn text thực chất là một"* (Ví dụ: gặp chữ `mom`, LLM tự trả về Entity name = `Mẹ`).

2. **Entity Alias (Gắn từ đồng nghĩa trong Đồ thị):**
   - Trường hợp không thể gom bằng LLM, thiết kế cấu trúc Graph linh hoạt hơn:
     `(Alias: "Mom") -[SAME_AS]-> (Entity: "Mẹ")`
   - Tuy nhiên cách này làm nặng Graph. Nên ưu tiên cách 1 (Merge Node từ lúc lưu).

3. **Mood & Tag Normalization:**
   - Các trường `mood` và `tags` trước khi insert vào Vector/SQLite nên được pass qua một lớp Vector Semantic Similarity nhỏ, hoặc Prompt gom nhóm. Ví dụ tự map `vui_vẻ` -> `happy`. Điều này giúp `get_life_patterns` chính xác tuyệt đối.

---

## 3. Universal Identifier: Nối kết O(1) về Văn bản gốc (Raw Text)

### Bài toán
Markdown tuy là Single Source of Truth (Sao lưu cực an toàn), nhưng việc Parse lại toàn bộ 1 file Markdown 500 lines chỉ để tìm lại 1 bằng chứng (Raw text evidence) là lãng phí tài nguyên (CPU, I/O) và gây tốn Token của LLM nếu đút cả file vào ngữ cảnh.

### Giải pháp (Implementation)
Dùng chính **SQLite làm Document Read-Store** hoàn hảo cho việc này với cơ chế Retrieval O(1). 
Thực chất, hệ thống hiện tại của Kioku ĐÃ CÓ sẵn một ID Độc nhất vô nhị (Universal ID) nhưng chưa tận dụng hết: Đó là trường **`content_hash`** (mã Hash SHA-256 sinh ra từ nội dung của từng block memory).

1. **SQLite (Keyword DB):** Đóng vai trò là **Primary Document Store**. Lưu trữ nội dung văn bản đầy đủ (raw text) và metadata hoàn chỉnh.
2. **Vector Store (ChromaDB):** Hiện đang dùng `content_hash` làm Vector ID. Sẽ giảm tải: không cần lặp lại raw text/metadata nặng trong ChromaDB nữa, chỉ lưu embedding và ID.
3. **Knowledge Graph (FalkorDB):** Cần bổ sung thêm properties `source_id: "mã_content_hash"` (khoá ngoại) vào các Edge liên kết (Relationship) trên đồ thị.
4. **Data Aggregation Layer (Kioku Service):** 
   - Bất cứ khi nào Agent tìm được một Vector khớp (từ ChromaDB), nó chỉ ném mảng Vector IDs ra.
   - Bất cứ khi nào lội theo Graph mà tóm được ID của một Relationship (từ FalkorDB).
   - **Tầng Backend (Service)** sẽ gom 1 mẻ ID này, chọc thẳng vào SQLite: `SELECT content, date, tags FROM memories WHERE content_hash IN (...)`.
   - Kết quả cuối cùng (Full text) được đắp thịt (Hydrated) và JSON-hóa hoàn chỉnh trước khi trả về cho Agent. (Bỏ qua hoàn toàn việc chạm vào file Markdown vật lý hay bắt Agent phải tự gọi tool).

=> **Lợi ích kép:** Backup của Text (Markdown) + Tốc độ Vận hành của Database (SQLite + ID).

---

## Checklist Hành động (Task List)
- [ ] Bổ sung trường `event_time` vào `kioku.storage.markdown`, `extractor.py`.
- [ ] Cập nhật Schema SQLite, ChromaDB Metadata và thuộc tính của Knowledge Graph theo `event_time`.
- [ ] Khắc trường `source_id` (chính là chuỗi `content_hash`) vào các Edge trong FalkorDB.
- [ ] Tối ưu ChromaDB: Bỏ lặp lại việc lưu Raw Text trong Chroma metadata/document nếu không cần thiết.
- [ ] Tuỳ biến `kioku timeline` command để hỗ trợ sort theo `event_time`.
- [ ] Nâng cấp Prompt trích xuất: Cung cấp `context_entities` và ép LLM thực hiện Entity Resolution (giải quyết đại từ/đồng nghĩa).
- [ ] Cấu trúc lại Tầng Service (KiokuService): Ngầm tự động thực hiện map ID từ ChromaDB/FalkorDB -> `SQLite.get_by_ids()` để đắp (hydrate) Raw Text trả về Agent trong cùng 1 nhịp Tool Call.
- [ ] Cập nhật bài Test đảm bảo hệ thống.
