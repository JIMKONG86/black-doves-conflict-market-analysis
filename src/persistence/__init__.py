"""Relational persistence for the written-assignment submission."""

from src.persistence.database import (
    AnalysisRecord,
    Base,
    DatasetManifest,
    DatasetMetadata,
    SubmissionDatabase,
)

__all__ = [
    "AnalysisRecord",
    "Base",
    "DatasetManifest",
    "DatasetMetadata",
    "SubmissionDatabase",
]
