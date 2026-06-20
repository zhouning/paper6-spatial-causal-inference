# World Model Holdout Validation Report

- Evaluation mode: `offline_fixture_proxy`
- Claim guidance: `scenario_simulation_only`

## Best Baseline

- Baseline: `persistence`
- Horizon: `1`
- RMSE: `0.06733817309807556`
- Mean cosine similarity: `0.8548982542020358`

## Holdout Metrics

- `persistence` horizon `1`: status `ok`, RMSE `0.06733817309807556`, decoded accuracy `0.859375`
- `mean_delta` horizon `1`: status `ok`, RMSE `0.06775566503457145`, decoded accuracy `0.859375`
- `ridge_transition` horizon `1`: status `ok`, RMSE `0.07469413103683638`, decoded accuracy `0.859375`
- `markov_transition` horizon `1`: status `ok`, RMSE `0.07542916861245143`, decoded accuracy `0.859375`
- `world_model_baseline` horizon `1`: status `ok`, RMSE `0.0798815616437838`, decoded accuracy `0.859375`
- `persistence` horizon `2`: status `ok`, RMSE `0.0954259951075429`, decoded accuracy `0.71875`
- `mean_delta` horizon `2`: status `ok`, RMSE `0.09620379824033969`, decoded accuracy `0.71875`
- `ridge_transition` horizon `2`: status `ok`, RMSE `0.10622909062378934`, decoded accuracy `0.71875`
- `markov_transition` horizon `2`: status `ok`, RMSE `0.10596786353907628`, decoded accuracy `0.71875`
- `world_model_baseline` horizon `2`: status `ok`, RMSE `0.1104025667737576`, decoded accuracy `0.71875`

## Scenario Calibration

- `baseline` x `0.25`: delta L2 `0.00925445342817911`, plausible `False`
- `baseline` x `0.5`: delta L2 `0.01851776038830757`, plausible `False`
- `baseline` x `1.0`: delta L2 `0.03706633223642763`, plausible `False`
- `baseline` x `2.0`: delta L2 `0.07421881157492081`, plausible `False`
- `baseline` x `4.0`: delta L2 `0.14848189095408293`, plausible `False`
- `urban_sprawl` x `0.25`: delta L2 `0.011569494953476755`, plausible `False`
- `urban_sprawl` x `0.5`: delta L2 `0.023152374979475657`, plausible `False`
- `urban_sprawl` x `1.0`: delta L2 `0.0463492829369635`, plausible `False`
- `urban_sprawl` x `2.0`: delta L2 `0.09280399495982755`, plausible `False`
- `urban_sprawl` x `4.0`: delta L2 `0.18544066612525956`, plausible `True`
- `ecological_restoration` x `0.25`: delta L2 `0.006939965275724017`, plausible `False`
- `ecological_restoration` x `0.5`: delta L2 `0.013885071924480064`, plausible `False`
- `ecological_restoration` x `1.0`: delta L2 `0.027788771528819933`, plausible `False`
- `ecological_restoration` x `2.0`: delta L2 `0.0556364594112536`, plausible `False`
- `ecological_restoration` x `4.0`: delta L2 `0.11138256395016513`, plausible `False`
