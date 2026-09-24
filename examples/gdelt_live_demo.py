"""Optional live GDELT example; not part of the offline regression suite."""

from src.data_access.crawler import CrawlRequest
from src.data_access.gdelt_source_adapter import GdeltSourceAdapter


def main() -> int:
    adapter = GdeltSourceAdapter(source_id="GDELT_GLOBAL_DOC_API")
    request = CrawlRequest(query="Iran", max_results=5)
    results = adapter.collect(request)

    print(f"Results: {len(results)}")
    for result in results:
        print("---")
        print("Status:", result.retrieval_status)
        print("Date:", result.published_at)
        print("Country:", result.source_country_code)
        print("Title:", result.title)
        print("URL:", result.url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
