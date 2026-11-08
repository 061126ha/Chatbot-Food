
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# =====================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Đọc biến môi trường từ file .env
load_dotenv(dotenv_path=ENV_PATH, override=False)


# =====================================================
# 2. KHỞI TẠO GEMINI CLIENT
# =====================================================

def get_client():
    """
    Khởi tạo Gemini API thông qua OpenAI SDK.
    """

    # Đọc lại cấu hình API Key
    load_dotenv(dotenv_path=ENV_PATH, override=False)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "Không tìm thấy Gemini API Key trong file .env. "
            "Hãy kiểm tra lại OPENAI_API_KEY."
        )

    client = OpenAI(
        api_key=api_key,
        base_url=(
            "https://generativelanguage.googleapis.com/"
            "v1beta/openai/"
        ),
        timeout=30.0
    )

    return client


# =====================================================
# 3. KIỂM TRA CẤU HÌNH API
# =====================================================

def is_configured():
    """
    Kiểm tra Gemini API Key đã được cấu hình hay chưa.
    """

    load_dotenv(dotenv_path=ENV_PATH, override=False)

    return bool(
        os.getenv("OPENAI_API_KEY", "").strip()
    )


# =====================================================
# 4. SINH CÂU TRẢ LỜI BẰNG GEMINI
# =====================================================

def generate_answer(question, context):
    """
    Nhận câu hỏi và dữ liệu RAG,
    gửi đến Gemini để tạo câu trả lời.

    Tương thích với rag.py:
        generate_answer(query, context)
    """

    # Lấy tên model Gemini
    model = os.getenv(
        "OPENAI_MODEL",
        "gemini-2.5-flash"
    ).strip() or "gemini-2.5-flash"

    # Khởi tạo client
    client = get_client()

    # Gửi yêu cầu đến Gemini
    response = client.chat.completions.create(
        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý AI tư vấn món ăn Việt Nam. "

                    "Trả lời bằng tiếng Việt, "
                    "ngắn gọn, rõ ràng và hữu ích. "

                    "Chỉ sử dụng thông tin có trong dữ liệu "
                    "RAG được cung cấp. "

                    "Không tự bịa giá, địa chỉ, nguyên liệu "
                    "hoặc thông tin món ăn. "

                    "Nếu dữ liệu không đủ để trả lời, "
                    "hãy nói rõ là chưa có thông tin."
                )
            },

            {
                "role": "user",
                "content": (
                    f"Dữ liệu món ăn đã truy xuất:\n"
                    f"{context}\n\n"

                    f"Câu hỏi của người dùng:\n"
                    f"{question}\n\n"

                    "Hãy phân tích dữ liệu và đưa ra "
                    "lời tư vấn phù hợp."
                )
            }
        ],

        temperature=0.3
    )

    # Nhận nội dung phản hồi
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(
            "Gemini không trả về nội dung."
        )

    return content.strip()
