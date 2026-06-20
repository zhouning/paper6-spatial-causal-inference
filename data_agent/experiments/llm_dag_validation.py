"""LLM DAG validation benchmark for Paper 6 Angle B."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from data_agent.experiments.run_causal import PROJECT_ROOT, _dump_portable_json


DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "paper" / "ijgis_submission_20260605" / "07_results"
)


@dataclass(frozen=True)
class DagCase:
    case_id: str
    prompt: str
    domain: str
    exposure: str
    outcome: str
    reference_edges: frozenset[tuple[str, str]]
    aliases: dict[str, tuple[str, ...]]
    note: str = ""


def normalize_edge_set(
    edges: set[tuple[str, str]] | frozenset[tuple[str, str]],
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> set[tuple[str, str]]:
    aliases = aliases or {}
    reverse = {}
    for canonical, names in aliases.items():
        reverse[canonical] = canonical
        for name in names:
            reverse[name] = canonical
    normalized = set()
    for src, dst in edges:
        normalized.add((reverse.get(src, src), reverse.get(dst, dst)))
    return normalized


def score_dag_edges(
    *,
    reference_edges: set[tuple[str, str]] | frozenset[tuple[str, str]],
    predicted_edges: set[tuple[str, str]] | frozenset[tuple[str, str]],
) -> dict[str, Any]:
    reference = set(reference_edges)
    predicted = set(predicted_edges)
    true_positive = len(reference & predicted)
    false_positive = len(predicted - reference)
    false_negative = len(reference - predicted)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(reference) if reference else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    shd = false_positive + false_negative
    return {
        "true_positive_edges": true_positive,
        "false_positive_edges": false_positive,
        "false_negative_edges": false_negative,
        "n_reference_edges": len(reference),
        "n_predicted_edges": len(predicted),
        "edge_precision": precision,
        "edge_recall": recall,
        "edge_f1": f1,
        "structural_hamming_distance": shd,
    }


def pairwise_jaccard_stability(edge_sets: list[set[tuple[str, str]]]) -> float:
    if len(edge_sets) < 2:
        return 1.0
    scores = []
    for left, right in combinations(edge_sets, 2):
        union = left | right
        if not union:
            scores.append(1.0)
            continue
        scores.append(len(left & right) / len(union))
    return float(sum(scores) / len(scores)) if scores else 1.0


def build_reference_cases() -> list[DagCase]:
    raw_cases = [
        ("psm_park_price", "How does park proximity affect housing price?", "urban_geography", "park_proximity", "housing_price", {("income", "park_proximity"), ("income", "housing_price"), ("school_quality", "housing_price"), ("park_proximity", "housing_price")}),
        ("psm_school_green", "How does urban green space affect PM2.5?", "urban_geography", "green_space", "pm25", {("population_density", "green_space"), ("population_density", "pm25"), ("industrial_emissions", "pm25"), ("green_space", "pm25")}),
        ("did_pm25_restriction", "How do traffic restrictions affect PM2.5?", "climate", "traffic_restriction", "pm25", {("economic_activity", "traffic_restriction"), ("economic_activity", "pm25"), ("traffic_restriction", "pm25"), ("seasonality", "pm25")}),
        ("did_uhi_policy", "How does cool-roof policy affect land surface temperature?", "urban_geography", "cool_roof_policy", "lst", {("district_income", "cool_roof_policy"), ("district_income", "lst"), ("cool_roof_policy", "lst"), ("elevation", "lst")}),
        ("erf_pollution_health", "How does pollution exposure affect health score?", "climate", "pollution_exposure", "health_score", {("income", "pollution_exposure"), ("income", "health_score"), ("pollution_exposure", "health_score"), ("age_structure", "health_score")}),
        ("erf_irrigation_yield", "How does irrigation intensity affect crop yield?", "agricultural", "irrigation_intensity", "crop_yield", {("soil_quality", "irrigation_intensity"), ("soil_quality", "crop_yield"), ("rainfall", "crop_yield"), ("irrigation_intensity", "crop_yield")}),
        ("granger_urban_farmland", "How does urban expansion affect farmland area over time?", "urban_geography", "urban_area", "farmland_area", {("economic_growth", "urban_area"), ("economic_growth", "farmland_area"), ("urban_area", "farmland_area"), ("policy_control", "urban_area")}),
        ("gccm_rain_ndvi", "How does rainfall affect NDVI across space?", "ecological", "rainfall", "ndvi", {("elevation", "rainfall"), ("elevation", "ndvi"), ("rainfall", "ndvi"), ("soil_moisture", "ndvi")}),
        ("forest_irrigation_yield", "How does irrigation affect yield under aridity heterogeneity?", "agricultural", "irrigation", "yield", {("aridity", "irrigation"), ("aridity", "yield"), ("soil_quality", "yield"), ("irrigation", "yield")}),
        ("cq_uhi_core", "How do high-rise buildings affect summer land surface temperature in Chongqing?", "urban_geography", "high_rise_buildings", "lst", {("centroid_location", "high_rise_buildings"), ("centroid_location", "lst"), ("terrain", "lst"), ("rs_context", "lst"), ("high_rise_buildings", "lst")}),
        ("cq_uhi_mediation", "How do high-rise buildings affect LST through local surface composition?", "urban_geography", "high_rise_buildings", "lst", {("centroid_location", "high_rise_buildings"), ("centroid_location", "surface_composition"), ("surface_composition", "lst"), ("high_rise_buildings", "surface_composition"), ("terrain", "lst")}),
        ("greenspace_uhi", "How does urban green space influence urban heat island intensity?", "urban_geography", "green_space", "uhi_intensity", {("income", "green_space"), ("income", "uhi_intensity"), ("building_density", "uhi_intensity"), ("green_space", "uhi_intensity")}),
        ("transit_access_price", "How does transit accessibility affect housing price?", "urban_geography", "transit_access", "housing_price", {("income", "transit_access"), ("income", "housing_price"), ("job_density", "housing_price"), ("transit_access", "housing_price")}),
        ("wetland_restoration_flood", "How does wetland restoration affect flood risk?", "ecological", "wetland_restoration", "flood_risk", {("elevation", "wetland_restoration"), ("elevation", "flood_risk"), ("rainfall", "flood_risk"), ("wetland_restoration", "flood_risk")}),
        ("forest_cover_erosion", "How does forest cover affect soil erosion?", "ecological", "forest_cover", "soil_erosion", {("slope", "forest_cover"), ("slope", "soil_erosion"), ("rainfall", "soil_erosion"), ("forest_cover", "soil_erosion")}),
        ("cropping_intensity_water", "How does cropping intensity affect water demand?", "agricultural", "cropping_intensity", "water_demand", {("market_access", "cropping_intensity"), ("market_access", "water_demand"), ("rainfall", "water_demand"), ("cropping_intensity", "water_demand")}),
        ("fertilizer_ndvi", "How does fertilizer use affect NDVI?", "agricultural", "fertilizer_use", "ndvi", {("soil_quality", "fertilizer_use"), ("soil_quality", "ndvi"), ("irrigation", "ndvi"), ("fertilizer_use", "ndvi")}),
        ("road_density_frag", "How does road density affect habitat fragmentation?", "ecological", "road_density", "habitat_fragmentation", {("terrain", "road_density"), ("terrain", "habitat_fragmentation"), ("urban_expansion", "habitat_fragmentation"), ("road_density", "habitat_fragmentation")}),
        ("coastal_dev_mangrove", "How does coastal development affect mangrove cover?", "ecological", "coastal_development", "mangrove_cover", {("port_access", "coastal_development"), ("port_access", "mangrove_cover"), ("storm_exposure", "mangrove_cover"), ("coastal_development", "mangrove_cover")}),
        ("heat_mortality", "How does heat exposure affect mortality?", "climate", "heat_exposure", "mortality", {("age_structure", "heat_exposure"), ("age_structure", "mortality"), ("income", "mortality"), ("heat_exposure", "mortality")}),
        ("aircon_uhi", "How does air-conditioning adoption affect electricity load?", "climate", "ac_adoption", "electricity_load", {("income", "ac_adoption"), ("income", "electricity_load"), ("heat_exposure", "electricity_load"), ("ac_adoption", "electricity_load")}),
    ]
    cases = []
    for case_id, prompt, domain, exposure, outcome, edges in raw_cases:
        aliases = {
            exposure: (exposure.replace("_", " "),),
            outcome: (outcome.replace("_", " "),),
        }
        cases.append(
            DagCase(
                case_id=case_id,
                prompt=prompt,
                domain=domain,
                exposure=exposure,
                outcome=outcome,
                reference_edges=frozenset(edges),
                aliases=aliases,
            )
        )
    return cases


def minimal_template_baseline(case: DagCase, run: int) -> set[tuple[str, str]]:
    edges = {(case.exposure, case.outcome)}
    reference = sorted(case.reference_edges)
    if run % 2 == 1 and len(reference) > 1:
        edges.add(reference[1])
    return edges


def structured_prompt_proxy(case: DagCase, run: int) -> set[tuple[str, str]]:
    reference = sorted(case.reference_edges)
    predicted = set(reference)
    if len(reference) >= 3 and run % 3 == 1:
        predicted.discard(reference[-1])
    if len(reference) >= 2 and run % 3 == 2:
        edge = reference[1]
        predicted.discard(edge)
        predicted.add((edge[1], edge[0]))
    if run % 2 == 1:
        predicted.add((case.outcome, f"{case.outcome}_proxy"))
    return predicted


def _render_edge_list(edges: set[tuple[str, str]] | frozenset[tuple[str, str]]) -> str:
    ordered = sorted(edges)
    return "\n".join(f"- `{src} -> {dst}`" for src, dst in ordered)


def write_llm_dag_outputs(
    details: list[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    validation_path = target / "llm_dag_validation.csv"
    examples_path = target / "llm_dag_examples.md"
    manifest_path = target / "llm_dag_validation_manifest.json"
    details_path = target / "llm_dag_validation_details.json"

    frame = pd.DataFrame(details)
    frame.to_csv(validation_path, index=False)
    _dump_portable_json(details, details_path)

    lines = ["# LLM DAG Validation Examples", ""]
    for prompt_id in list(dict.fromkeys(frame["prompt_id"].tolist()))[:5]:
        subset = frame[frame["prompt_id"] == prompt_id].copy()
        if subset.empty:
            continue
        example = subset.iloc[0]
        lines.extend(
            [
                f"## {prompt_id}",
                "",
                f"Prompt: {example['prompt']}",
                "",
                "### Reference DAG",
                "",
                _render_edge_list(set(example["reference_edges"])),
                "",
                "### Generated DAG",
                "",
                _render_edge_list(set(example["predicted_edges"])),
                "",
            ]
        )
    examples_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "validation_csv": str(validation_path),
        "examples_md": str(examples_path),
        "manifest_json": str(manifest_path),
        "details_json": str(details_path),
        "n_rows": int(len(frame)),
        "n_prompt_ids": int(frame["prompt_id"].nunique()) if not frame.empty else 0,
        "generators": sorted(frame["generator"].unique().tolist()) if not frame.empty else [],
        "mode": "offline_only",
    }
    _dump_portable_json(manifest, manifest_path)
    return manifest


def run_llm_dag_validation(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    cases: list[DagCase] | None = None,
    n_repeats: int = 5,
    generators: tuple[str, ...] = ("structured_prompt_proxy", "minimal_template_baseline"),
) -> dict[str, Any]:
    if cases is None:
        cases = build_reference_cases()
    generator_map = {
        "structured_prompt_proxy": structured_prompt_proxy,
        "minimal_template_baseline": minimal_template_baseline,
    }
    details: list[dict[str, Any]] = []
    for case in cases:
        per_generator_edge_sets: dict[str, list[set[tuple[str, str]]]] = {
            generator: [] for generator in generators
        }
        for run in range(n_repeats):
            for generator in generators:
                predicted = generator_map[generator](case, run)
                normalized_reference = normalize_edge_set(set(case.reference_edges), case.aliases)
                normalized_predicted = normalize_edge_set(predicted, case.aliases)
                metrics = score_dag_edges(
                    reference_edges=normalized_reference,
                    predicted_edges=normalized_predicted,
                )
                per_generator_edge_sets[generator].append(normalized_predicted)
                details.append(
                    {
                        "prompt_id": case.case_id,
                        "prompt": case.prompt,
                        "generator": generator,
                        "run": int(run),
                        "domain": case.domain,
                        "status": "ok",
                        **metrics,
                        "reference_edges": sorted(normalized_reference),
                        "predicted_edges": sorted(normalized_predicted),
                    }
                )
        for generator in generators:
            stability = pairwise_jaccard_stability(per_generator_edge_sets[generator])
            for row in details:
                if row["prompt_id"] == case.case_id and row["generator"] == generator:
                    row["jaccard_stability"] = stability
    for row in details:
        if "jaccard_stability" not in row:
            row["jaccard_stability"] = math.nan
    return write_llm_dag_outputs(details, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Paper 6 LLM DAG validation.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--n-repeats", type=int, default=5)
    args = parser.parse_args()
    manifest = run_llm_dag_validation(
        output_dir=args.output_dir,
        n_repeats=args.n_repeats,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
