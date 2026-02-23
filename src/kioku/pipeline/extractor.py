"""LLM-powered entity and relationship extraction from memory text."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass
class Entity:
    """An extracted entity."""

    name: str
    type: str  # PERSON, PLACE, EVENT, EMOTION, TOPIC, PRODUCT

    def __hash__(self):
        return hash((self.name.lower(), self.type))

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.name.lower() == other.name.lower() and self.type == other.type


@dataclass
class Relationship:
    """An extracted relationship between two entities."""

    source: str  # entity name
    target: str  # entity name
    rel_type: str  # CAUSAL, EMOTIONAL, TEMPORAL, TOPICAL, INVOLVES
    weight: float = 0.5
    evidence: str = ""


@dataclass
class ExtractionResult:
    """Result of entity/relationship extraction."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    event_time: str | None = None  # YYYY-MM-DD — when the event actually happened


EXTRACTION_PROMPT_TEMPLATE = """Extract entities, relationships, and event time from this personal diary entry.

Return a JSON object with:
- "entities": array of objects with "name" (string) and "type" ("PERSON"|"PLACE"|"EVENT"|"EMOTION"|"TOPIC"|"PRODUCT")
- "relationships": array of objects with "source" (string), "target" (string), "type" ("CAUSAL"|"EMOTIONAL"|"TEMPORAL"|"TOPICAL"|"INVOLVES"), "weight" (0.0-1.0), "evidence" (string)
- "event_time": string (YYYY-MM-DD) — the date the event ACTUALLY happened (not when it was recorded). Analyze relative time expressions like "hôm qua" (yesterday), "tuần trước" (last week), "năm ngoái" (last year), "tháng 3" (March), "lúc 22 tuổi" etc. relative to the processing date. If unclear or the event is happening today, return null.

Rules:
- Extract ALL people, places, emotions, events, and topics mentioned
- "weight" reflects how strong the connection is (0.1=weak, 1.0=very strong)
- "evidence" is the exact quote from the text that supports this relationship
- Keep entity names short and consistent (e.g., "Hùng" not "sếp Hùng")
{context_entities_block}
- Return ONLY valid JSON, no markdown, no explanation

Processing date: {processing_date}

Text: {text}"""

# Legacy prompt prefix (kept for compatibility)
EXTRACTION_PROMPT_PREFIX = """Extract entities and relationships from this personal diary entry.

Return a JSON object with:
- "entities": array of objects with "name" (string) and "type" ("PERSON"|"PLACE"|"EVENT"|"EMOTION"|"TOPIC"|"PRODUCT")
- "relationships": array of objects with "source" (string), "target" (string), "type" ("CAUSAL"|"EMOTIONAL"|"TEMPORAL"|"TOPICAL"|"INVOLVES"), "weight" (0.0-1.0), "evidence" (string)

Rules:
- Extract ALL people, places, emotions, events, and topics mentioned
- "weight" reflects how strong the connection is (0.1=weak, 1.0=very strong)
- "evidence" is the exact quote from the text that supports this relationship
- Keep entity names short and consistent (e.g., "Hùng" not "sếp Hùng")
- Return ONLY valid JSON, no markdown, no explanation

Text: """


class Extractor(Protocol):
    """Protocol for entity extractors."""

    def extract(
        self, text: str, context_entities: list[str] | None = None, processing_date: str = ""
    ) -> ExtractionResult: ...


class ClaudeExtractor:
    """Extract entities and relationships using Claude Haiku."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.model = model
        self._client = None
        self._api_key = api_key

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def extract(
        self, text: str, context_entities: list[str] | None = None, processing_date: str = ""
    ) -> ExtractionResult:
        """Extract entities, relationships, and event_time from text using Claude.

        Args:
            text: The memory text to extract from.
            context_entities: Existing canonical entity names for disambiguation.
            processing_date: Today's date (YYYY-MM-DD) for resolving relative time.
        """
        # Build context entity block for entity resolution
        if context_entities:
            entity_list = ", ".join(context_entities[:30])
            context_block = (
                f"- IMPORTANT: The following entities already exist in the knowledge graph: [{entity_list}]. "
                "If an entity in the text refers to one of these (synonyms, nicknames, abbreviations, pronouns), "
                "use the EXISTING canonical name instead of creating a new one."
            )
        else:
            context_block = ""

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            context_entities_block=context_block,
            processing_date=processing_date or "unknown",
            text=text,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            return self._parse_response(content)
        except Exception as e:
            log.warning("Entity extraction failed: %s", e)
            return ExtractionResult()

    def _parse_response(self, text: str) -> ExtractionResult:
        """Parse LLM JSON response into ExtractionResult."""
        try:
            # Strip markdown code fences if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
                text = text.strip()

            # Find JSON object — Claude may add preamble text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

            data = json.loads(text)
            entities = [
                Entity(name=e["name"], type=e["type"])
                for e in data.get("entities", [])
                if "name" in e and "type" in e
            ]
            relationships = [
                Relationship(
                    source=r["source"],
                    target=r["target"],
                    rel_type=r.get("type", "TOPICAL"),
                    weight=r.get("weight", 0.5),
                    evidence=r.get("evidence", ""),
                )
                for r in data.get("relationships", [])
                if "source" in r and "target" in r
            ]
            event_time = data.get("event_time") or None
            return ExtractionResult(
                entities=entities, relationships=relationships, event_time=event_time
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Failed to parse extraction response: %s", e)
            return ExtractionResult()


class FakeExtractor:
    """Deterministic fake extractor for testing."""

    def extract(
        self, text: str, context_entities: list[str] | None = None, processing_date: str = ""
    ) -> ExtractionResult:
        """Simple rule-based extraction for tests."""
        entities = []
        relationships = []

        # Simple keyword-based extraction
        emotion_keywords = {
            "vui": "EMOTION",
            "buồn": "EMOTION",
            "stressed": "EMOTION",
            "happy": "EMOTION",
            "căng thẳng": "EMOTION",
            "khỏe": "EMOTION",
            "trầm cảm": "EMOTION",
            "lo lắng": "EMOTION",
        }
        for kw, etype in emotion_keywords.items():
            if kw.lower() in text.lower():
                entities.append(Entity(name=kw, type=etype))

        # Detect capitalized Vietnamese names (simple heuristic)
        words = text.split()
        for i, w in enumerate(words):
            if w[0].isupper() and len(w) > 1 and w.isalpha():
                # Skip common Vietnamese words
                if w.lower() not in {"hôm", "sáng", "tối", "đọc", "cảm", "bị", "đi", "gọi"}:
                    entities.append(Entity(name=w, type="PERSON"))

        # Simple relationship: if emotion + person both exist
        persons = [e for e in entities if e.type == "PERSON"]
        emotions = [e for e in entities if e.type == "EMOTION"]
        for p in persons:
            for em in emotions:
                relationships.append(
                    Relationship(
                        source=p.name,
                        target=em.name,
                        rel_type="EMOTIONAL",
                        weight=0.6,
                        evidence=text[:100],
                    )
                )

        return ExtractionResult(entities=entities, relationships=relationships)
