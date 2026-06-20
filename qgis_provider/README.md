# GeoCausal SCCA QGIS Provider Skeleton

This folder defines the QGIS integration boundary for GeoCausal SCCA.

The current module is intentionally a lightweight skeleton: it can be imported
without a QGIS runtime and delegates all algorithm work to
`geocausal.adapters.AnalysisRequest`. A full QGIS Processing plugin should add
the QGIS UI classes around this boundary, export selected layer attributes to a
CSV or GeoPackage, call `GeoCausalSCCAAlgorithm.run_from_csv`, and register the
generated `analysis_joined.csv` and report files as QGIS outputs.

No Paper 6 case-study field names or dataset paths belong in this provider.
