
import chromadb
from sentence_transformers import SentenceTransformer

# Tai mo hinh embedding
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Ket noi vector database da luu
client = chromadb.PersistentClient(path="./vector_db")

collection = client.get_collection(
    name="food_collection"
)

# Nhap cau hoi
question = input("Ban muon tim mon an gi? ")

# Chuyen cau hoi thanh vector
query_vector = model.encode(
    [question],
    normalize_embeddings=True
).tolist()

# Tim 5 ket qua gan nghia nhat
results = collection.query(
    query_embeddings=query_vector,
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

# Hien thi ket qua
if not results["ids"][0]:
    print("Khong tim thay mon an phu hop.")
else:
    for i, food_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        print(f"\nKet qua {i + 1}")
        print("ID:", food_id)
        print("Ten mon:", metadata["ten_mon"])
        print("Quan/huyen:", metadata["quan_huyen"])
        print("Dia chi:", metadata["dia_chi"])

        if "gia" in metadata:
            print("Gia goc:", metadata["gia"], "dong")

        if "gia_khuyen_mai" in metadata:
            print(
                "Gia khuyen mai:",
                metadata["gia_khuyen_mai"],
                "dong"
            )

        print("Khoang cach vector:", round(distance, 4))
