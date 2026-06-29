# EPA AirData / Green Book Benchmark Inputs

This directory contains the small public-source inputs used by the Paper6 EPA
nonattainment policy-structure benchmark. They were downloaded in the Windows
workspace for the `scca-epa-airdata-benchmark` branch so the benchmark can run
from a clean checkout without depending on local browser/download cache paths.

The benchmark currently uses EPA Green Book PM2.5 county-year nonattainment
structure plus Census county geometry. AQS AirData downloads timed out in the
original environment, so the committed benchmark remains a semi-synthetic
known-effect validation on real EPA policy geography, not a completed
observational AQS policy-effect estimate.

## Files

- `nayro.xls`
  - SHA256: `84b100ef6174e77b2566e9a40a4c8cfa8c0b68c67d85d0f4bf1c909c3ac7e355`
  - Role: EPA Green Book nonattainment status source used by the benchmark.
- `cb_2024_us_county_500k.zip`
  - SHA256: `da4051717caec55c75e3748c3608c2a3dbde8d1ff401bbaf4f952e3c3fb63ef1`
  - Role: U.S. Census county cartographic boundary geometry used for centroids and adjacency.
- `areadata.xls`
  - SHA256: `2df5195236446d635bd0f80326c61246d8c684c6c9b8989f7883a2f1bfaa0d8c`
  - Role: downloaded EPA Green Book companion table retained for benchmark provenance.
- `phistory.xls`
  - SHA256: `7fa8ea6fedbbcafe0d0ae8b41104db71b36a96a838137b55d3d4e58c8dc381e4`
  - Role: downloaded EPA Green Book companion table retained for benchmark provenance.

## Reproduction Command

From the repository root:

```bash
python -m data_agent.experiments.epa_airdata_benchmark \
  --raw-dir data/raw/epa_airdata \
  --output-dir paper/ijgis_submission_20260605/07_results/epa_nonattainment_airdata
```