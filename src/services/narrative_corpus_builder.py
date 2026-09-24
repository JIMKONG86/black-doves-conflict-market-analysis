import csv
import json
from dataclasses import replace
from datetime import date, datetime, time, timezone
from pathlib import Path

from src.data_access.media_source_registry import MediaSourceRegistry
from src.models.narrative_document import NarrativeDocument
from src.services.narrative_classifier import (
    FRAMING_TAXONOMY,
    NARRATIVE_TAXONOMY,
    NarrativeClassifier,
)


SOURCE_LAYERS = ("STATE_ORGAN", "NEWS", "TELEVISION")


class NarrativeCorpusBuilder:
    """Build the auditable state/news/TV comparison corpus."""

    def __init__(self, classifier=None):
        self.classifier = classifier or NarrativeClassifier()

    def build(
        self,
        start_date,
        end_date,
        announcement_directory,
        media_directory,
        media_registry_file,
        centcom_file,
        review_directory=None,
    ):
        start_date, end_date = self._validate_period(start_date, end_date)
        media_registry = MediaSourceRegistry.from_json(media_registry_file)
        documents = []
        documents.extend(
            self._load_versioned_documents(
                announcement_directory,
                start_date,
                end_date,
                source_layer="STATE_ORGAN",
                media_registry=None,
            )
        )
        documents.extend(
            self._load_versioned_documents(
                media_directory,
                start_date,
                end_date,
                source_layer=None,
                media_registry=media_registry,
            )
        )
        documents.extend(
            self._load_centcom_documents(centcom_file, start_date, end_date)
        )

        deduplicated = {}
        for document in documents:
            deduplicated[document.document_id] = document
        suggested = [
            self.classifier.suggest(document)
            for document in deduplicated.values()
        ]
        reviewed = self._apply_reviews(suggested, review_directory)
        return sorted(
            reviewed,
            key=lambda item: (
                item.published_at,
                item.source_layer,
                item.source_id,
                item.document_id,
            ),
        )

    def export(self, documents, document_file, category_file, coverage_file):
        document_path = Path(document_file)
        category_path = Path(category_file)
        coverage_path = Path(coverage_file)
        for path in (document_path, category_path, coverage_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._write_csv(document_path, self.document_records(documents))
        self._write_csv(category_path, self.category_records(documents))
        self._write_csv(coverage_path, self.coverage_records(documents))
        return document_path, category_path, coverage_path

    @staticmethod
    def document_records(documents):
        return [
            {
                "document_id": item.document_id,
                "published_at": item.published_at.isoformat(),
                "country_code": item.country_code,
                "target_country_codes": ";".join(item.target_country_codes),
                "source_id": item.source_id,
                "publisher": item.publisher,
                "source_layer": item.source_layer,
                "broadcaster_control": item.broadcaster_control,
                "company_ids": ";".join(item.company_ids),
                "medium": item.medium,
                "title": item.title,
                "content": item.content,
                "url": item.url,
                "categories": ";".join(item.categories),
                "framing_codes": ";".join(item.framing_codes),
                "classification_status": item.classification_status,
                "verification_status": item.verification_status,
                "reviewer": item.reviewer or "",
                "reviewed_at": (
                    item.reviewed_at.isoformat() if item.reviewed_at else ""
                ),
            }
            for item in documents
        ]

    @staticmethod
    def category_records(documents):
        records = []
        for layer in SOURCE_LAYERS:
            layer_documents = [item for item in documents if item.source_layer == layer]
            reviewed = [
                item
                for item in layer_documents
                if item.classification_status == "MANUALLY_REVIEWED"
            ]
            suggested = [
                item
                for item in layer_documents
                if item.classification_status in {
                    "AUTO_SUGGESTED",
                    "MANUALLY_REVIEWED",
                }
            ]
            for code, definition in NARRATIVE_TAXONOMY.items():
                reviewed_count = sum(code in item.categories for item in reviewed)
                suggested_count = sum(code in item.categories for item in suggested)
                records.append(
                    {
                        "source_layer": layer,
                        "category_code": code,
                        "category_label": definition["label"],
                        "reviewed_document_count": reviewed_count,
                        "reviewed_layer_total": len(reviewed),
                        "reviewed_share": (
                            reviewed_count / len(reviewed) if reviewed else ""
                        ),
                        "suggested_document_count": suggested_count,
                        "suggested_layer_total": len(suggested),
                        "suggested_share": (
                            suggested_count / len(suggested) if suggested else ""
                        ),
                    }
                )
        return records

    @staticmethod
    def coverage_records(documents):
        records = []
        for layer in SOURCE_LAYERS:
            layer_documents = [item for item in documents if item.source_layer == layer]
            dates = [item.published_at.date() for item in layer_documents]
            records.append(
                {
                    "source_layer": layer,
                    "source_count": len({item.source_id for item in layer_documents}),
                    "document_count": len(layer_documents),
                    "reviewed_document_count": sum(
                        item.classification_status == "MANUALLY_REVIEWED"
                        for item in layer_documents
                    ),
                    "first_publication_date": min(dates).isoformat() if dates else "",
                    "last_publication_date": max(dates).isoformat() if dates else "",
                    "coverage_status": "PARTIAL" if layer_documents else "MISSING",
                    "study_window_complete": False,
                }
            )
        return records

    @staticmethod
    def _load_versioned_documents(
        directory,
        start_date,
        end_date,
        source_layer,
        media_registry,
    ):
        root = Path(directory)
        if not root.exists():
            return []
        selected = {}
        for path in sorted(root.glob("*/*/*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("retrieval_status") != "success":
                continue
            published_at = NarrativeCorpusBuilder._parse_datetime(
                payload.get("published_at")
            )
            if published_at is None or not (
                start_date <= published_at.date() <= end_date
            ):
                continue
            document_id = str(payload.get("document_id") or "").strip()
            if not document_id:
                continue
            title = str(payload.get("title") or "Untitled document").strip()
            url = str(payload.get("canonical_url") or payload.get("url") or "").strip()
            if not url:
                continue
            source_id = str(payload.get("source_id") or payload.get("source_name") or "").strip()
            country_code = str(payload.get("source_country_code") or "").strip()
            publisher = str(payload.get("publisher") or payload.get("source_name") or "").strip()
            broadcaster_control = "UNKNOWN"
            if source_layer is None:
                try:
                    definition = media_registry.get(source_id)
                except KeyError:
                    continue
                item_layer = definition.source_layer
                medium = definition.medium
                country_code = country_code or definition.publisher_country_code
                publisher = publisher or definition.publisher
                broadcaster_control = definition.broadcaster_control
            else:
                item_layer = source_layer
                medium = "OFFICIAL_RELEASE"
                broadcaster_control = "STATE_CONTROLLED"
            if not country_code or not source_id or not publisher:
                continue
            company_ids = payload.get("company_ids") or ()
            if isinstance(company_ids, str):
                company_ids = [
                    value.strip() for value in company_ids.split(";") if value.strip()
                ]
            target_country_codes = payload.get("target_country_codes") or ()
            if isinstance(target_country_codes, str):
                target_country_codes = [
                    value.strip()
                    for value in target_country_codes.split(";")
                    if value.strip()
                ]
            selected[document_id] = NarrativeDocument(
                document_id=document_id,
                published_at=published_at,
                country_code=country_code,
                source_id=source_id,
                publisher=publisher,
                source_layer=item_layer,
                medium=medium,
                title=title,
                content=str(payload.get("content") or "").strip(),
                url=url,
                verification_status="PARTIALLY_VERIFIED",
                broadcaster_control=broadcaster_control,
                company_ids=tuple(company_ids),
                target_country_codes=tuple(target_country_codes),
            )
        return list(selected.values())

    @staticmethod
    def _load_centcom_documents(file_path, start_date, end_date):
        path = Path(file_path)
        if not path.is_file():
            return []
        grouped = {}
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if str(row.get("include_in_core_series", "")).casefold() not in {
                    "true",
                    "1",
                    "yes",
                }:
                    continue
                publication = NarrativeCorpusBuilder._parse_datetime(
                    row.get("publication_date")
                )
                if publication is None or not (
                    start_date <= publication.date() <= end_date
                ):
                    continue
                release_id = row["source_release_id"].strip()
                record = grouped.setdefault(
                    release_id,
                    {
                        "published_at": publication,
                        "title": row["title"].strip(),
                        "url": row["source_url"].strip(),
                        "descriptions": [],
                        "targets": set(),
                    },
                )
                description = row.get("description", "").strip()
                if description and description not in record["descriptions"]:
                    record["descriptions"].append(description)
                affected = row.get("affected_country_code", "").strip().upper()
                if affected:
                    record["targets"].add(affected)
        return [
            NarrativeDocument(
                document_id=f"CENTCOM-{release_id}",
                published_at=record["published_at"],
                country_code="US",
                source_id="US_CENTCOM_PUBLIC_RELEASES",
                publisher="U.S. Central Command",
                source_layer="STATE_ORGAN",
                medium="OFFICIAL_RELEASE",
                title=record["title"],
                content="\n".join(record["descriptions"]),
                url=record["url"],
                verification_status="VERIFIED",
                target_country_codes=tuple(sorted(record["targets"])),
                broadcaster_control="STATE_CONTROLLED",
            )
            for release_id, record in grouped.items()
        ]

    def _apply_reviews(self, documents, review_directory):
        if review_directory is None:
            return documents
        root = Path(review_directory)
        if not root.exists():
            return documents
        reviews = {}
        for path in sorted(root.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            reviews[payload["document_id"]] = payload
        output = []
        for document in documents:
            review = reviews.get(document.document_id)
            if review is None:
                output.append(document)
                continue
            confirmed = self.classifier.confirm(
                document,
                categories=review.get("categories", ()),
                framing_codes=review.get("framing_codes", ()),
                reviewer=review["reviewer"],
                reviewed_at=self._parse_datetime(review.get("reviewed_at")),
            )
            output.append(
                replace(
                    confirmed,
                    verification_status=review.get(
                        "verification_status",
                        document.verification_status,
                    ),
                )
            )
        return output

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        normalized = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed_date = date.fromisoformat(normalized)
            except ValueError:
                return None
            parsed = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _validate_period(start_date, end_date):
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise TypeError("start_date and end_date must be dates")
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        return start_date, end_date

    @staticmethod
    def _write_csv(path, rows):
        if not rows:
            raise ValueError(f"No rows available for {path.name}")
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
