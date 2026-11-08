import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Đọc cấu hình từ file .env của chính dự án.
load_dotenv(dotenv_path=ENV_PATH, override=False)


def get_client():
    # Đọc tại thời điểm gọi để tránh giữ API key cũ trong bộ nhớ module.
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Không tìm thấy OPENAI_API_KEY trong file .env. "
            "Hãy điền API key hợp lệ rồi khởi động lại ứng dụng."
        )
    return OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def generate_answer(question, context):
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý tư vấn món ăn Việt Nam. "
                    "Trả lời bằng tiếng Việt, ngắn gọn và hữu ích. "
                    "Chỉ sử dụng thông tin có trong dữ liệu RAG được cung cấp. "
                    "Không tự bịa giá, địa chỉ, nguyên liệu hoặc tình trạng còn bán. "
                    "Nếu dữ liệu không có câu trả lời, hãy nói rõ là chưa có thông tin."
                ),
            },
            {
                "role": "user",
                "content": f"Dữ liệu món ăn đã truy xuất:\n{context}\n\nCâu hỏi:\n{question}",
            },
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI không trả về nội dung.")
    return content.strip()
