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
def eval(
    n_traces: int = typer.Option(200, "--n-traces", help="Synthetic traces to generate"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
) -> None:
    """Run the eval harness against the synthetic dataset.

    Uses FakeAgentRunner (baseline pass_rate=0.2, candidate pass_rate=0.8) and a
    keyword judge calibrated against synthetic seed examples.
    Prints a pass/fail report with significance stats and judge agreement rate.
    """
    from core.eval import (
        AgentConfig,
        EvalHarness,
        FakeAgentRunner,
        JudgeCalibrationError,
        split,
    )
    from core.testing.generator import generate_dataset

    console.print(f"Generating {n_traces} synthetic traces (seed={seed})…")
    traces = generate_dataset(n=n_traces, seed=seed)

    train, holdout = split(traces, seed=seed)
    console.print(f"  {len(train.cases)} train  ·  {len(holdout.cases)} holdout")

    if not holdout.cases:
        console.print("[red]No holdout cases — increase --n-traces.[/red]")
        raise typer.Exit(code=1)

    baseline_config = AgentConfig(prompt="baseline prompt v1", skills=("lookup_order",))
    candidate_config = AgentConfig(prompt="improved prompt v2", skills=("lookup_order", "issue_refund"))

    baseline_runner = FakeAgentRunner(pass_rate=0.2)
    candidate_runner = FakeAgentRunner(pass_rate=0.8)

    class _PairedRunner:
        """Delegates to baseline or candidate based on which config is passed."""

        def run(self, trace: object, config: AgentConfig) -> str:
            if config is baseline_config:
                return baseline_runner.run(trace, config)  # type: ignore[arg-type]
            return candidate_runner.run(trace, config)  # type: ignore[arg-type]

    class _KeywordJudge:
        """Returns 1.0 if the response contains 'resolved', 0.0 otherwise."""

        def score(self, context: str) -> float:
            return 1.0 if "resolved" in context.lower() else 0.0

    # Seed examples calibrate the judge: "resolved" responses are passes, others are fails.
    seed_contexts = ["issue resolved successfully"] * 10 + ["I cannot help with that"] * 10
    seed_labels = ["pass"] * 10 + ["fail"] * 10

    harness = EvalHarness(
        runner=_PairedRunner(),
        judge=_KeywordJudge(),
        seed_contexts=seed_contexts,
        seed_labels=seed_labels,
    )

    try:
        report = harness.evaluate(baseline_config, candidate_config, holdout)
    except JudgeCalibrationError as exc:
        console.print(f"[red bold]Judge calibration failed:[/red bold] {exc}")
        raise typer.Exit(code=1) from exc

    status = "[green bold]PASS[/green bold]" if report.passed else "[yellow bold]FAIL[/yellow bold]"
    console.print()
    console.print(f"Eval result: {status}")
    console.print(f"  Baseline score   : {report.baseline_score:.3f}")
    console.print(f"  Candidate score  : {report.candidate_score:.3f}")
    console.print(f"  Delta            : {report.significance.delta:+.3f}")
    console.print(f"  p-value (1-tail) : {report.significance.p_value:.4f}")
    console.print(f"  Sample size      : {report.significance.sample_size}")
    console.print(f"  Judge agreement  : {report.judge_agreement_rate:.1%}")


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
