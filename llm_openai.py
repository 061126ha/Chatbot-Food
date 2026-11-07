import os
from openai import OpenAI


class OpenAIAnswerer:
    """Gọi OpenAI để diễn đạt kết quả truy xuất từ Food RAG."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.client = (
            OpenAI(api_key=self.api_key, timeout=30.0)
            if self.api_key
            else None
        )

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def generate_answer(self, query: str, results: list, filters: dict) -> str:
        if not self.client:
            raise RuntimeError("Thiếu OPENAI_API_KEY trong file .env.")

        # Chỉ gửi những trường cần thiết, không gửi dữ liệu thừa.
        food_lines = []
        for index, item in enumerate(results, 1):
            price = (
                item.get("gia_khuyen_mai")
                if item.get("gia_khuyen_mai") is not None
                else item.get("gia")
            )
            price_text = (
                f"{price:,.0f} VND"
                if isinstance(price, (int, float))
                else "Chưa có giá"
            )
            food_lines.append(
                f"{index}. Tên: {item.get('ten_mon', '')}; "
                f"Khu vực: {item.get('quan_huyen', '')}; "
                f"Địa chỉ: {item.get('dia_chi', '')}; "
                f"Giá: {price_text}; "
                f"Thông tin: {item.get('document', '')}"
            )

        context = "\n".join(food_lines)

        system_prompt = """
Bạn là trợ lý tư vấn món ăn của dự án Food AI.
Chỉ sử dụng thông tin món ăn được cung cấp trong CONTEXT.
Không tự bịa tên món, giá, địa chỉ, khuyến mãi hoặc tình trạng còn bán.
Trả lời bằng tiếng Việt tự nhiên, ngắn gọn, dễ đọc.
Nếu dữ liệu thiếu, hãy nói rõ là chưa có thông tin.
Đề xuất tối đa 3-5 món phù hợp nhất và giải thích ngắn gọn.
"""

        user_prompt = f"""
Câu hỏi của người dùng:
{query}

Bộ lọc đã nhận diện:
{filters}

CONTEXT — các món được truy xuất từ cơ sở dữ liệu:
{context}

Hãy tư vấn dựa đúng trên CONTEXT.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        answer = response.choices[0].message.content
        if not answer:
            raise RuntimeError("OpenAI trả về nội dung rỗng.")
        return answer.strip()
