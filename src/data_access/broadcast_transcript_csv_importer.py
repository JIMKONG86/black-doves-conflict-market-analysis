import csv
from datetime import datetime, timezone
from pathlib import Path

from src.data_access.crawler import (
    CrawlRequest,
    CrawlResult,
    SourceAdapter,
    SourceType,
)
from src.models.media_source_definition import MediaSourceDefinition


class BroadcastTranscriptCsvImporter(SourceAdapter):
    """Import lawfully obtained broadcast transcripts from a stable CSV.

    The importer deliberately does not scrape video platforms or bypass access
    controls. The source CSV remains the auditable evidence file.
    """

    REQUIRED_COLUMNS = frozenset({
        "published_at",
        "programme",
        "title",
        "transcript",
        "url",
    })

    def __init__(self, definition, input_file):
        if not isinstance(definition, MediaSourceDefinition):
            raise TypeError("definition must be a MediaSourceDefinition")
        if definition.delivery_method != "TRANSCRIPT_CSV":
            raise ValueError(
                "BroadcastTranscriptCsvImporter requires TRANSCRIPT_CSV"
            )
        self.definition = definition
        self.input_file = Path(input_file)

    @property
    def source_name(self):
        return self.definition.source_name

    def collect(self, request):
        if not isinstance(request, CrawlRequest):
            raise TypeError("request must be a CrawlRequest")
        if not self.input_file.is_file():
            raise FileNotFoundError(self.input_file)
        with self.input_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or ())
            if missing:
                raise ValueError(
                    "Transcript CSV is missing columns: "
                    + ", ".join(sorted(missing))
                )
            results = []
            for row in reader:
                published_at = self._parse_datetime(row["published_at"])
                if not self._in_range(published_at, request):
                    continue
                searchable = f"{row['title']} {row['transcript']}".casefold()
                if request.query != "*" and not all(
                    term in searchable for term in request.query.casefold().split()
                ):
                    continue
                programme = row["programme"].strip()
                transcript = row["transcript"].strip()
                url = row["url"].strip()
                if not programme or not transcript or not url:
                    raise ValueError(
                        "programme, transcript and url must not be empty"
                    )
                content = f"Programme: {programme}\n\n{transcript}"
                results.append(
                    CrawlResult(
                        source_name=self.source_name,
                        source_type=SourceType.FILE,
                        url=url,
                        canonical_url=url,
                        source_id=self.definition.source_id,
                        source_country_code=(
                            self.definition.publisher_country_code
                        ),
                        query=request.query,
                        title=row["title"].strip() or programme,
                        publisher=self.definition.publisher,
                        author=row.get("presenter", "").strip() or None,
                        published_at=published_at,
                        publication_timezone=(
                            self.definition.publication_timezone
                        ),
                        date_precision="datetime",
                        jurisdiction=(
                            self.definition.publisher_country_code
                        ),
                        language=self.definition.primary_language,
                        content=content,
                        retrieved_at=datetime.now(timezone.utc),
                    )
                )
                if len(results) >= request.max_results:
                    break
        return results

    @staticmethod
    def _parse_datetime(value):
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError(
                "published_at must use ISO-8601 date/time format"
            ) from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _in_range(published_at, request):
        publication_date = published_at.date()
        if request.start_date and publication_date < request.start_date:
            return False
        if request.end_date and publication_date > request.end_date:
            return False
        return True
