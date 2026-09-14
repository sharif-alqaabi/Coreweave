"""Semantic index over the corpus passages, so the candidate pool for each finding is retrieved by meaning and not only
by shared entities. Static embeddings (model2vec, numpy-only, ~30 MB model, ~10k passages/s); cosine search in numpy.
TypeSafe still judges every candidate; this only decides what it gets to see.

    idx = Index.build(passages)            # cached in data/corpus/<model>.npz, keyed by passage ids
    idx.search("E2f7 expression is reduced in spaceflight thymus", k=40)  -> [(passage_index, score), ...]
"""
import hashlib, json, os
import numpy as np
from helix.settings import settings, ROOT

DIR = os.path.join(ROOT, "data/corpus")


class Index:
    def __init__(self, ids, vectors, model_name):
        self.ids, self.vectors, self.model_name = ids, vectors, model_name
        self.pos = {pid: i for i, pid in enumerate(ids)}
        self._model = None

    @staticmethod
    def _cache_path(model_name, ids):
        h = hashlib.sha1("\n".join(ids).encode()).hexdigest()[:10]
        return os.path.join(DIR, f"index_{model_name.replace('/', '_')}_{h}.npz")

    @classmethod
    def build(cls, passages, model_name=None, progress=print):
        model_name = model_name or settings.helix_embeddings
        ids = [p["id"] for p in passages]
        path = cls._cache_path(model_name, ids)
        if os.path.exists(path):
            z = np.load(path, allow_pickle=False)
            return cls(ids, z["vectors"], model_name)
        from model2vec import StaticModel
        model = StaticModel.from_pretrained(model_name)
        vecs = model.encode([p["text"] for p in passages], show_progress_bar=False).astype(np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
        os.makedirs(DIR, exist_ok=True)
        np.savez(path, vectors=vecs)
        progress(f"embedded {len(ids)} passages with {model_name} -> {os.path.basename(path)}")
        idx = cls(ids, vecs, model_name); idx._model = model
        return idx

    def _encode(self, texts):
        if self._model is None:
            from model2vec import StaticModel
            self._model = StaticModel.from_pretrained(self.model_name)
        v = self._model.encode(texts, show_progress_bar=False).astype(np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    def search(self, text, k=40):
        q = self._encode([text])[0]
        scores = self.vectors @ q
        top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
        top = top[np.argsort(-scores[top])]
        return [(int(i), float(scores[i])) for i in top]


def finding_query(f):
    """What to embed for a finding: the claim plus the scout's novelty argument (it names the mechanism and tissue)."""
    return f"{f['claim']} {f.get('why_not_known', '')}".strip()
