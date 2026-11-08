from llm_openai import generate_answer
import re
import unicodedata
from pathlib import Path
import os

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "vector_db"
COLLECTION_NAME = "food_collection"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def normalize(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d")


class FoodRAG:
    def __init__(self):
        # app.py dùng hai thuộc tính này để hiển thị trạng thái OpenAI.
        self.llm_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())
        self.llm_error = None
        if not DB_DIR.exists():
            raise FileNotFoundError(
                f"Chưa có thư mục Vector DB: {DB_DIR}. "
                "Hãy chạy: python embedding_food.py"
            )

        self.model = SentenceTransformer(MODEL_NAME)
        self.client = chromadb.PersistentClient(path=str(DB_DIR))

        try:
            self.collection = self.client.get_collection(COLLECTION_NAME)
        except Exception as exc:
            raise RuntimeError(
                "Không mở được collection 'food_collection'. "
                "Vector DB có thể chưa được tạo hoặc không tương thích. "
                "Hãy chạy lại: python embedding_food.py"
            ) from exc

        count = self.collection.count()
        if count == 0:
            raise RuntimeError(
                "Vector DB đang rỗng. Hãy chạy lại: python embedding_food.py"
            )

        metadata = self.collection.metadata or {}
        stored_model = metadata.get("embedding_model")
        if stored_model and stored_model != MODEL_NAME:
            raise RuntimeError(
                "Model embedding trong Vector DB không khớp với model truy vấn. "
                "Hãy tạo lại DB bằng: python embedding_food.py"
            )

        self.count = count

    def parse_query(self, query):
        q = normalize(query)
        filters = {"district": None, "max_price": None, "min_price": None}

        districts = [
            "bac tu liem", "ba dinh", "cau giay", "hai ba trung",
            "hoai duc", "hoan kiem", "hoang mai", "ha dong",
            "long bien", "nam tu liem", "thanh tri", "thanh xuan",
            "tay ho", "dong da"
        ]
        for district in districts:
            if district in q:
                filters["district"] = district
                break

        # Hỗ trợ: dưới 80k, tối đa 100 nghìn, dưới 1 triệu...
        match = re.search(
            r"(?:duoi|<=|khong qua|toi da|tam|khoang)\s*"
            r"(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu|m)?",
            q,
        )
        if match:
            number = float(match.group(1).replace(",", "."))
            unit = match.group(2) or ""
            if unit in ("k", "nghin", "ngan"):
                number *= 1000
            elif unit in ("trieu", "m"):
                number *= 1_000_000
            elif number < 1000:
                number *= 1000

            if any(term in q for term in ("duoi", "<=", "khong qua", "toi da")):
                filters["max_price"] = number

        return filters

    def search(self, query, top_k=5):
        if not str(query).strip():
            return self.parse_query(query), []

        filters = self.parse_query(query)
        vector = self.model.encode(
            [query], normalize_embeddings=True
        ).tolist()

        # Lấy nhiều ứng viên hơn top_k để bộ lọc khu vực/giá không làm hụt kết quả.
        candidate_count = min(max(top_k * 10, 30), self.count)
        raw = self.collection.query(
            query_embeddings=vector,
            n_results=candidate_count,
            include=["documents", "metadatas", "distances"],
        )

        results = []
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        for index, food_id in enumerate(ids):
            md = metadatas[index] or {}
            price = md.get("gia_khuyen_mai")
            if price is None:
                price = md.get("gia")

            district_ok = True
            price_ok = True

            if filters["district"]:
                district_ok = (
                    normalize(md.get("quan_huyen", "")) == filters["district"]
                )

            if filters["max_price"] is not None:
                # Món không có giá không được xem là đáp ứng điều kiện giá.
                price_ok = price is not None and float(price) <= filters["max_price"]

            if district_ok and price_ok:
                results.append({
                    "id": food_id,
                    "ten_mon": md.get("ten_mon", ""),
                    "quan_huyen": md.get("quan_huyen", ""),
                    "dia_chi": md.get("dia_chi", ""),
                    "gia": md.get("gia"),
                    "gia_khuyen_mai": md.get("gia_khuyen_mai"),
                    "distance": distances[index] if index < len(distances) else None,
                    "document": docs[index] if index < len(docs) else "",
                })

            if len(results) >= top_k:
                break

        return filters, results

    def answer(self, query, results, filters):
        """Tạo câu trả lời bằng OpenAI trên context RAG; dự phòng nếu API lỗi."""
        if not results:
            self.llm_error = None
            return (
                "Mình chưa tìm thấy món phù hợp. "
                "Bạn có thể thử khu vực khác hoặc nới rộng mức giá."
            )

        # Luôn chuẩn bị câu trả lời dự phòng từ dữ liệu đã truy xuất.
        lines = ["Mình tìm thấy các món phù hợp với nhu cầu của bạn:", ""]
        for index, item in enumerate(results, 1):
            price = (
                item.get("gia_khuyen_mai")
                if item.get("gia_khuyen_mai") is not None
                else item.get("gia")
            )
            price_text = (
                f"{price:,.0f}đ"
                if isinstance(price, (int, float))
                else "Chưa cập nhật giá"
            )
            lines.append(
                f"{index}. {item.get('ten_mon', 'Chưa có tên')} — {price_text}"
            )
            lines.append(
                f"   📍 {item.get('dia_chi') or 'Chưa cập nhật địa chỉ'}"
            )
        fallback_answer = "\n".join(lines)

        if not self.llm_enabled:
            self.llm_error = "Chưa cấu hình OPENAI_API_KEY trong file .env."
            return fallback_answer

        context_parts = []
        for item in results:
            price = (
                item.get("gia_khuyen_mai")
                if item.get("gia_khuyen_mai") is not None
                else item.get("gia")
            )
            context_parts.append(
                f"Tên món: {item.get('ten_mon', '')}; "
                f"Quận/huyện: {item.get('quan_huyen', '')}; "
                f"Địa chỉ: {item.get('dia_chi', '')}; "
                f"Giá: {price if price is not None else 'Chưa cập nhật'}; "
                f"Thông tin: {item.get('document', '')}"
            )
        context = "\n".join(context_parts)

        try:
            answer_text = generate_answer(query, context)
            if not answer_text or not str(answer_text).strip():
                raise RuntimeError("OpenAI trả về nội dung rỗng.")
            self.llm_error = None
            return str(answer_text).strip()
        except Exception as exc:
            self.llm_error = f"{type(exc).__name__}: {exc}"
            return fallback_answer
