"""Community detection and centrality for the codebase dependency graph.

source: ADR-0125"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx

# source: ADR-0125

_MIN_NODES_FOR_GRAPH_ANALYSIS = 2
# source: ADR-0125
_MIN_SAMPLES_FOR_STD = 2


def _build_dependency_graph(
    file_edges: list[tuple[str, str]],
    call_edges: list[tuple[str, str, str]],
) -> nx.Graph:
    """Build a weighted networkx graph from file and call edges."""
    import networkx as nx  # noqa: PLC0415 — source: ADR-0125

    g = nx.Graph()
    for src, tgt in file_edges:
        g.add_edge(src, tgt, weight=1.0)
    for src, _, tgt in call_edges:
        if g.has_edge(src, tgt):
            g[src][tgt]["weight"] += 0.5
        else:
            g.add_edge(src, tgt, weight=0.5)
    return g


def _leiden_partition(g: nx.Graph) -> dict[str, int] | None:
    """Partition g with the Leiden algorithm, or None if deps are absent.

    source: ADR-0125"""
    try:
        import igraph  # noqa: PLC0415 — source: ADR-0125
        import leidenalg  # noqa: PLC0415 — source: ADR-0125
    except ImportError:
        return None

    nodes = list(g.nodes())  # type: ignore[attr-defined]
    index = {n: i for i, n in enumerate(nodes)}
    edges = [(index[u], index[v]) for u, v in g.edges()]  # type: ignore[attr-defined]
    weights = [g[u][v]["weight"] for u, v in g.edges()]  # type: ignore[index]
    ig = igraph.Graph(n=len(nodes), edges=edges)
    partition = leidenalg.find_partition(
        ig,
        leidenalg.ModularityVertexPartition,
        weights=weights,
        seed=42,
    )
    return {nodes[i]: partition.membership[i] for i in range(len(nodes))}


def detect_communities(
    file_edges: list[tuple[str, str]],
    call_edges: list[tuple[str, str, str]],
) -> dict[str, int]:
    """Detect functional communities on the import+call graph.

    source: ADR-0125

    Returns:
        Map of file_path -> community_id.
    """
    try:
        import networkx as nx  # noqa: PLC0415 — source: ADR-0125
    except ImportError:
        return {}

    g = _build_dependency_graph(file_edges, call_edges)
    if g.number_of_nodes() < _MIN_NODES_FOR_GRAPH_ANALYSIS:
        return {n: 0 for n in g.nodes()}

    leiden = _leiden_partition(g)
    if leiden is not None:
        return leiden

    communities = nx.community.louvain_communities(g, weight="weight", seed=42)
    result: dict[str, int] = {}
    for idx, community in enumerate(communities):
        for node in community:
            result[node] = idx
    return result


def compute_centrality(
    file_edges: list[tuple[str, str]],
    call_edges: list[tuple[str, str, str]],
) -> dict[str, dict[str, float]]:
    """Compute per-node centrality on the dependency graph.

    Returns a map of file_path -> {degree, betweenness, pagerank}, each a
    normalized score in [0, 1]. Empty dict when networkx is unavailable or
    the graph has fewer than 2 nodes.

    source: ADR-0125"""
    try:
        import networkx as nx  # noqa: PLC0415 — source: ADR-0125
    except ImportError:
        return {}

    g = _build_dependency_graph(file_edges, call_edges)
    if g.number_of_nodes() < _MIN_NODES_FOR_GRAPH_ANALYSIS:
        return {}

    degree = nx.degree_centrality(g)
    betweenness = nx.betweenness_centrality(g, weight="weight", normalized=True)
    pagerank = nx.pagerank(g, weight="weight")
    return {
        node: {
            "degree": degree.get(node, 0.0),
            "betweenness": betweenness.get(node, 0.0),
            "pagerank": pagerank.get(node, 0.0),
        }
        for node in g.nodes()
    }


def detect_god_nodes(
    centrality: dict[str, dict[str, float]],
    sigma: float = 2.0,
) -> list[str]:
    """Flag "god" nodes: degree-centrality statistical outliers.

    source: ADR-0125

    Returns the god-node file paths sorted by descending degree centrality.
    """
    if len(centrality) < _MIN_SAMPLES_FOR_STD:
        return []

    degrees = [c["degree"] for c in centrality.values()]
    mean = sum(degrees) / len(degrees)
    variance = sum((d - mean) ** 2 for d in degrees) / len(degrees)
    std = variance**0.5
    if std == 0.0:
        return []

    threshold = mean + sigma * std
    gods = [node for node, scores in centrality.items() if scores["degree"] > threshold]
    return sorted(gods, key=lambda n: centrality[n]["degree"], reverse=True)
