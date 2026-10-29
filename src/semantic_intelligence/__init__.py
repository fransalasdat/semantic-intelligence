"""Semantic Intelligence package."""

from semantic_intelligence.semantic_model import (
    SemanticModel,
    SemanticModelBuildError,
    build_semantic_model,
)


__version__ = "0.1.0"

__all__ = [
    "SemanticModel",
    "SemanticModelBuildError",
    "build_semantic_model",
]
