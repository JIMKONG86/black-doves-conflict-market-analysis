"""SQLite/SQLAlchemy persistence with row-level provenance.

The database is a compact, queryable snapshot of the tables used in the final
report.  CSV remains the transparent exchange format; SQLite demonstrates
relational persistence and keeps a checksum plus provenance for every import.
"""

from __future__ import annotations

import csv
import hashlib
import json

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


class DatasetManifest(Base):
    __tablename__ = "dataset_manifest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(120), unique=True)
    relative_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    imported_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    default_source_name: Mapped[str] = mapped_column(Text)
    default_source_url: Mapped[str] = mapped_column(Text)
    default_reporting_period: Mapped[str] = mapped_column(Text)
    default_unit: Mapped[str] = mapped_column(Text)
    default_estimation_status: Mapped[str] = mapped_column(Text)

    records: Mapped[list["AnalysisRecord"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AnalysisRecord(Base):
    __tablename__ = "analysis_record"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "row_number",
            name="uq_analysis_record_dataset_row",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_manifest.id", ondelete="CASCADE"),
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer)
    observation_date: Mapped[str] = mapped_column(Text)
    reporting_period: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    estimation_status: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)

    dataset: Mapped[DatasetManifest] = relationship(
        back_populates="records"
    )


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_key: str
    relative_path: str
    source_name: str
    source_url: str
    reporting_period: str
    unit: str
    estimation_status: str


class SubmissionDatabase:
    """Create and populate an idempotent SQLite analysis snapshot."""

    def __init__(self, database_file):
        self.database_file = Path(database_file)
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.database_file.resolve()}",
            future=True,
        )
        event.listen(self.engine, "connect", self._enable_foreign_keys)
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    @staticmethod
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def create_schema(self):
        Base.metadata.create_all(self.engine)

    def import_csv(self, project_root, metadata):
        if not isinstance(metadata, DatasetMetadata):
            raise TypeError("metadata must be a DatasetMetadata instance")
        root = Path(project_root).resolve()
        source_file = (root / metadata.relative_path).resolve()
        try:
            source_file.relative_to(root)
        except ValueError as error:
            raise ValueError("Dataset path must stay inside project_root") from error
        if not source_file.is_file():
            raise FileNotFoundError(f"Submission dataset not found: {source_file}")

        rows = self._read_csv(source_file)
        digest = hashlib.sha256(source_file.read_bytes()).hexdigest()
        imported_at = datetime.now(timezone.utc)

        with self.session_factory.begin() as session:
            manifest = session.scalar(
                select(DatasetManifest).where(
                    DatasetManifest.dataset_key == metadata.dataset_key
                )
            )
            if manifest is None:
                manifest = DatasetManifest(dataset_key=metadata.dataset_key)
                session.add(manifest)
            else:
                manifest.records.clear()

            manifest.relative_path = metadata.relative_path
            manifest.sha256 = digest
            manifest.row_count = len(rows)
            manifest.imported_at_utc = imported_at
            manifest.default_source_name = metadata.source_name
            manifest.default_source_url = metadata.source_url
            manifest.default_reporting_period = metadata.reporting_period
            manifest.default_unit = metadata.unit
            manifest.default_estimation_status = metadata.estimation_status
            session.flush()

            for row_number, row in enumerate(rows, start=1):
                session.add(
                    AnalysisRecord(
                        dataset_id=manifest.id,
                        row_number=row_number,
                        observation_date=self._first_value(
                            row,
                            (
                                "observation_date",
                                "market_date",
                                "event_calendar_date",
                                "event_date",
                                "fuel_observation_date",
                                "announcement_date",
                                "publication_date",
                            ),
                            metadata.reporting_period,
                        ),
                        reporting_period=self._reporting_period(
                            row, metadata.reporting_period
                        ),
                        unit=self._first_value(
                            row, ("unit",), metadata.unit
                        ),
                        source_name=self._first_value(
                            row,
                            (
                                "source_name",
                                "source_org",
                                "brent_source_name",
                            ),
                            metadata.source_name,
                        ),
                        source_url=self._first_value(
                            row,
                            (
                                "source_url",
                                "brent_source_url",
                            ),
                            metadata.source_url,
                        ),
                        estimation_status=self._first_value(
                            row,
                            (
                                "estimation_status",
                                "verification_status",
                                "event_verification_status",
                                "status",
                            ),
                            metadata.estimation_status,
                        ),
                        payload_json=json.dumps(
                            row,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    )
                )
        return len(rows)

    def counts(self):
        with self.session_factory() as session:
            manifests = session.scalars(
                select(DatasetManifest).order_by(
                    DatasetManifest.dataset_key
                )
            ).all()
            return {
                manifest.dataset_key: manifest.row_count
                for manifest in manifests
            }

    @staticmethod
    def _read_csv(source_file):
        with source_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"CSV has no header: {source_file}")
            return [
                {key: (value if value is not None else "") for key, value in row.items()}
                for row in reader
            ]

    @classmethod
    def _reporting_period(cls, row, default):
        explicit = cls._first_value(row, ("reference_period",), "")
        if explicit:
            return explicit
        start = cls._first_value(
            row,
            ("analysis_start_date", "brent_week_start"),
            "",
        )
        end = cls._first_value(
            row,
            ("analysis_end_date", "brent_week_end"),
            "",
        )
        if start and end:
            return f"{start}/{end}"
        return default

    @staticmethod
    def _first_value(row, names, default):
        for name in names:
            value = str(row.get(name, "")).strip()
            if value and value.casefold() != "nan":
                return value
        return default
