import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

from rag import FoodRAG

st.set_page_config(
    page_title="Food AI - Trợ lý tư vấn món ăn",
    page_icon="🍜",
    layout="wide",
)

st.title("🍜 Food AI — Trợ lý tư vấn món ăn")
st.caption(
    "Tìm kiếm món ăn bằng Sentence Transformers + ChromaDB "
    "và tạo câu trả lời bằng OpenAI."
)


@st.cache_resource(show_spinner="Đang tải model embedding và Vector DB...")
def load_rag():
    return FoodRAG()


try:
    rag = load_rag()
except Exception as exc:
    st.error("Không khởi tạo được Food RAG / Vector DB.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.markdown(
        """
Kiểm tra các mục sau:
1. Đang chạy lệnh tại thư mục có `app.py`.
2. Thư mục `vector_db` đã được tạo bằng `embedding_food.py`.
3. Đã cài thư viện trong `requirements.txt`.
        """
    )
    st.stop()


with st.sidebar:
    st.header("⚙️ Trạng thái hệ thống")
    st.caption(f"Vector DB: {rag.count} món ăn")

    if rag.llm_enabled:
        st.success("OpenAI LLM: Đã cấu hình API key")
        st.caption("Model: OPENAI_MODEL trong file .env")
    else:
        st.warning("OpenAI LLM: Chưa cấu hình API key")
        st.caption("Đang dùng câu trả lời dự phòng từ RAG.")

    st.divider()
    st.header("🔎 Bộ lọc")
    st.write("Nhập khu vực và mức giá trực tiếp trong câu hỏi.")
    top_k = st.slider("Số món tối đa", min_value=1, max_value=10, value=5)

    if st.button("🗑️ Xóa hội thoại"):
        st.session_state.messages = []
        st.rerun()


if "messages" not in st.session_state:
    st.session_state.messages = []


def show_results(results, show_distance=False):
    for item in results:
        price = (
            item.get("gia_khuyen_mai")
            if item.get("gia_khuyen_mai") is not None
            else item.get("gia")
        )
        price_text = (
            f"{price:,.0f}đ"
            if isinstance(price, (int, float))
            else "Chưa cập nhật"
        )
        st.write(
            f"**{item.get('ten_mon', 'Chưa có tên')}** — "
            f"{price_text} — {item.get('quan_huyen', '')}"
        )
        st.caption(item.get("dia_chi", "Chưa cập nhật địa chỉ"))
        if show_distance and item.get("distance") is not None:
            st.caption(f"Vector distance: {item['distance']:.4f}")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("results"):
            show_results(message["results"])


query = st.chat_input("Ví dụ: Tôi muốn ăn món ở Cầu Giấy dưới 80k")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Đang tìm món ăn và tạo câu trả lời..."):
                filters, results = rag.search(query, top_k=top_k)
                answer = rag.answer(query, results, filters)

            st.markdown(answer)

            if rag.llm_error:
                st.warning(
                    "OpenAI chưa được sử dụng thành công. "
                    "Ứng dụng đã chuyển sang câu trả lời dự phòng từ RAG."
                )
                st.code(rag.llm_error)

            if results:
                st.markdown("### 📚 Dữ liệu RAG đã truy xuất")
                with st.expander("Xem chi tiết kết quả"):
                    show_results(results, show_distance=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "results": results,
            })

        except Exception as exc:
            st.error("Có lỗi trong quá trình tìm kiếm hoặc tạo câu trả lời.")
            st.code(f"{type(exc).__name__}: {exc}")
