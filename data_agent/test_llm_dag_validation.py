import json

import pandas as pd


def test_score_dag_edges_reports_edge_metrics():
    from data_agent.experiments.llm_dag_validation import score_dag_edges

    metrics = score_dag_edges(
        reference_edges={("A", "B"), ("B", "C")},
        predicted_edges={("A", "B"), ("C", "B"), ("X", "Y")},
    )

    assert metrics["true_positive_edges"] == 1
    assert metrics["n_reference_edges"] == 2
    assert metrics["n_predicted_edges"] == 3
    assert metrics["edge_precision"] == 1 / 3
    assert metrics["edge_recall"] == 1 / 2
    assert round(metrics["edge_f1"], 6) == round(0.4, 6)
    assert metrics["structural_hamming_distance"] == 3


def test_pairwise_jaccard_stability_averages_repeated_runs():
    from data_agent.experiments.llm_dag_validation import pairwise_jaccard_stability

    stability = pairwise_jaccard_stability(
        [
            {("A", "B"), ("B", "C")},
            {("A", "B")},
            {("A", "B"), ("B", "C")},
        ]
    )

    assert round(stability, 6) == round((0.5 + 1.0 + 0.5) / 3.0, 6)


def test_reference_suite_has_enough_cases_and_complete_fields():
    from data_agent.experiments.llm_dag_validation import build_reference_cases

    cases = build_reference_cases()

    assert len(cases) >= 20
    ids = {case.case_id for case in cases}
    assert len(ids) == len(cases)
    for case in cases:
        assert case.prompt
        assert case.exposure
        assert case.outcome
        assert len(case.reference_edges) >= 2


def test_run_llm_dag_validation_writes_contract_files(tmp_path):
    from data_agent.experiments.llm_dag_validation import (
        build_reference_cases,
        run_llm_dag_validation,
    )

    manifest = run_llm_dag_validation(
        output_dir=tmp_path,
        cases=build_reference_cases()[:3],
        n_repeats=2,
        generators=("structured_prompt_proxy", "minimal_template_baseline"),
    )

    expected_files = {
        "validation_csv": tmp_path / "llm_dag_validation.csv",
        "examples_md": tmp_path / "llm_dag_examples.md",
        "manifest_json": tmp_path / "llm_dag_validation_manifest.json",
        "details_json": tmp_path / "llm_dag_validation_details.json",
    }
    for key, path in expected_files.items():
        assert manifest[key] == str(path)
        assert path.exists()

    validation = pd.read_csv(expected_files["validation_csv"])
    required_columns = {
        "prompt_id",
        "generator",
        "run",
        "edge_precision",
        "edge_recall",
        "edge_f1",
        "structural_hamming_distance",
        "jaccard_stability",
        "status",
    }
    assert required_columns.issubset(validation.columns)
    assert set(validation["generator"]) == {
        "structured_prompt_proxy",
        "minimal_template_baseline",
    }
    assert validation["prompt_id"].nunique() == 3
    assert validation["run"].nunique() == 2

    examples = expected_files["examples_md"].read_text(encoding="utf-8")
    assert "Reference DAG" in examples
    assert "Generated DAG" in examples

    details = json.loads(expected_files["details_json"].read_text(encoding="utf-8"))
    assert details
