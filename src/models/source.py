class DataSource:
    def __init__(
        self,
        source_id,
        name,
        source_type,
        url,
        publication_date
    ):
        self.name = name
        self.source_id = source_id
        self.source_type = source_type
        self.url = url
        self.publication_date = publication_date
