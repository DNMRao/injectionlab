"""Day-3 check: turn text into vectors and find the closest one to a question.

No Qdrant yet: we do the "nearest neighbour" search by hand with numpy,
to see what Qdrant will do for us later.
Run:  uv run python scripts/try_embeddings.py
"""

import numpy as np
from fastembed import TextEmbedding 

texts = [
    "Travel policy: hotels up to 150 EUR per night, economy class flights.",
    "Q3 report: revenue grew 8 percent compared to Q2.",
    "Meeting notes: the team agreed to move the launch to January.",
    "Invoices from suppliers must be paid within 14 days.",
]
#question = "How much can I spend on a hotel during a business trip?"
question = "Did sales go up?"
# 1) Load the model (downloaded once, ~130 MB, then cached)
model = TextEmbedding("BAAI/bge-small-en-v1.5")

# 2) Text -> vectors. embed() gives a generator, list() collects the results
doc_vecs = np.array(list(model.embed(texts)))
q_vec = np.array(list(model.query_embed(question)))[0]
print("Each text became a vector of", doc_vecs.shape[1], "numbers")
print("First 5 numbers of text 1:", doc_vecs[0][:5].round(3))

# 3) Cosine similarity = how much two vectors point in the same direction (1 = same)
scores = doc_vecs @ q_vec / (np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(q_vec))

print(f"\nQuestion: {question}\n")
for score, text in sorted(zip(scores, texts), reverse=True):
    print(f"  {score:.3f}  {text}")
