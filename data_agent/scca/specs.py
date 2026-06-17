from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StudySpec:
    """Explicit causal study configuration for an SCCA run."""

    name: str
    unit_id: str
    exposure: str
    outcome: str
    baseline_outcome: str | None = None
    population: str | None = None
    confounders: tuple[str, ...] = field(default_factory=tuple)
    context_columns: tuple[str, ...] = field(default_factory=tuple)
    coordinate_columns: tuple[str, str] | None = None
    subgroup_column: str | None = None

    @classmethod
    def snow8_default(cls) -> "StudySpec":
        return cls(
            name="south_london_cholera_supplier",
            unit_id="sub_ID",
            exposure="perc_sou",
            outcome="rate1854",
            baseline_outcome="rate1849",
            population="pop1854",
            confounders=("rate1849", "pop_house", "pop1851"),
            context_columns=("d_sou", "d_lam", "d_pump", "d_thames", "d_unasc"),
            subgroup_column="district",
        )


@dataclass(frozen=True)
class SCCAPaths:
    """Output paths for one SCCA experiment run."""

    output_dir: Path

    def ensure(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_profile(self) -> Path:
        return self.output_dir / "data_profile.json"

    @property
    def variable_candidates(self) -> Path:
        return self.output_dir / "variable_candidates.csv"

    @property
    def context_features(self) -> Path:
        return self.output_dir / "context_features.csv"

    @property
    def context_manifest(self) -> Path:
        return self.output_dir / "context_feature_manifest.json"

    @property
    def design_plan(self) -> Path:
        return self.output_dir / "design_plan.json"

    @property
    def effect_estimates(self) -> Path:
        return self.output_dir / "effect_estimates.csv"

    @property
    def erf_curve(self) -> Path:
        return self.output_dir / "erf_curve.csv"

    @property
    def model_diagnostics(self) -> Path:
        return self.output_dir / "model_diagnostics.json"

    @property
    def balance_summary(self) -> Path:
        return self.output_dir / "balance_summary.csv"

    @property
    def overlap_summary(self) -> Path:
        return self.output_dir / "overlap_summary.json"

    @property
    def spatial_robustness(self) -> Path:
        return self.output_dir / "spatial_robustness.csv"

    @property
    def credibility_report(self) -> Path:
        return self.output_dir / "credibility_report.json"

    @property
    def analysis_report(self) -> Path:
        return self.output_dir / "analysis_report.md"

    @property
    def manifest(self) -> Path:
        return self.output_dir / "manifest.json"
