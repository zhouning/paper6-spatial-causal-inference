# LLM DAG Validation Examples

## psm_park_price

Prompt: How does park proximity affect housing price?

### Reference DAG

- `income -> housing_price`
- `income -> park_proximity`
- `park_proximity -> housing_price`
- `school_quality -> housing_price`

### Generated DAG

- `income -> housing_price`
- `income -> park_proximity`
- `park_proximity -> housing_price`
- `school_quality -> housing_price`

## psm_school_green

Prompt: How does urban green space affect PM2.5?

### Reference DAG

- `green_space -> pm25`
- `industrial_emissions -> pm25`
- `population_density -> green_space`
- `population_density -> pm25`

### Generated DAG

- `green_space -> pm25`
- `industrial_emissions -> pm25`
- `population_density -> green_space`
- `population_density -> pm25`

## did_pm25_restriction

Prompt: How do traffic restrictions affect PM2.5?

### Reference DAG

- `economic_activity -> pm25`
- `economic_activity -> traffic_restriction`
- `seasonality -> pm25`
- `traffic_restriction -> pm25`

### Generated DAG

- `economic_activity -> pm25`
- `economic_activity -> traffic_restriction`
- `seasonality -> pm25`
- `traffic_restriction -> pm25`

## did_uhi_policy

Prompt: How does cool-roof policy affect land surface temperature?

### Reference DAG

- `cool_roof_policy -> lst`
- `district_income -> cool_roof_policy`
- `district_income -> lst`
- `elevation -> lst`

### Generated DAG

- `cool_roof_policy -> lst`
- `district_income -> cool_roof_policy`
- `district_income -> lst`
- `elevation -> lst`

## erf_pollution_health

Prompt: How does pollution exposure affect health score?

### Reference DAG

- `age_structure -> health_score`
- `income -> health_score`
- `income -> pollution_exposure`
- `pollution_exposure -> health_score`

### Generated DAG

- `age_structure -> health_score`
- `income -> health_score`
- `income -> pollution_exposure`
- `pollution_exposure -> health_score`

