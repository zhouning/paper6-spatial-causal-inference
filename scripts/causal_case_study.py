"""
Real-world causal inference case study:
Building density → Urban Heat Island effect in Chongqing, China

Uses: MODIS LST + AlphaEarth GeoFM embeddings + Building footprint data
Runs: PSM (with/without GeoFM), PCA ablation, Causal Forest
"""
import sys, os, json, time
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from data_agent.experiments.chongqing_uhi_analysis import run_chongqing_uhi_analysis

BUILDING_PATH = os.path.join(
    REPO_ROOT,
    "data",
    "raw",
    "01数据样例",
    "04重庆市中心城区建筑物轮廓数据2021年",
    "中心城区建筑数据带层高.shp",
)

RESULTS_DIR = (
    Path(REPO_ROOT) / "paper" / "ijgis_submission_20260605" / "07_results"
)
ANALYSIS_SAMPLE_PATH = RESULTS_DIR / "chongqing_uhi_analysis_sample.csv"
DEFAULT_BUILDINGS_TOTAL = 107035

def banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def step1_load_buildings():
    """Load building data and create treatment variable."""
    banner("Step 1: Load buildings + create treatment")
    gdf = gpd.read_file(BUILDING_PATH)

    # Remove null geometries
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf = gdf[gdf['Floor'].notna()].copy()
    gdf['Floor'] = gdf['Floor'].astype(float)

    # Treatment: high-rise (>=10 floors) vs low-rise (<10 floors)
    gdf['treatment'] = (gdf['Floor'] >= 10).astype(int)

    # Compute centroids for spatial operations
    gdf['centroid_x'] = gdf.geometry.centroid.x
    gdf['centroid_y'] = gdf.geometry.centroid.y
    gdf['area_m2'] = gdf.geometry.area * 111000**2  # approx for degrees

    n_treated = gdf['treatment'].sum()
    n_control = len(gdf) - n_treated
    print(f"  Total: {len(gdf):,}")
    print(f"  High-rise (>=10F): {n_treated:,}")
    print(f"  Low-rise (<10F): {n_control:,}")
    print(f"  CRS: {gdf.crs}")
    return gdf


def step2_extract_modis_lst(gdf):
    """Extract MODIS LST for building centroids from GEE."""
    banner("Step 2: Extract MODIS LST (summer 2021)")
    import ee
    ee.Initialize()

    roi = ee.Geometry.Rectangle([106.2095, 29.2126, 106.8216, 29.8312])

    # Get summer mean LST
    lst_col = ee.ImageCollection('MODIS/061/MOD11A2') \
        .filterDate('2021-06-01', '2021-08-31') \
        .filterBounds(roi) \
        .select('LST_Day_1km')

    # Mean composite, convert to Celsius (scale factor 0.02, offset -273.15)
    lst_mean = lst_col.mean().multiply(0.02).subtract(273.15)

    # Sample at building centroids (use a subsample for GEE limits)
    # GEE has limits on feature collection size, so sample strategically
    sample_size = min(5000, len(gdf))
    print(f"  Sampling LST at {sample_size} building centroids (of {len(gdf):,})...")

    # Stratified sample: equal treated/control
    treated = gdf[gdf['treatment'] == 1].sample(min(sample_size // 2, len(gdf[gdf['treatment'] == 1])), random_state=42)
    control = gdf[gdf['treatment'] == 0].sample(min(sample_size // 2, len(gdf[gdf['treatment'] == 0])), random_state=42)
    sample = pd.concat([treated, control])

    # Create GEE feature collection from centroids
    features = []
    for idx, row in sample.iterrows():
        pt = ee.Geometry.Point([row['centroid_x'], row['centroid_y']])
        features.append(ee.Feature(pt, {'idx': int(idx), 'treatment': int(row['treatment'])}))

    fc = ee.FeatureCollection(features)

    # Sample LST at points
    sampled = lst_mean.sampleRegions(
        collection=fc,
        scale=1000,
        geometries=False,
    )

    # Get results
    results = sampled.getInfo()
    lst_values = {}
    for f in results['features']:
        props = f['properties']
        lst_values[props['idx']] = props.get('LST_Day_1km', None)

    sample['LST'] = sample.index.map(lst_values)
    sample = sample[sample['LST'].notna()].copy()

    print(f"  LST values retrieved: {len(sample)}")
    print(f"  LST range: {sample['LST'].min():.1f} - {sample['LST'].max():.1f} C")
    print(f"  Mean LST (treated): {sample[sample['treatment']==1]['LST'].mean():.2f} C")
    print(f"  Mean LST (control): {sample[sample['treatment']==0]['LST'].mean():.2f} C")
    print(f"  Raw diff: {sample[sample['treatment']==1]['LST'].mean() - sample[sample['treatment']==0]['LST'].mean():.2f} C")

    return sample


def step3_extract_spectral_features(sample):
    """Extract Sentinel-2 spectral indices + SRTM DEM as spatial confounders."""
    banner("Step 3: Extract spatial context (Sentinel-2 + SRTM DEM)")
    import ee
    ee.Initialize()

    roi = ee.Geometry.Rectangle([106.2095, 29.2126, 106.8216, 29.8312])

    # Sentinel-2 summer composite
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2021-06-01', '2021-08-31') \
        .filterBounds(roi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()

    # Compute spectral indices
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndbi = s2.normalizedDifference(['B11', 'B8']).rename('NDBI')
    mndwi = s2.normalizedDifference(['B3', 'B11']).rename('MNDWI')
    bsi = s2.expression(
        '((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))',
        {'B11': s2.select('B11'), 'B4': s2.select('B4'),
         'B8': s2.select('B8'), 'B2': s2.select('B2')}
    ).rename('BSI')

    # SRTM DEM
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation')
    slope = ee.Terrain.slope(dem).rename('slope')

    # Stack all features: 6 bands + 4 indices + elevation + slope = 12 features
    stack = s2.select(['B2','B3','B4','B8','B11','B12']) \
        .addBands(ndvi).addBands(ndbi).addBands(mndwi).addBands(bsi) \
        .addBands(dem).addBands(slope)

    feature_names = ['B2','B3','B4','B8','B11','B12','NDVI','NDBI','MNDWI','BSI','elevation','slope']
    print(f"  Features: {feature_names} ({len(feature_names)} dims)")

    # Sample in batches
    batch_size = 500
    all_data = {}
    indices = list(sample.index)
    n_batches = (len(indices) + batch_size - 1) // batch_size
    print(f"  Sampling at {len(sample)} points in {n_batches} batches...")

    for b in range(n_batches):
        batch_idx = indices[b * batch_size : (b + 1) * batch_size]
        batch = sample.loc[batch_idx]

        features = []
        for idx, row in batch.iterrows():
            pt = ee.Geometry.Point([row['centroid_x'], row['centroid_y']])
            features.append(ee.Feature(pt, {'idx': int(idx)}))

        fc = ee.FeatureCollection(features)

        try:
            sampled = stack.sampleRegions(collection=fc, scale=10, geometries=False)
            results = sampled.getInfo()
            for f in results['features']:
                props = f['properties']
                idx_val = props['idx']
                vec = {fn: props.get(fn, None) for fn in feature_names}
                all_data[idx_val] = vec
            print(f"    Batch {b+1}/{n_batches}: {len(results['features'])} points OK")
        except Exception as e:
            print(f"    Batch {b+1}/{n_batches}: FAILED ({e})")
        time.sleep(1)

    # Add columns
    feat_df = pd.DataFrame.from_dict(all_data, orient='index')
    # Rename to rs_ prefix for clarity
    feat_df.columns = [f'rs_{c}' for c in feat_df.columns]
    sample = sample.join(feat_df, how='inner')

    # Drop rows with missing values
    rs_cols = [c for c in sample.columns if c.startswith('rs_')]
    before = len(sample)
    sample = sample.dropna(subset=rs_cols)
    print(f"  Retrieved: {len(sample)} / {before} (after dropping NaN)")
    print(f"  Feature dim: {len(rs_cols)}")
    print(f"  NDVI range: {sample['rs_NDVI'].min():.3f} - {sample['rs_NDVI'].max():.3f}")
    print(f"  NDBI range: {sample['rs_NDBI'].min():.3f} - {sample['rs_NDBI'].max():.3f}")
    print(f"  Elevation range: {sample['rs_elevation'].min():.0f} - {sample['rs_elevation'].max():.0f}m")

    return sample


def _normalize_analysis_sample(sample):
    """Normalize historical script column names for the reusable analysis module."""
    prepared = sample.copy()
    if "floor" not in prepared.columns and "Floor" in prepared.columns:
        prepared["floor"] = pd.to_numeric(prepared["Floor"], errors="coerce")
    elif "floor" in prepared.columns:
        prepared["floor"] = pd.to_numeric(prepared["floor"], errors="coerce")
    if "treatment" not in prepared.columns and "floor" in prepared.columns:
        prepared["treatment"] = (prepared["floor"] >= 10).astype(int)
    if "area_m2" not in prepared.columns and "area_sqm" in prepared.columns:
        prepared["area_m2"] = prepared["area_sqm"]
    if "LST" not in prepared.columns and "lst" in prepared.columns:
        prepared["LST"] = prepared["lst"]
    return prepared


def _minmax(series):
    values = pd.to_numeric(series, errors="coerce")
    span = values.max() - values.min()
    if not np.isfinite(span) or abs(span) < 1e-12:
        return pd.Series(np.zeros(len(values)), index=values.index)
    return (values - values.min()) / span


def _build_fallback_analysis_sample(gdf, fallback_reason, sample_size=5000):
    """Create a clearly labeled smoke sample when GEE extraction is unavailable."""
    banner("Fallback: synthetic smoke sample for pipeline verification")
    rng = np.random.default_rng(42)
    treated = gdf[gdf["treatment"] == 1]
    control = gdf[gdf["treatment"] == 0]
    n_each = min(sample_size // 2, len(treated), len(control))
    sample = pd.concat(
        [
            treated.sample(n=n_each, random_state=42),
            control.sample(n=n_each, random_state=42),
        ],
        ignore_index=False,
    ).copy()
    sample = _normalize_analysis_sample(sample)
    x_norm = _minmax(sample["centroid_x"])
    y_norm = _minmax(sample["centroid_y"])
    area_norm = _minmax(sample["area_m2"])
    floor_norm = _minmax(sample["floor"])

    sample["rs_elevation"] = 180 + 260 * y_norm + 30 * x_norm
    sample["rs_slope"] = 2 + 18 * area_norm
    sample["rs_NDVI"] = 0.55 - 0.18 * x_norm - 0.05 * floor_norm
    sample["rs_NDBI"] = 0.08 + 0.28 * floor_norm + 0.08 * x_norm
    sample["rs_MNDWI"] = -0.12 + 0.08 * y_norm
    sample["rs_BSI"] = 0.05 + 0.16 * area_norm + 0.04 * floor_norm
    sample["rs_B2"] = 0.10 + 0.03 * x_norm
    sample["rs_B3"] = 0.12 + 0.04 * y_norm
    sample["rs_B4"] = 0.14 + 0.03 * floor_norm
    sample["rs_B8"] = 0.22 + 0.05 * sample["rs_NDVI"]
    sample["rs_B11"] = 0.25 + 0.04 * sample["rs_NDBI"]
    sample["rs_B12"] = 0.27 + 0.03 * sample["rs_BSI"]
    sample["LST"] = (
        34.0
        - 0.004 * sample["rs_elevation"]
        + 0.55 * sample["treatment"]
        + 1.2 * sample["rs_NDBI"]
        - 0.6 * sample["rs_NDVI"]
        + rng.normal(0, 0.35, len(sample))
    )
    sample.attrs["fallback_reason"] = str(fallback_reason)
    print(f"  GEE extraction failed; generated fallback smoke sample: {fallback_reason}")
    print("  This output is for pipeline verification, not final IJGIS evidence.")
    return sample


def _save_analysis_sample(sample):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if hasattr(sample, "geometry"):
        sample.drop(columns=["geometry"], errors="ignore").to_csv(
            ANALYSIS_SAMPLE_PATH,
            index=False,
        )
    else:
        sample.to_csv(ANALYSIS_SAMPLE_PATH, index=False)
    return ANALYSIS_SAMPLE_PATH


def run_chongqing_uhi_case_study(
    *,
    analysis_sample_csv=None,
    allow_fallback=True,
    output_dir=RESULTS_DIR,
    n_bootstrap=500,
    n_spatial_bootstrap=500,
):
    """Run extraction plus the reusable Chongqing UHI analysis suite."""
    banner("Real-World Causal Case Study: Building Density -> UHI")
    print("  Study area: Chongqing central urban districts")
    print("  Treatment: high-rise (>=10 floors) vs low-rise (<10 floors)")
    print("  Outcome: MODIS Land Surface Temperature (Summer 2021)")
    print("  Confounders: location, area, Sentinel-2, and DEM features")

    t0 = time.time()
    fallback_reason = None
    if analysis_sample_csv is not None:
        sample_path = Path(analysis_sample_csv)
        sample = _normalize_analysis_sample(pd.read_csv(sample_path))
        gdf = sample
        buildings_total = DEFAULT_BUILDINGS_TOTAL
        data_source = "provided_analysis_sample"
        print(f"  Reusing analysis sample: {sample_path}")
    else:
        gdf = step1_load_buildings()
        buildings_total = int(len(gdf))
        data_source = "gee_modis_sentinel_srtm"
        try:
            sample = step2_extract_modis_lst(gdf)
            sample = step3_extract_spectral_features(sample)
            sample = _normalize_analysis_sample(sample)
        except Exception as exc:
            if not allow_fallback:
                raise
            fallback_reason = str(exc)
            data_source = "synthetic_fallback_smoke"
            sample = _build_fallback_analysis_sample(gdf, fallback_reason)
        sample_path = _save_analysis_sample(sample)
    manifest = run_chongqing_uhi_analysis(
        sample,
        output_dir=output_dir,
        threshold=10,
        caliper=0.2,
        n_bootstrap=n_bootstrap,
        n_spatial_bootstrap=n_spatial_bootstrap,
        random_state=42,
        outcome_col="LST",
        metadata={
            "study": "Building density -> UHI in Chongqing",
            "buildings_total": buildings_total,
            "analysis_sample_csv": str(sample_path),
            "data_source": data_source,
            "fallback_reason": fallback_reason,
            "gee_required_for_final_evidence": bool(fallback_reason),
        },
    )

    elapsed = time.time() - t0
    legacy_results = {
        "study": "Building density -> UHI in Chongqing",
        "data": {
            "buildings_total": buildings_total,
            "sample_size": int(len(sample)),
            "treatment_threshold": ">=10 floors",
            "data_source": data_source,
            "fallback_reason": fallback_reason,
        },
        "analysis_manifest": manifest,
        "elapsed_seconds": round(elapsed, 1),
    }
    report_path = os.path.join(os.path.dirname(__file__), "causal_case_study_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(legacy_results, f, ensure_ascii=False, indent=2, default=str)

    banner("Summary")
    print(f"  Total time: {elapsed:.0f}s")
    print(f"  Analysis sample saved: {sample_path}")
    print(f"  Manifest saved: {manifest['manifest_json']}")
    print(f"  Legacy summary saved: {report_path}")
    return manifest


def step4_psm_analysis(sample):
    """Run PSM with and without GeoFM augmentation."""
    banner("Step 4: Propensity Score Matching")
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.neighbors import NearestNeighbors

    results = {}

    # Observed confounders
    obs_confounders = ['centroid_x', 'centroid_y', 'area_m2']
    rs_cols = [c for c in sample.columns if c.startswith('rs_')]

    for label, confounders in [
        ("No RS features (3 covariates)", obs_confounders),
        (f"With RS features ({3 + len(rs_cols)} covariates)", obs_confounders + rs_cols),
    ]:
        print(f"\n  --- PSM: {label} ---")
        X = sample[confounders].values
        T = sample['treatment'].values
        Y = sample['LST'].values

        # Fit propensity score model
        ps_model = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1,
            ccp_alpha=0.01,  # cost-complexity pruning
            random_state=42,
        )
        ps_model.fit(X, T)
        ps = ps_model.predict_proba(X)[:, 1]

        # Nearest-neighbor matching on propensity score
        treated_idx = np.where(T == 1)[0]
        control_idx = np.where(T == 0)[0]

        nn = NearestNeighbors(n_neighbors=1, metric='euclidean')
        nn.fit(ps[control_idx].reshape(-1, 1))
        distances, indices = nn.kneighbors(ps[treated_idx].reshape(-1, 1))
        matched_control_idx = control_idx[indices.flatten()]

        # ATT = mean(Y_treated) - mean(Y_matched_control)
        att = Y[treated_idx].mean() - Y[matched_control_idx].mean()

        # Bootstrap CI
        n_boot = 1000
        boot_atts = []
        for _ in range(n_boot):
            boot_idx = np.random.choice(len(treated_idx), len(treated_idx), replace=True)
            boot_att = Y[treated_idx[boot_idx]].mean() - Y[matched_control_idx[boot_idx]].mean()
            boot_atts.append(boot_att)

        ci_lo = np.percentile(boot_atts, 2.5)
        ci_hi = np.percentile(boot_atts, 97.5)
        se = np.std(boot_atts)

        # Balance check (SMD)
        max_smd = 0
        for j in range(X.shape[1]):
            smd = abs(X[treated_idx, j].mean() - X[matched_control_idx, j].mean()) / (X[treated_idx, j].std() + 1e-8)
            max_smd = max(max_smd, smd)

        print(f"  ATT = {att:+.2f} C")
        print(f"  95% CI: [{ci_lo:+.2f}, {ci_hi:+.2f}]")
        print(f"  SE = {se:.3f}")
        print(f"  Max SMD after matching: {max_smd:.3f}")

        results[label] = {
            "ATT": round(att, 4),
            "CI_low": round(ci_lo, 4),
            "CI_high": round(ci_hi, 4),
            "SE": round(se, 4),
            "max_SMD": round(max_smd, 4),
            "n_treated": len(treated_idx),
            "n_control_matched": len(matched_control_idx),
        }

    # Bias reduction
    keys = list(results.keys())
    att_baseline = results[keys[0]]["ATT"]
    att_augmented = results[keys[1]]["ATT"]
    if abs(att_baseline) > 0.001:
        bias_change = abs(att_baseline - att_augmented) / abs(att_baseline) * 100
    else:
        bias_change = 0
    print(f"\n  Effect change from RS augmentation: {bias_change:.1f}%")
    results["bias_change_pct"] = round(bias_change, 1)

    return results


def step5_pca_ablation(sample):
    """PCA ablation: reduce 64D to top-k components."""
    banner("Step 5: PCA Ablation Study")
    from sklearn.decomposition import PCA
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.neighbors import NearestNeighbors

    rs_cols = [c for c in sample.columns if c.startswith('rs_')]
    X_emb = sample[rs_cols].values

    # PCA
    pca = PCA(n_components=min(0.95, len(rs_cols) - 1))  # retain 95% variance
    X_pca = pca.fit_transform(X_emb)
    k = X_pca.shape[1]
    print(f"  PCA: 64D -> {k}D (95% variance retained)")
    print(f"  Explained variance ratio: {pca.explained_variance_ratio_.sum():.3f}")

    # PSM with PCA components
    obs_confounders = ['centroid_x', 'centroid_y', 'area_m2']
    X_obs = sample[obs_confounders].values
    X_combined = np.hstack([X_obs, X_pca])

    T = sample['treatment'].values
    Y = sample['LST'].values

    ps_model = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    ps_model.fit(X_combined, T)
    ps = ps_model.predict_proba(X_combined)[:, 1]

    treated_idx = np.where(T == 1)[0]
    control_idx = np.where(T == 0)[0]

    nn = NearestNeighbors(n_neighbors=1)
    nn.fit(ps[control_idx].reshape(-1, 1))
    _, indices = nn.kneighbors(ps[treated_idx].reshape(-1, 1))
    matched_control_idx = control_idx[indices.flatten()]

    att_pca = Y[treated_idx].mean() - Y[matched_control_idx].mean()

    # Bootstrap CI
    boot_atts = [Y[treated_idx[np.random.choice(len(treated_idx), len(treated_idx), replace=True)]].mean() -
                 Y[matched_control_idx[np.random.choice(len(matched_control_idx), len(matched_control_idx), replace=True)]].mean()
                 for _ in range(1000)]
    ci_lo, ci_hi = np.percentile(boot_atts, [2.5, 97.5])

    print(f"  ATT (PCA-{k}): {att_pca:+.2f} C")
    print(f"  95% CI: [{ci_lo:+.2f}, {ci_hi:+.2f}]")

    return {"k": k, "ATT": round(att_pca, 4), "CI_low": round(ci_lo, 4), "CI_high": round(ci_hi, 4)}


def step6_causal_forest(sample):
    """Causal Forest for heterogeneous treatment effects."""
    banner("Step 6: Causal Forest (CATE heterogeneity)")
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import KFold

    obs_confounders = ['centroid_x', 'centroid_y', 'area_m2']
    rs_cols = [c for c in sample.columns if c.startswith('rs_')]
    feature_cols = obs_confounders + rs_cols

    X = sample[feature_cols].values
    T = sample['treatment'].values
    Y = sample['LST'].values

    # T-learner: separate models for treated and control
    treated_mask = T == 1
    control_mask = T == 0

    model_t = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
    model_c = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)

    model_t.fit(X[treated_mask], Y[treated_mask])
    model_c.fit(X[control_mask], Y[control_mask])

    # CATE for all units
    cate = model_t.predict(X) - model_c.predict(X)

    sample_with_cate = sample.copy()
    sample_with_cate['CATE'] = cate

    print(f"  CATE range: {cate.min():.2f} to {cate.max():.2f} C")
    print(f"  CATE mean: {cate.mean():.2f} C")
    print(f"  CATE std: {cate.std():.2f} C")

    # Feature importance
    importances_t = model_t.feature_importances_
    importances_c = model_c.feature_importances_
    avg_imp = (importances_t + importances_c) / 2
    top5_idx = np.argsort(avg_imp)[-5:][::-1]
    print(f"  Top 5 features driving CATE heterogeneity:")
    for idx in top5_idx:
        print(f"    {feature_cols[idx]}: {avg_imp[idx]:.4f}")

    # Spatial heterogeneity: split by longitude (east vs west)
    median_x = sample['centroid_x'].median()
    east = sample_with_cate[sample_with_cate['centroid_x'] >= median_x]
    west = sample_with_cate[sample_with_cate['centroid_x'] < median_x]
    print(f"  CATE East (dense): {east['CATE'].mean():.2f} C (n={len(east)})")
    print(f"  CATE West (sparse): {west['CATE'].mean():.2f} C (n={len(west)})")

    return {
        "CATE_min": round(float(cate.min()), 4),
        "CATE_max": round(float(cate.max()), 4),
        "CATE_mean": round(float(cate.mean()), 4),
        "CATE_std": round(float(cate.std()), 4),
        "CATE_east": round(float(east['CATE'].mean()), 4),
        "CATE_west": round(float(west['CATE'].mean()), 4),
        "top_features": {feature_cols[i]: round(float(avg_imp[i]), 4) for i in top5_idx},
    }


if __name__ == "__main__":
    run_chongqing_uhi_case_study()
