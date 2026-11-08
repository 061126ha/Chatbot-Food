import argparse
import json
import math
import shutil
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / "data_food(4).json"
DB_DIR = BASE_DIR / "vector_db"
COLLECTION_NAME = "food_collection"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 128


def clean_text(value):
    """Convert a JSON value to safe, non-null text."""
    if value is None:
        return ""
    return str(value).strip()


def safe_number(value):
    """Return a finite float, or None when the value is missing/invalid."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def load_foods():
    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy dữ liệu: {JSON_FILE}\n"
            "Hãy đặt data_food(4).json cùng thư mục với embedding_food.py."
        )

    with JSON_FILE.open("r", encoding="utf-8") as file:
        foods = json.load(file)

    if not isinstance(foods, list):
        raise ValueError("File JSON phải chứa một danh sách (list) món ăn.")

    valid_foods = []
    seen_ids = set()
    for index, food in enumerate(foods):
        if not isinstance(food, dict):
            print(f"Bỏ qua dòng {index + 1}: dữ liệu không phải object.")
            continue
        if food.get("id") is None:
            print(f"Bỏ qua dòng {index + 1}: thiếu id.")
            continue

        food_id = str(food["id"]).strip()
        if not food_id or food_id in seen_ids:
            print(f"Bỏ qua dòng {index + 1}: id rỗng hoặc bị trùng ({food_id}).")
            continue

        seen_ids.add(food_id)
        valid_foods.append(food)

    if not valid_foods:
        raise ValueError("Không có món ăn hợp lệ để tạo Vector DB.")

    return valid_foods


def build_document(food):
    ten_mon = clean_text(food.get("ten_mon"))
    quan_huyen = clean_text(food.get("quan_huyen"))
    dia_chi = clean_text(food.get("dia_chi"))
    gia = safe_number(food.get("gia"))
    gia_km = safe_number(food.get("gia_khuyen_mai"))

    gia_text = f"{gia:,.0f}" if gia is not None else "chưa cập nhật"
    gia_km_text = f"{gia_km:,.0f}" if gia_km is not None else "không có"

    document = (
        f"Tên món: {ten_mon}. Khu vực: {quan_huyen}. Địa chỉ: {dia_chi}. "
        f"Giá: {gia_text} đồng. Giá khuyến mãi: {gia_km_text} đồng."
    )

    metadata = {
        "ten_mon": ten_mon or "Chưa có tên",
        "quan_huyen": quan_huyen,
        "dia_chi": dia_chi,
    }
    if gia is not None:
        metadata["gia"] = gia
    if gia_km is not None:
        metadata["gia_khuyen_mai"] = gia_km

    return str(food["id"]).strip(), document, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Tạo lại ChromaDB từ data_food(4).json"
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Không xóa thư mục vector_db trước khi ghi (chỉ dùng khi DB hiện tại tương thích).",
    )
    args = parser.parse_args()

    foods = load_foods()
    print(f"Đọc được {len(foods)} món ăn.")
    print(f"Model embedding: {MODEL_NAME}")

    ids, documents, metadatas = [], [], []
    for food in foods:
        food_id, document, metadata = build_document(food)
        ids.append(food_id)
        documents.append(document)
        metadatas.append(metadata)

    print("Đang tải model embedding. Lần đầu có thể cần Internet để tải model...")
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(
        documents,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    if len(vectors) != len(ids):
        raise RuntimeError("Số vector không khớp số món ăn.")

    # Mặc định tạo DB sạch để tránh lỗi schema/version từ ChromaDB cũ.
    if DB_DIR.exists() and not args.keep_existing:
        print(f"Đang xóa Vector DB cũ: {DB_DIR}")
        shutil.rmtree(DB_DIR)

    DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_DIR))

    # Nếu collection đã tồn tại, xóa collection cũ để tránh trộn model/vector cũ.
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": MODEL_NAME,
            "embedding_dimension": len(vectors[0]),
        },
    )

    for start in range(0, len(ids), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(ids))
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=vectors[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"Đã ghi {end}/{len(ids)} món.")

    print(f"\nHOÀN TẤT: Vector DB có {collection.count()} món.")
    print(f"Đường dẫn DB: {DB_DIR}")


if __name__ == "__main__":
    main()
