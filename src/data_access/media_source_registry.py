import json
from pathlib import Path

from src.models.media_source_definition import MediaSourceDefinition


class MediaSourceRegistry:
    def __init__(self, definitions):
        self._definitions = {}
        for definition in definitions:
            if not isinstance(definition, MediaSourceDefinition):
                raise TypeError(
                    "definitions must contain MediaSourceDefinition objects"
                )
            if definition.source_id in self._definitions:
                raise ValueError(f"Duplicate source_id: {definition.source_id}")
            self._definitions[definition.source_id] = definition

    @classmethod
    def from_json(cls, file_path="config/media_sources.json"):
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)
        sources = payload.get("sources")
        if not isinstance(sources, list):
            raise ValueError("Media registry JSON must contain a sources list")
        return cls(MediaSourceDefinition.from_mapping(item) for item in sources)

    def get(self, source_id):
        try:
            return self._definitions[source_id]
        except KeyError as error:
            raise KeyError(f"Unknown media source_id: {source_id}") from error

    def active(self):
        return [item for item in self._definitions.values() if item.active]

    def __len__(self):
        return len(self._definitions)
