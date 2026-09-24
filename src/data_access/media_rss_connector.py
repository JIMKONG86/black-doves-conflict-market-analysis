from src.data_access.crawler import SourceAdapter
from src.data_access.rss_source_adapter import RssSourceAdapter
from src.models.media_source_definition import MediaSourceDefinition


class MediaRssConnector(SourceAdapter):
    """Connect a configured publisher RSS feed to the common crawl boundary."""

    def __init__(self, definition):
        if not isinstance(definition, MediaSourceDefinition):
            raise TypeError("definition must be a MediaSourceDefinition")
        if definition.delivery_method != "RSS":
            raise ValueError("MediaRssConnector requires delivery_method RSS")
        self.definition = definition
        self.adapter = RssSourceAdapter(
            source_name=definition.source_name,
            feed_url=definition.feed_url,
            source_id=definition.source_id,
            source_country_code=definition.publisher_country_code,
            jurisdiction=definition.publisher_country_code,
            publication_timezone=definition.publication_timezone,
            publisher=definition.publisher,
        )

    @property
    def source_name(self):
        return self.definition.source_name

    def collect(self, request):
        return self.adapter.collect(request)
