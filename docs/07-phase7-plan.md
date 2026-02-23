# Kioku MCP — Restructure Plan Phase 7

## Mục tiêu (Objectives)
Tập trung nâng cấp chất lượng dữ liệu và khả năng truy vết của hệ thống ở cấp độ ngữ nghĩa sâu hơn. Phase 7 giải quyết ba bài toán kinh điển trong phân tích dữ liệu (Data Analytics), Đồ thị tri thức (Knowledge Graph) và Truy Xuất Tăng Cường (RAG):
1. **Bi-temporal Modeling (Mô hình lưỡng cực thời gian)**
2. **Entity Resolution & Disambiguation (Đồng nhất & Khử thực thể trùng lặp)**
3. **Universal Identifier & O(1) Raw Text Retrieval (Truy xuất nguyên bản siêu tốc)**

---

## 1. Bi-temporal Time: Event Time vs Processing Time

### Bài toán
Trong thế giới dữ liệu, có 2 trục thời gian cực kì quan trọng:
- **Processing Time (Transaction Time):** Thời điểm hệ thống ghi nhận sự việc. Trong Kioku, đây chính là trường `time` hiện tại khi người dùng gõ phím.
- **Event Time (Valid Time):** Thời điểm sự việc THỰC SỰ xảy ra ngoài đời thực.

Hiện tại mọi `timeline` của Kioku được xếp theo Processing Time. Điều này chỉ tạo ra một "Nhật ký hồi tưởng" (biết được hôm nay mình đã nhớ về chuyện gì), nhưng KHÔNG vẽ ra được "Nhật ký cuộc đời" (diễn biến sự kiện theo trục thời gian thực).

### Kế hoạch Triển khai (Implementation)
1. **Cập nhật Markdown Frontmatter:** Thêm trường `event_time: "YYYY-MM-DD"` (Optional).
2. **Cập nhật AI Extractor Prompt:** Dạy lại LLM (`ClaudeExtractor`) tự động phân tích Relative Time (ví dụ: "tuổi 22", "hôm qua", "năm ngoái") kết hợp với Processing Time để nội suy và điền giá trị Date chuẩn hóa vào `event_time` lúc phân tách các block văn bản.
3. **Cập nhật DB Schema:**
   - **SQLite:** Thêm cột `event_time` vào bảng `memories`.
   - **ChromaDB:** Thêm metadata `event_time` vào các cấu trúc payload.
   - **FalkorDB (Knowledge Graph):** Cập nhật thuộc tính của Node và Edge (Relationship) để lưu `event_time` thay vì chỉ lưu `processing_time`.

---

## 2. Entity Resolution & Disambiguation (Đồng nhất Thực thể)

### Bài toán
Ngôn ngữ tự nhiên rất đa dạng: `Mẹ`, `Mom`, `Mother`, `Bà Vinh`... về mặt ngữ nghĩa đều trỏ về 1 người. Nếu Knowledge Graph trích xuất mỗi từ thành 1 Node riêng biệt, đồ thị sẽ bị phân mảnh gãy vụn (Fragmented), làm suy yếu khả năng suy luận quan hệ bắc cầu (`A -> B -> C`). Quá trình xử lý cảm xúc (`mood`) hoặc thẻ tag (`tags`) cũng gặp vấn đề tương tự nếu không được nhóm lặp.

### Kế hoạch Triển khai (Implementation)
Áp dụng **In-Flight LLM Disambiguation (Giải quyết trên đường bay)** để tránh đẻ thêm Node dư thừa.

1. **Context-Aware Extraction:**
   - Trước khi gọi LLM (Claude) trích xuất Entity, hệ thống truy vấn siêu tốc lấy ra mạng lưới các Canonical Entities (Danh sách tên thực thể chuẩn) đang tồn tại phổ biến trong Graph của user.
   - Đưa danh sách này vào Prompt: *"Dưới đây là các thực thể đã biết. Hãy ưu tiên sử dụng lại các Entity (Canonical Name) này nếu thực thể trong đoạn text thực chất là một, thay vì tạo tên mới."* (Coreference Resolution).
2. **Mood & Tag Normalization:**
   - Đưa các trường `mood` và `tags` đi qua bộ Semantic Similarity nhẹ. Ví dụ LLM/Hệ thống tự map `vui_vẻ` -> `happy` nhằm quy chuẩn lại cho chức năng Life Patterns chính xác 100%.

---

## 3. Universal Identifier: Nối kết O(1) về Văn bản gốc (Raw Text)

### Bài toán
Markdown tuy là Single Source of Truth (Sao lưu cực an toàn), nhưng việc Service phải Parse lại toàn bộ 1 file Markdown lớn (hàng trăm dòng) chỉ để đắp thịt 1 bằng chứng (evidence raw text) là rất lãng phí CPU, I/O và Token LLM.

### Kế hoạch Triển khai (Implementation)
Quy hoạch lại hệ thống Database thành mô hình **Standardized Retrieval Pipeline**: Dùng SQLite làm trung tâm dữ liệu toàn văn và sử dụng `content_hash` làm Universal Identifier (ID Duy nhất).

1. **SQLite (Keyword DB):** Đóng vai trò là **Primary Document Store**. Nơi lưu trữ duy nhất và đầy đủ nguyên văn văn bản (raw text), ID tự tăng, cùng chuỗi hash định danh `content_hash`. Chuyển tốc độ truy xuất thành O(1).
2. **Ví trí của Vector Store (ChromaDB):** Sẽ giảm tải hoàn toàn! Không lặp lại việc lưu raw text hay metadata nặng. ChromaDB chỉ dùng để chấm điểm độ tương đồng vector, sau đó ném lại mảng the ID (`content_hash`).
3. **FalkorDB (Knowledge Graph):** Buộc phải bổ sung thêm tham số khoá ngoại `source_id: "<mã_content_hash>"` vào các Edge liên kết trên đồ thị.
4. **Data Aggregation Layer (Tầng Service gom dữ liệu):** 
   - Không bắt Agent tự đi đọc văn bản.
   - Khi Service nhận lại các mảng ID (từ ChromaDB hoặc FalkorDB), nó sẽ chọc 1 phát vào SQLite: `SELECT content, date, tags FROM memories WHERE content_hash IN (...)`.
   - Kết quả trả lại cho Agent sẽ luôn là dạng JSON đã được Hydrate (đắp thịt) toàn bộ văn bản gốc liên quan sâu nhất. Định dạng đồng nhất và tốc độ mili-giây.

---

## 4. Tác Động Đến Kioku MCP Tools (Impact on Tools & AGENTS.md)
Việc cấu trúc lại backend này sẽ trực tiếp làm thay đổi hành vi và hướng dẫn của các công cụ sau:

1. **`timeline` Tool:**
   - **Tham số thay đổi:** Sẽ có thêm cờ `--sort-by` (hoặc `sort_type`), nhận giá trị `processing_time` (mặc định) hoặc `event_time`.
   - **Hướng dẫn cho Agent:** Phân biệt rõ tình huống. Khi User hỏi "Nhóm các sự kiện cuộc đời tôi từ nhỏ tới lớn" => Agent phải tự biết gõ cờ `--sort-by event_time`. Còn "Hôm qua tôi đã nhảm gì" => `--sort-by processing_time`.
2. **`save` Tool:**
   - **Tác động ngầm:** Sẽ chạy chậm hơn một chút vì có thêm bước Context-Aware LLM resolution (lấy danh sách tên Entity cũ). Quá trình ghi nhận sẽ tạo ra các Network Graph tập trung và ít phân tán hơn.
   - Không thay đổi argument đầu vào.
3. **`search` / `explain` / `recall` Tools:**
   - **Payload trả về thay đổi:** Tốc độ trả về sẽ nhanh hơn, nhưng lượng text sẽ chính xác tuyệt đối từng câu/đoạn nhờ khả năng trích xuất O(1) từ SQLite, chứ không đọc tràn lan từ file Markdown hay Chroma chunk nữa. 
   - Danh sách "Evidence" ở đồ thị giờ đã luôn kèm Raw Text cực kì hoàn hảo.
   - Các Agent không cần sử dụng trick `kioku read` để đọc Raw Markdown như ngày trước nữa, vì mọi kết quả Graph giờ đã nhúng Full-text ở cấp độ block.

---

## 5. Checklist Hành động (Task List)
- [ ] Bổ sung cơ chế parse/validate `event_time` vào `kioku.storage.markdown` và prompt `extractor.py`.
- [ ] Cập nhật Schema SQLite để chứa cột `event_time`.
- [ ] Xoá bỏ việc dư thừa raw document trong metadata của ChromaDB. Thêm filter `event_time`.
- [ ] Khắc trường `source_id` (chính là chuỗi `content_hash`) và thuộc tính `event_time` vào các Edge/Node trong FalkorDB.
- [ ] Nâng cấp Prompt trích xuất: Cung cấp `context_entities` và ép Entity Resolution (giải quyết đại từ/đồng nghĩa).
- [ ] Cấu trúc lại `KiokuService`: Các hàm search graph/vector hiện tại sẽ chỉ thu thập ID, sau đó Map qua `SQLite.get_by_ids()` để trả JSON nguyên bản cho Agent.
- [ ] Cập nhật Tham số CLI CLI/MCP cho lệnh `timeline`.
- [ ] Cập nhật Bài Test cho mọi Module.
