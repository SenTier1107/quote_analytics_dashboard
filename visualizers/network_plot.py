import platform
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.font_manager as fm
import networkx as nx

from analyzers.network import get_tag_cooccurrence_pairs


def set_korean_font():
    system = platform.system()
    if system == "Windows":
        plt.rcParams["font.family"] = "Malgun Gothic"
    else:
        try:
            fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
            plt.rcParams["font.family"] = "NanumGothic"
        except Exception:
            plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()


def create_tag_network_figure(limit=30):
    pairs = get_tag_cooccurrence_pairs(limit=limit)
    fig, ax = plt.subplots(figsize=(12, 8))

    if not pairs:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax.axis("off")
        plt.close(fig)
        return fig

    graph = nx.Graph()
    for pair in pairs:
        graph.add_edge(pair["tag1"], pair["tag2"], weight=pair["count"])

    pos = nx.spring_layout(graph, seed=42, k=1.5)

    degrees    = dict(graph.degree())
    max_degree = max(degrees.values()) if degrees else 1
    node_sizes  = [300 + degrees[node] * 250 for node in graph.nodes()]

    # 주황 계열 노드 색상
    node_colors = [
        cm.YlOrRd(0.3 + 0.7 * degrees[node] / max_degree)
        for node in graph.nodes()
    ]

    weights     = [graph[u][v]["weight"] for u, v in graph.edges()]
    max_weight  = max(weights) if weights else 1
    edge_widths = [0.5 + w * 0.3 for w in weights]
    edge_colors = [(0.9, 0.5, 0.1, 0.2 + 0.6 * w / max_weight) for w in weights]

    nx.draw_networkx_nodes(
        graph, pos, ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        linewidths=1.5,
        edgecolors="white"
    )
    nx.draw_networkx_edges(
        graph, pos, ax=ax,
        width=edge_widths,
        edge_color=edge_colors
    )
    nx.draw_networkx_labels(
        graph, pos, ax=ax,
        font_size=8,
        font_weight="bold",
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.6, edgecolor="none")
    )

    ax.set_title("태그 동시출현 네트워크", fontsize=14, fontweight="bold", pad=12)
    ax.axis("off")

    for degree, label in [(1, "연결 적음"), (5, "연결 많음")]:
        ax.scatter([], [], s=300 + degree * 250,
                   c="darkorange", alpha=0.7, label=label)
    ax.legend(scatterpoints=1, frameon=False, labelspacing=1, loc="lower left", fontsize=8)

    fig.tight_layout()
    plt.close(fig)
    return fig