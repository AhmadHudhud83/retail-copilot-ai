# agent/rag/retrieval.py
import os
import glob
from typing import List, Dict
from rank_bm25 import BM25Okapi

class LocalRetriever:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = docs_dir
        self.chunks = []
        self.bm25 = None
        self._build_index()

    def _build_index(self):
            md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
            print(f"  > [Retriever] Found files: {[os.path.basename(f) for f in md_files]}") # DEBUG PRINT
            
            for fpath in md_files:
                fname = os.path.basename(fpath)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # IMPROVED CHUNKING: Split by "## " headers to keep sections together
                # This ensures "Beverages" and "14 days" stay in the same chunk
                raw_chunks = content.split("\n## ")
                
                for i, text in enumerate(raw_chunks):
                    if not text.strip(): continue
                    
                    # Add "## " back if it was removed by split
                    full_text = text if text.startswith("#") else "## " + text
                    
                    chunk_id = f"{fname.replace('.md', '')}::chunk{i}"
                    self.chunks.append({
                        "id": chunk_id,
                        "text": full_text,
                        "source": fname,
                        # Simple tokenization: lowercase and alphanumeric only
                        "tokens": "".join([c if c.isalnum() else " " for c in full_text.lower()]).split()
                    })

            tokenized_corpus = [c["tokens"] for c in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            print(f"  > [Retriever] Indexed {len(self.chunks)} chunks.")

    def search(self, query: str, k: int = 3) -> List[Dict]:
        if not self.chunks: return []

        # Same simple tokenization for query
        query_tokens = "".join([c if c.isalnum() else " " for c in query.lower()]).split()
        scores = self.bm25.get_scores(query_tokens)
        
        top_n_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        results = []
        for idx in top_n_indices:
            # LOWER THRESHOLD: Even weak matches should be returned for small docs
            if scores[idx] > 0.0: 
                chunk = self.chunks[idx].copy()
                chunk["score"] = scores[idx]
                del chunk["tokens"]
                results.append(chunk)
        return results

# Simple test
if __name__ == "__main__":
    retriever = LocalRetriever()
    results = retriever.search("return policy for beverages", k=2)
    for r in results:
        print(f"[{r['score']:.2f}] {r['id']}: {r['text'][:50]}...")