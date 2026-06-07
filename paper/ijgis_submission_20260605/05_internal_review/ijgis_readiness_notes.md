# IJGIS Readiness Notes

## Fit

IJGIS is the best target for the current manuscript shape. The paper is a GIScience methods manuscript rather than a pure remote sensing, urban planning, or machine learning paper. Its core audience is researchers working on spatial analysis, geospatial AI, spatial decision support, and causal reasoning in geographic systems.

## Strong Points

- Clear GIScience problem: spatial confounding makes causal inference fragile in geographic settings.
- Integrated framework across statistical estimation, LLM reasoning, and world-model simulation.
- Multiple causal methods in one operational GIS agent platform.
- Real-world Chongqing urban heat island case gives policy relevance.
- The sign reversal from naive association to matched ATT is a strong narrative result.

## Main Risks Before IJGIS Submission

1. GeoFM claim is currently stronger than the real-world evidence.
   - The abstract frames AlphaEarth/GeoFM embeddings as central infrastructure.
   - The real-world case says AlphaEarth embeddings were not used for inland China and Sentinel-2 plus DEM features were substituted.
   - Reviewers may see this as a mismatch between contribution and evidence.

2. Synthetic validations may look too easy.
   - Six synthetic scenarios are useful for implementation checking.
   - They do not prove robustness on real geographic policy problems.
   - The manuscript should explicitly describe them as controlled validation cases.

3. LLM causal reasoning needs evaluation.
   - Angle B is currently plausible but mostly illustrative.
   - IJGIS reviewers may ask how DAG validity, hallucination risk, and prompt sensitivity are assessed.

4. The Chongqing causal claim needs stronger uncertainty treatment.
   - MODIS LST is coarse relative to building footprints.
   - Spatial autocorrelation, interference, and local unobserved confounding should be addressed.
   - Add placebo tests, spatial blocking, or sensitivity analysis if possible.

## Recommended IJGIS Revision Path

1. Keep IJGIS as the target journal.
2. Reframe the manuscript as "spatial-context-augmented causal inference" unless true GeoFM features are added to the real-world case.
3. Add ablations:
   - Coordinates only
   - Conventional covariates
   - Sentinel-2 plus DEM features
   - GeoFM embeddings, if available
4. Add at least one robustness section for spatial dependence and hidden confounding.
5. Move implementation line counts out of the abstract or make them secondary; IJGIS reviewers will value methodological evidence more than code volume.
