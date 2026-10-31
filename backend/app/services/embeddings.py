"""Embedding multilingue locale (fastembed, ONNX: niente PyTorch)."""
from app.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        kwargs = {"model_name": settings.embedding_model}
        if settings.embedding_cache:
            kwargs["cache_dir"] = settings.embedding_cache
        _model = TextEmbedding(**kwargs)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _get_model().embed(texts)]
