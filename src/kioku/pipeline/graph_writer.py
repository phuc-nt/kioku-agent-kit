"""FalkorDB knowledge graph writer — stores entities and relationships."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Protocol
from dataclasses import dataclass, field

from kioku.pipeline.extractor import Entity, Relationship, ExtractionResult

log = logging.getLogger(__name__)
JST = timezone(timedelta(hours=7))


@dataclass
class GraphNode:
    """A node in the graph search results."""

    name: str
    type: str
    mention_count: int = 0
    first_seen: str = ""
    last_seen: str = ""


@dataclass
class GraphEdge:
    """An edge in the graph search results."""

    source: str
    target: str
    rel_type: str
    weight: float = 0.5
    evidence: str = ""


@dataclass
class GraphSearchResult:
    """Result from a graph traversal."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    paths: list[list[str]] = field(default_factory=list)


class GraphStore(Protocol):
    """Protocol for graph stores."""

    def upsert(self, extraction: ExtractionResult, date: str, timestamp: str) -> None: ...
    def search_entities(self, query: str, limit: int = 10) -> list[GraphNode]: ...
    def traverse(self, entity_name: str, max_hops: int = 2, limit: int = 20) -> GraphSearchResult: ...
    def find_path(self, source: str, target: str) -> GraphSearchResult: ...


class FalkorGraphStore:
    """FalkorDB-backed knowledge graph store."""

    def __init__(self, host: str = "localhost", port: int = 6379, graph_name: str = "kioku"):
        self.host = host
        self.port = port
        self.graph_name = graph_name
        self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            from falkordb import FalkorDB
            db = FalkorDB(host=self.host, port=self.port)
            self._graph = db.select_graph(self.graph_name)
            self._ensure_schema()
        return self._graph

    def _ensure_schema(self):
        """Create indexes for fast lookups."""
        try:
            self.graph.query("CREATE INDEX FOR (e:Entity) ON (e.name)")
        except Exception:
            pass  # Index may already exist

    def upsert(self, extraction: ExtractionResult, date: str, timestamp: str) -> None:
        """Upsert entities and relationships into the graph."""
        now = datetime.now(JST).isoformat()

        for entity in extraction.entities:
            self.graph.query(
                """MERGE (e:Entity {name: $name})
                   ON CREATE SET e.type = $type, e.first_seen = $date,
                                 e.last_seen = $date, e.mention_count = 1
                   ON MATCH SET e.last_seen = $date,
                                e.mention_count = e.mention_count + 1""",
                {"name": entity.name, "type": entity.type, "date": date},
            )

        for rel in extraction.relationships:
            self.graph.query(
                """MATCH (a:Entity {name: $source})
                   MATCH (b:Entity {name: $target})
                   MERGE (a)-[r:RELATES {type: $rel_type}]->(b)
                   ON CREATE SET r.weight = $weight, r.evidence = $evidence,
                                 r.created_at = $now, r.event_time = $date
                   ON MATCH SET r.weight = ($weight + r.weight) / 2,
                                r.event_time = $date""",
                {
                    "source": rel.source,
                    "target": rel.target,
                    "rel_type": rel.rel_type,
                    "weight": rel.weight,
                    "evidence": rel.evidence,
                    "now": now,
                    "date": date,
                },
            )

    def search_entities(self, query: str, limit: int = 10) -> list[GraphNode]:
        """Search for entities by name (case-insensitive contains)."""
        result = self.graph.query(
            """MATCH (e:Entity)
               WHERE toLower(e.name) CONTAINS toLower($query)
               RETURN e.name, e.type, e.mention_count, e.first_seen, e.last_seen
               ORDER BY e.mention_count DESC
               LIMIT $limit""",
            {"query": query, "limit": limit},
        )
        return [
            GraphNode(
                name=row[0], type=row[1], mention_count=row[2] or 0,
                first_seen=row[3] or "", last_seen=row[4] or "",
            )
            for row in result.result_set
        ]

    def traverse(self, entity_name: str, max_hops: int = 2, limit: int = 20) -> GraphSearchResult:
        """Multi-hop traversal from a seed entity."""
        result = self.graph.query(
            """MATCH (start:Entity {name: $name})
               MATCH path = (start)-[r:RELATES*1..""" + str(max_hops) + """]->(connected:Entity)
               RETURN start.name, start.type,
                      connected.name, connected.type,
                      [rel IN relationships(path) | rel.type] AS rel_types,
                      [rel IN relationships(path) | rel.weight] AS weights,
                      [rel IN relationships(path) | rel.evidence] AS evidences
               LIMIT $limit""",
            {"name": entity_name, "limit": limit},
        )

        nodes_map = {}
        edges = []
        for row in result.result_set:
            src_name, src_type = row[0], row[1]
            tgt_name, tgt_type = row[2], row[3]
            rel_types, weights, evidences = row[4], row[5], row[6]

            nodes_map[src_name] = GraphNode(name=src_name, type=src_type)
            nodes_map[tgt_name] = GraphNode(name=tgt_name, type=tgt_type)

            if rel_types:
                edges.append(GraphEdge(
                    source=src_name, target=tgt_name,
                    rel_type=rel_types[-1] if rel_types else "",
                    weight=weights[-1] if weights else 0.5,
                    evidence=evidences[-1] if evidences else "",
                ))

        return GraphSearchResult(nodes=list(nodes_map.values()), edges=edges)

    def find_path(self, source: str, target: str) -> GraphSearchResult:
        """Find shortest path between two entities."""
        result = self.graph.query(
            """MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
               MATCH path = shortestPath((a)-[*..5]->(b))
               RETURN [n IN nodes(path) | n.name] AS names,
                      [n IN nodes(path) | n.type] AS types,
                      [r IN relationships(path) | r.type] AS rel_types,
                      [r IN relationships(path) | r.evidence] AS evidences""",
            {"source": source, "target": target},
        )

        nodes = []
        edges = []
        paths = []
        for row in result.result_set:
            names, types, rel_types, evidences = row[0], row[1], row[2], row[3]
            paths.append(names)
            for i, name in enumerate(names):
                nodes.append(GraphNode(name=name, type=types[i] if i < len(types) else ""))
            for i in range(len(names) - 1):
                edges.append(GraphEdge(
                    source=names[i], target=names[i + 1],
                    rel_type=rel_types[i] if i < len(rel_types) else "",
                    evidence=evidences[i] if i < len(evidences) else "",
                ))

        return GraphSearchResult(nodes=nodes, edges=edges, paths=paths)


class InMemoryGraphStore:
    """In-memory graph store for testing — no FalkorDB needed."""

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []

    def upsert(self, extraction: ExtractionResult, date: str, timestamp: str) -> None:
        for entity in extraction.entities:
            key = entity.name.lower()
            if key in self.nodes:
                self.nodes[key].mention_count += 1
                self.nodes[key].last_seen = date
            else:
                self.nodes[key] = GraphNode(
                    name=entity.name, type=entity.type,
                    mention_count=1, first_seen=date, last_seen=date,
                )

        for rel in extraction.relationships:
            self.edges.append(GraphEdge(
                source=rel.source, target=rel.target,
                rel_type=rel.rel_type, weight=rel.weight,
                evidence=rel.evidence,
            ))

    def search_entities(self, query: str, limit: int = 10) -> list[GraphNode]:
        q = query.lower()
        matches = [n for n in self.nodes.values() if q in n.name.lower()]
        matches.sort(key=lambda n: n.mention_count, reverse=True)
        return matches[:limit]

    def traverse(self, entity_name: str, max_hops: int = 2, limit: int = 20) -> GraphSearchResult:
        visited = set()
        result_nodes = {}
        result_edges = []

        def _walk(name: str, depth: int):
            if depth > max_hops or name.lower() in visited:
                return
            visited.add(name.lower())
            if name.lower() in self.nodes:
                result_nodes[name.lower()] = self.nodes[name.lower()]

            for edge in self.edges:
                if edge.source.lower() == name.lower() and edge.target.lower() not in visited:
                    result_edges.append(edge)
                    if edge.target.lower() in self.nodes:
                        result_nodes[edge.target.lower()] = self.nodes[edge.target.lower()]
                    _walk(edge.target, depth + 1)
                elif edge.target.lower() == name.lower() and edge.source.lower() not in visited:
                    result_edges.append(edge)
                    if edge.source.lower() in self.nodes:
                        result_nodes[edge.source.lower()] = self.nodes[edge.source.lower()]
                    _walk(edge.source, depth + 1)

        _walk(entity_name, 0)
        nodes_list = list(result_nodes.values())[:limit]
        edges_list = result_edges[:limit]
        return GraphSearchResult(nodes=nodes_list, edges=edges_list)

    def find_path(self, source: str, target: str) -> GraphSearchResult:
        """BFS shortest path."""
        from collections import deque

        queue = deque([(source.lower(), [source])])
        visited = {source.lower()}
        adj: dict[str, list[tuple[str, GraphEdge]]] = {}

        for edge in self.edges:
            s, t = edge.source.lower(), edge.target.lower()
            adj.setdefault(s, []).append((edge.target, edge))
            adj.setdefault(t, []).append((edge.source, edge))

        while queue:
            current, path = queue.popleft()
            if current == target.lower():
                nodes = [self.nodes.get(n.lower(), GraphNode(name=n, type="")) for n in path]
                edges = []
                for i in range(len(path) - 1):
                    for e in self.edges:
                        if (e.source.lower() == path[i].lower() and e.target.lower() == path[i+1].lower()) or \
                           (e.target.lower() == path[i].lower() and e.source.lower() == path[i+1].lower()):
                            edges.append(e)
                            break
                return GraphSearchResult(nodes=nodes, edges=edges, paths=[path])

            for neighbor, edge in adj.get(current, []):
                nl = neighbor.lower()
                if nl not in visited:
                    visited.add(nl)
                    queue.append((nl, path + [neighbor]))

        return GraphSearchResult()
