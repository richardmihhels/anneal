from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="anneal", no_args_is_help=True, add_completion=False)
console = Console()


@app.callback()
def _root() -> None:
    """Anneal — AI agent prompt optimizer."""


@app.command()
def cluster(
    n_traces: int = typer.Option(100, "--n-traces", help="Synthetic traces to generate"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
) -> None:
    """Cluster failures in the synthetic Cascade support dataset.

    Uses TF-IDF embeddings and keyword labeling — no API keys required.
    For production use, swap in OpenAIEmbedder and AnthropicLabeler.
    """
    from core.clustering import ClusterPipeline, FakeJudge, FakeLabeler, TFIDFEmbedder
    from core.testing.generator import generate_dataset

    console.print(f"Generating {n_traces} synthetic traces (seed={seed})…")
    traces = generate_dataset(n=n_traces, seed=seed)

    n_failures = sum(1 for t in traces if t.outcome == "failure")
    n_unknown = sum(1 for t in traces if t.outcome == "unknown")
    console.print(
        f"  {n_failures} failures  ·  {n_unknown} ambiguous  ·  {len(traces) - n_failures - n_unknown} successes"
    )

    pipeline = ClusterPipeline(
        embedder=TFIDFEmbedder(),
        judge=FakeJudge(),
        labeler=FakeLabeler(),
    )

    console.print("Embedding and clustering…")
    clusters = pipeline.run(traces)

    if not clusters:
        console.print("[yellow]No clusters found.[/yellow]")
        raise typer.Exit(code=1)

    total_clustered = sum(c.size for c in clusters)
    noise = n_failures - total_clustered

    table = Table(
        title=f"Failure Clusters  —  {n_failures} failures, {len(clusters)} clusters",
        show_header=True,
        header_style="bold",
        box=None,
        pad_edge=False,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Description", min_width=45)
    table.add_column("Count", justify="right", width=6)
    table.add_column("% of failures", justify="right", width=14)

    for rank, c in enumerate(sorted(clusters, key=lambda x: -x.size), 1):
        pct = 100 * c.size / n_failures if n_failures else 0.0
        table.add_row(str(rank), c.description, str(c.size), f"{pct:.1f}%")

    console.print()
    console.print(table)
    console.print(f"\n[dim]{len(clusters)} clusters  ·  {noise} noise points discarded[/dim]")
