# Air Quality & Environmental Diagnostics

An interactive Streamlit dashboard for exploring air-quality data by city, time period, and pollutant. The app retrieves data from the Open-Meteo Air Quality API and presents charts, summary metrics, health context, emission sources, and targeted urban-planning interventions.

## Features

- Search for and confirm a city using the Open-Meteo Geocoding API
- Analyze current conditions, the past 7 days, the current meteorological season, or a custom historical date range
- Select PM2.5, PM10, NO2, O3, CO, SO2, and Overall US AQI
- View data in a table and an ASCII screening plot
- Choose one of three visualizations:
  - Bar chart comparing pollutant concentrations with WHO references
  - Line chart showing pollutant values over time
  - Radar chart showing values as a percentage of WHO references
- Generate an environmental report covering:
  - Observed values and screening results
  - Anthropogenic and natural emission sources
  - Public-health and ecosystem risks
  - Two targeted policy or urban-planning interventions

## Requirements

- Python 3.9 or newer
- Internet access for the Open-Meteo APIs

## Installation

1. Clone the repository and move into the project directory:

   ```bash
   git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   cd Air_Quality_Sample
   ```

2. Create and activate a virtual environment:

   **Windows PowerShell**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the App

Start the Streamlit application with:

```bash
streamlit run air_quality_app.py
```

Streamlit will open the dashboard in your browser. If it does not open automatically, visit the local URL shown in the terminal, usually `http://localhost:8501`.

## How to Use

1. Enter a city and select the matching result.
2. Choose a time period.
3. Select one or more air-quality parameters.
4. Select a visualization.
5. Run the analysis to retrieve the dataset and generate the report.

## Data Sources

- City coordinates: [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- Air-quality observations and US AQI: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- Health-based comparison values: [WHO Global Air Quality Guidelines](https://www.who.int/publications/i/item/9789240034228)

## Methodology

For historical data, the dashboard calculates:

- Daily means for PM2.5, PM10, NO2, CO, and SO2
- The daily maximum 8-hour rolling mean for O3
- The mean of returned US AQI values for Overall AQI

Current data is shown as a current snapshot. WHO values are used for screening comparisons only and are not regulatory compliance determinations or AQI scores.

## Project Structure

```text
.
├── air_quality_app.py
├── requirements.txt
└── README.md
```

## Limitations

- The app requires an active internet connection to retrieve data.
- API availability and returned data coverage depend on Open-Meteo.
- WHO guideline values depend on specific averaging periods; the dashboard provides an educational screening comparison.
- Results should not replace official local air-quality advisories, regulatory measurements, or medical advice.

## License

No license has been specified for this repository yet. Add a license file if you want others to reuse, modify, or distribute the project under defined terms.
