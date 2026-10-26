
import json
import chromadb
from sentence_transformers import SentenceTransformer

# ==========================================
# 1. DOC DU LIEU JSON
# ==========================================

JSON_FILE = "data_food(4).json"

with open(JSON_FILE, "r", encoding="utf-8") as file:
    foods = json.load(file)

print("So mon an doc duoc:", len(foods))


# ==========================================
# 2. TAI MO HINH EMBEDDING
# ==========================================

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

model = SentenceTransformer(MODEL_NAME)


# ==========================================
# 3. CHUYEN DU LIEU THANH VAN BAN
# ==========================================

ids = []
documents = []
metadatas = []

for food in foods:
    food_id = str(food["id"])
    ten_mon = str(food.get("ten_mon", ""))
    quan_huyen = str(food.get("quan_huyen", ""))
    dia_chi = str(food.get("dia_chi", ""))

    gia = food.get("gia")
    gia_khuyen_mai = food.get("gia_khuyen_mai")

    # Tao van ban mo ta mon an
    noi_dung = (
        f"Ten mon: {ten_mon}. "
        f"Quan huyen: {quan_huyen}. "
        f"Dia chi: {dia_chi}. "
    )

    if gia is not None:
        noi_dung += f"Gia goc: {gia} dong. "

    if gia_khuyen_mai is not None:
        noi_dung += (
            f"Gia khuyen mai: {gia_khuyen_mai} dong. "
        )

    ids.append(food_id)
    documents.append(noi_dung)

    # Metadata chi luu cac gia tri co du lieu
    metadata = {
        "ten_mon": ten_mon,
        "quan_huyen": quan_huyen,
        "dia_chi": dia_chi
    }

    if gia is not None:
        metadata["gia"] = float(gia)

    if gia_khuyen_mai is not None:
        metadata["gia_khuyen_mai"] = float(gia_khuyen_mai)

    metadatas.append(metadata)


# ==========================================
# 4. TAO VECTOR TU VAN BAN
# ==========================================

print("Dang tao vector...")

vectors = model.encode(
    documents,
    batch_size=32,
    show_progress_bar=True,
    normalize_embeddings=True
).tolist()


# ==========================================
# 5. TAO VECTOR DATABASE
# ==========================================

client = chromadb.PersistentClient(
    path="./vector_db"
)

collection = client.get_or_create_collection(
    name="food_collection",
    metadata={"hnsw:space": "cosine"}
)


# ==========================================
# 6. LUU DU LIEU VAO CHROMADB
# ==========================================

# Chia thanh cac lo nho de luu
batch_size = 200

for start in range(0, len(ids), batch_size):
    end = start + batch_size

    collection.upsert(
        ids=ids[start:end],
        documents=documents[start:end],
        embeddings=vectors[start:end],
        metadatas=metadatas[start:end]
    )

    print(f"Da xu ly {min(end, len(ids))}/{len(ids)} mon")


# ==========================================
# 7. KIEM TRA KET QUA
# ==========================================

print("\nEMBEDDING HOAN TAT!")
print("Tong so mon trong JSON:", len(foods))
print("Tong so mon trong Vector DB:", collection.count())
print("Thu muc luu Vector DB: ./vector_db")
