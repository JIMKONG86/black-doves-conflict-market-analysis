import json
from pathlib import Path

from src.models.source_definition import SourceDefinition


class SourceRegistry:
    """Loads and validates the runtime export of the source registry."""

    def __init__(self, definitions):
        self._definitions = {}

        for definition in definitions:
            if not isinstance(definition, SourceDefinition):
                raise TypeError("definitions must contain SourceDefinition objects")

            if definition.source_id in self._definitions:
                raise ValueError(
                    f"Duplicate source_id: {definition.source_id}"
                )

            self._definitions[definition.source_id] = definition

    @classmethod
    def from_json(cls, file_path="config/country_sources.json"):
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)

        sources = payload.get("sources")
        if not isinstance(sources, list):
            raise ValueError("Registry JSON must contain a sources list")

        return cls(
            SourceDefinition.from_mapping(source)
            for source in sources
        )

    def get(self, source_id):
        try:
            return self._definitions[source_id]
        except KeyError as error:
            raise KeyError(f"Unknown source_id: {source_id}") from error

    def for_country(self, country_code, active_only=True):
        normalized_code = country_code.strip().upper()
        definitions = [
            definition
            for definition in self._definitions.values()
            if definition.country_code == normalized_code
            and (definition.active or not active_only)
        ]
        return sorted(
            definitions,
            key=lambda item: (item.source_priority, item.source_id),
        )

    def automated(self):
        return [
            definition
            for definition in self._definitions.values()
            if definition.active
            and definition.integration_status == "IMPLEMENTED"
        ]

    def __len__(self):
        return len(self._definitions)
