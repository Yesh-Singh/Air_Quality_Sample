
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# ============================================================
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="Air Quality & Environmental Diagnostics",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Air Quality & Environmental Diagnostics")
st.caption(
    "University Sustainability Course — Interactive Chatbot Data Run"
)

# ============================================================
# CONSTANTS
# ============================================================

AQ_VARIABLES = {
    "PM2.5": "pm2_5",
    "PM10": "pm10",
    "NO2": "nitrogen_dioxide",
    "O3": "ozone",
    "CO": "carbon_monoxide",
    "SO2": "sulphur_dioxide",
    "Overall AQI": "us_aqi",
}

DISPLAY_UNITS = {
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "NO2": "µg/m³",
    "O3": "µg/m³",
    "CO": "µg/m³",
    "SO2": "µg/m³",
    "Overall AQI": "US AQI",
}

# WHO 2021 health-based guideline values.
# These are used only for the matching averaging periods.
WHO = {
    "PM2.5": {"limit": 15.0, "unit": "µg/m³", "period": "24-hour"},
    "PM10": {"limit": 45.0, "unit": "µg/m³", "period": "24-hour"},
    "NO2": {"limit": 25.0, "unit": "µg/m³", "period": "24-hour"},
    "O3": {"limit": 100.0, "unit": "µg/m³", "period": "8-hour"},
    "CO": {"limit": 4000.0, "unit": "µg/m³", "period": "24-hour"},
    "SO2": {"limit": 40.0, "unit": "µg/m³", "period": "24-hour"},
}

SOURCES = {
    "PM2.5": {
        "Anthropogenic": "Vehicle exhaust, fuel/biomass combustion, industry, construction activity.",
        "Natural": "Windblown dust and wildfire smoke where applicable."
    },
    "PM10": {
        "Anthropogenic": "Road dust, construction, quarrying and industrial dust.",
        "Natural": "Windblown soil/mineral dust and wildfire ash where applicable."
    },
    "NO2": {
        "Anthropogenic": "Road traffic, power generation and industrial combustion.",
        "Natural": "Lightning and soil microbial processes."
    },
    "O3": {
        "Anthropogenic": "Not emitted directly; formed from NOx and VOC precursors from traffic, industry and solvent use.",
        "Natural": "Biogenic VOCs, lightning and stratospheric influence can contribute."
    },
    "CO": {
        "Anthropogenic": "Incomplete combustion from vehicles, generators, industry and biomass burning.",
        "Natural": "Wildfires and natural atmospheric oxidation processes."
    },
    "SO2": {
        "Anthropogenic": "Coal/oil combustion, industrial processes and some metal-processing activities.",
        "Natural": "Volcanic emissions."
    },
}

HEALTH_RISKS = {
    "PM2.5": "Fine particles can penetrate deeply into the lungs and are associated with cardiovascular and respiratory health effects.",
    "PM10": "Coarse particles can irritate the airways and worsen respiratory symptoms.",
    "NO2": "NO2 can irritate the respiratory system and contributes to formation of secondary air pollutants.",
    "O3": "Ground-level ozone can irritate the respiratory system and damage vegetation.",
    "CO": "Carbon monoxide reduces the blood's oxygen-carrying capacity at sufficiently high exposure.",
    "SO2": "Sulfur dioxide can irritate the respiratory system and contributes to acid deposition.",
}

# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "step": 1,
    "city_query": "",
    "city": None,
    "latitude": None,
    "longitude": None,
    "timezone": None,
    "period": None,
    "pollutants": [],
    "visualization": None,
    "results": None,
    "df": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_app():
    for key, value in defaults.items():
        st.session_state[key] = value


# ============================================================
# API HELPERS
# ============================================================

def api_get(url, params):
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("error"):
        raise RuntimeError(data.get("reason", "API returned an error."))

    return data


def geocode_city(city_query):
    """Convert a city name into latitude/longitude using Open-Meteo."""
    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city_query,
        "count": 5,
        "language": "en",
        "format": "json",
    }

    data = api_get(url, params)

    return data.get("results", [])


def fetch_current(lat, lon):
    variables = list(AQ_VARIABLES.values())

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(variables),
        "timezone": "auto",
    }

    return api_get(url, params)


def fetch_historical(lat, lon, start_date, end_date):
    variables = list(AQ_VARIABLES.values())

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(variables),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "timezone": "auto",
    }

    return api_get(url, params)


# ============================================================
# TIME PERIOD HELPERS
# ============================================================

def current_meteorological_season(today):
    """
    Returns the current meteorological season-to-date.
    Northern Hemisphere:
      Spring = Mar-May
      Summer = Jun-Aug
      Autumn = Sep-Nov
      Winter = Dec-Feb
    """
    year = today.year
    month = today.month

    if month in (3, 4, 5):
        return date(year, 3, 1), today, "Spring"
    elif month in (6, 7, 8):
        return date(year, 6, 1), today, "Summer"
    elif month in (9, 10, 11):
        return date(year, 9, 1), today, "Autumn"
    else:
        # Winter crosses calendar years.
        if month == 12:
            return date(year, 12, 1), today, "Winter"
        return date(year - 1, 12, 1), today, "Winter"


def get_period_dates(period, custom_start=None, custom_end=None):
    today = date.today()

    if period == "Past 7 Days":
        return today - timedelta(days=6), today, "Past 7 Days"

    if period == "Seasonal Average":
        start, end, season = current_meteorological_season(today)
        return start, end, f"{season} season-to-date"

    if period == "Custom Date Range":
        return custom_start, custom_end, "Custom Date Range"

    return None, None, "Real-time/Current"


# ============================================================
# DATA CONVERSION
# ============================================================

def current_to_dataframe(data):
    current = data.get("current", {})

    if not current:
        raise ValueError("No current air-quality record was returned.")

    row = {"Time": pd.to_datetime(current.get("time"))}

    for label, api_name in AQ_VARIABLES.items():
        row[label] = current.get(api_name)

    return pd.DataFrame([row])


def historical_to_dataframe(data):
    hourly = data.get("hourly", {})

    if "time" not in hourly:
        raise ValueError("No hourly air-quality data was returned.")

    df = pd.DataFrame({
        "Time": pd.to_datetime(hourly["time"])
    })

    for label, api_name in AQ_VARIABLES.items():
        values = hourly.get(api_name)
        if values is not None:
            df[label] = values

    return df


# ============================================================
# COMPARABLE DAILY METRICS
# ============================================================

def daily_o3_8h_max(group):
    values = group["O3"].dropna().reset_index(drop=True)

    if len(values) < 8:
        return values.mean() if len(values) else None

    return values.rolling(window=8, min_periods=8).mean().max()


def build_daily_metrics(df):
    """
    Creates metrics that are closer to WHO averaging periods:
      PM2.5, PM10, NO2, CO, SO2 -> daily means
      O3 -> daily maximum 8-hour rolling mean
      Overall AQI -> daily mean
    """
    work = df.copy()

    work["Date"] = work["Time"].dt.date

    records = []

    for day, group in work.groupby("Date"):
        row = {"Date": day}

        for pollutant in ["PM2.5", "PM10", "NO2", "CO", "SO2"]:
            if pollutant in group.columns:
                row[pollutant] = group[pollutant].mean()

        if "O3" in group.columns:
            row["O3"] = daily_o3_8h_max(group)

        if "Overall AQI" in group.columns:
            row["Overall AQI"] = group["Overall AQI"].mean()

        records.append(row)

    return pd.DataFrame(records)


# ============================================================
# SUMMARY VALUES
# ============================================================

def get_summary_value(df, pollutant, is_current=False):
    if pollutant not in df.columns:
        return None

    if is_current:
        value = df[pollutant].iloc[-1]
        return float(value) if pd.notna(value) else None

    daily = build_daily_metrics(df)

    if pollutant not in daily.columns:
        return None

    value = daily[pollutant].mean()

    return float(value) if pd.notna(value) else None


def get_aqi_category(aqi):
    if aqi is None:
        return "Unavailable"

    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"

    return "Hazardous"


# ============================================================
# ASCII PLOT
# ============================================================

def make_ascii_plot(df, pollutants, is_current):
    lines = []
    lines.append("AIR QUALITY SCREENING PLOT")
    lines.append("=" * 72)

    for pollutant in pollutants:

        value = get_summary_value(df, pollutant, is_current)

        if value is None:
            continue

        if pollutant in WHO:
            limit = WHO[pollutant]["limit"]
            ratio = value / limit if limit else 0
            filled = min(40, max(1, round(ratio * 10)))

            bar = "#" * filled
            spaces = "." * (40 - filled)

            lines.append(
                f"{pollutant:<12} | {bar}{spaces} | "
                f"{value:.1f} / {limit:.1f} "
                f"({ratio * 100:.0f}% of WHO reference)"
            )

        elif pollutant == "Overall AQI":
            filled = min(40, max(1, round(value / 12.5)))
            bar = "#" * filled
            spaces = "." * (40 - filled)

            lines.append(
                f"{pollutant:<12} | {bar}{spaces} | "
                f"{value:.0f} ({get_aqi_category(value)})"
            )

    lines.append("=" * 72)
    lines.append(
        "AQI uses the Open-Meteo US AQI field. WHO values are "
        "health-based concentration references, not AQI scores."
    )

    return "\n".join(lines)


# ============================================================
# VISUALIZATIONS
# ============================================================

def make_bar_chart(df, pollutants, is_current):
    rows = []

    for pollutant in pollutants:
        if pollutant not in WHO:
            continue

        value = get_summary_value(df, pollutant, is_current)

        if value is not None:
            rows.append({
                "Pollutant": pollutant,
                "Observed": value,
                "WHO reference": WHO[pollutant]["limit"],
            })

    if not rows:
        return None

    plot_df = pd.DataFrame(rows)

    long_df = plot_df.melt(
        id_vars="Pollutant",
        value_vars=["Observed", "WHO reference"],
        var_name="Measure",
        value_name="Value",
    )

    fig = px.bar(
        long_df,
        x="Pollutant",
        y="Value",
        color="Measure",
        barmode="group",
        title="Observed Concentration vs WHO Reference",
    )

    fig.update_layout(
        xaxis_title="Pollutant",
        yaxis_title="Concentration",
        legend_title="",
    )

    return fig


def make_line_chart(df, pollutants):
    available = [
        p for p in pollutants
        if p in df.columns
    ]

    if not available:
        return None

    long_df = df[["Time"] + available].melt(
        id_vars="Time",
        var_name="Pollutant",
        value_name="Value",
    )

    fig = px.line(
        long_df,
        x="Time",
        y="Value",
        color="Pollutant",
        markers=False,
        title="Air Quality Parameters Over Time",
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Concentration / AQI",
    )

    return fig


def make_radar_chart(df, pollutants, is_current):
    rows = []

    for pollutant in pollutants:

        if pollutant not in WHO:
            continue

        value = get_summary_value(df, pollutant, is_current)

        if value is None:
            continue

        ratio = (value / WHO[pollutant]["limit"]) * 100

        rows.append({
            "Pollutant": pollutant,
            "Percent of WHO reference": ratio,
        })

    if not rows:
        return None

    radar_df = pd.DataFrame(rows)

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=radar_df["Percent of WHO reference"],
            theta=radar_df["Pollutant"],
            fill="toself",
            name="Observed / WHO × 100",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[100] * len(radar_df),
            theta=radar_df["Pollutant"],
            name="WHO reference = 100%",
            line=dict(dash="dash"),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                title="% of WHO reference",
            )
        ),
        title="Radar Comparison Against WHO References",
    )

    return fig


# ============================================================
# ENVIRONMENTAL REPORT
# ============================================================

def generate_report(city, df, pollutants, is_current):
    st.subheader("Environmental Report")

    # -----------------------------
    # SUMMARY TABLE
    # -----------------------------

    summary_rows = []

    for pollutant in pollutants:

        value = get_summary_value(df, pollutant, is_current)

        if value is None:
            continue

        row = {
            "Parameter": pollutant,
            "Observed": round(value, 2),
            "Unit": DISPLAY_UNITS[pollutant],
        }

        if pollutant in WHO:
            limit = WHO[pollutant]["limit"]
            ratio = value / limit

            row["WHO reference"] = limit
            row["WHO averaging period"] = WHO[pollutant]["period"]
            row["Reference ratio"] = round(ratio, 2)

            if ratio > 1:
                row["Screening result"] = "Above reference"
            else:
                row["Screening result"] = "At/below reference"

        else:
            row["WHO reference"] = "N/A"
            row["WHO averaging period"] = "N/A"
            row["Reference ratio"] = "N/A"
            row["Screening result"] = "AQI scale"

        summary_rows.append(row)

    if summary_rows:
        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
        )

    st.warning(
        "The WHO comparison is a screening comparison, not a regulatory "
        "compliance determination. WHO guideline values depend on specific "
        "averaging periods."
    )

    # -----------------------------
    # EMISSION SOURCES
    # -----------------------------

    st.subheader("1. Primary Anthropogenic & Natural Emission Sources")

    for pollutant in pollutants:

        if pollutant not in SOURCES:
            continue

        with st.expander(pollutant):
            st.write(
                "**Anthropogenic:** "
                + SOURCES[pollutant]["Anthropogenic"]
            )
            st.write(
                "**Natural:** "
                + SOURCES[pollutant]["Natural"]
            )

    # -----------------------------
    # HEALTH + ECOSYSTEM RISKS
    # -----------------------------

    st.subheader("2. Public Health & Ecosystem Risks")

    for pollutant in pollutants:

        if pollutant not in HEALTH_RISKS:
            continue

        value = get_summary_value(
            df,
            pollutant,
            is_current
        )

        if value is None:
            continue

        if pollutant in WHO:
            ratio = value / WHO[pollutant]["limit"]

            if ratio > 1:
                context = (
                    "The selected dataset's summary value is above the "
                    "WHO reference used for this screening comparison."
                )
            else:
                context = (
                    "The selected dataset's summary value is at or below "
                    "the WHO reference used for this screening comparison."
                )
        else:
            context = ""

        st.markdown(
            f"**{pollutant}:** {HEALTH_RISKS[pollutant]} "
            f"{context}"
        )

    # -----------------------------
    # TWO TARGETED INTERVENTIONS
    # -----------------------------

    st.subheader(
        f"3. Two Targeted Policy / Urban Planning Interventions for {city}"
    )

    scored = []

    for pollutant in pollutants:
        if pollutant not in WHO:
            continue

        value = get_summary_value(df, pollutant, is_current)

        if value is not None:
            ratio = value / WHO[pollutant]["limit"]
            scored.append((pollutant, ratio))

    scored.sort(key=lambda x: x[1], reverse=True)

    interventions = []

    pollutant_names = [p for p, _ in scored]

    if any(p in pollutant_names for p in ["PM2.5", "PM10"]):
        interventions.append(
            "Prioritize road and construction-dust management in the "
            f"main {city} activity corridors: dust suppression, covered "
            "material transport, mechanized road cleaning and construction "
            "site controls."
        )

    if any(p in pollutant_names for p in ["NO2", "CO"]):
        interventions.append(
            "Prioritize transport-emission measures in dense traffic "
            f"corridors of {city}: bus/public-transit priority, anti-idling "
            "controls, traffic-flow management and vehicle inspection/"
            "maintenance."
        )

    if "SO2" in pollutant_names:
        interventions.append(
            "Strengthen industrial-combustion controls in and around "
            f"{city}, including cleaner fuels, sulfur controls and "
            "continuous emissions monitoring where appropriate."
        )

    if "O3" in pollutant_names:
        interventions.append(
            "Target ozone precursor emissions around "
            f"{city} by controlling NOx and VOC sources from traffic, "
            "industry and solvent use, especially during high-ozone episodes."
        )

    # Always return exactly two interventions.
    defaults = [
        "Expand neighborhood-level air-quality monitoring so that "
        f"{city} can identify pollution hotspots and compare interventions "
        "over time.",
        "Use public transport, walking/cycling infrastructure and "
        "land-use planning to reduce exposure along high-traffic corridors."
    ]

    for item in defaults:
        if len(interventions) >= 2:
            break
        interventions.append(item)

    # Deduplicate while keeping order.
    unique_interventions = []
    for item in interventions:
        if item not in unique_interventions:
            unique_interventions.append(item)

    for i, item in enumerate(unique_interventions[:2], start=1):
        st.markdown(f"**Intervention {i}:** {item}")


# ============================================================
# STEP 1 — CITY SELECTION
# ============================================================

if st.session_state.step == 1:

    st.header("Step 1: City Selection")

    city_query = st.text_input(
        "Which city would you like to analyze today?",
        placeholder="Example: Delhi",
    )

    if st.button("Continue to Step 2", type="primary"):

        if not city_query.strip():
            st.error("Please enter a city.")
            st.stop()

        try:
            matches = geocode_city(city_query.strip())

            if not matches:
                st.error("No matching city was found. Try a more specific name.")
                st.stop()

            st.session_state.city_matches = matches
            st.session_state.step = 1.5
            st.rerun()

        except Exception as exc:
            st.error(f"City lookup failed: {exc}")


# ============================================================
# STEP 1.5 — CONFIRM CITY
# ============================================================

elif st.session_state.step == 1.5:

    st.header("Step 1: Confirm City")

    matches = st.session_state.get("city_matches", [])

    labels = [
        f"{m['name']}, {m.get('admin1', '')}, {m.get('country', '')}"
        for m in matches
    ]

    selected_label = st.selectbox(
        "Select the matching city:",
        labels
    )

    selected_index = labels.index(selected_label)
    selected = matches[selected_index]

    st.caption(
        f"Coordinates: {selected['latitude']:.4f}, "
        f"{selected['longitude']:.4f}"
    )

    if st.button("Confirm City", type="primary"):

        st.session_state.city = selected["name"]
        st.session_state.latitude = selected["latitude"]
        st.session_state.longitude = selected["longitude"]
        st.session_state.timezone = selected.get("timezone")
        st.session_state.step = 2
        st.rerun()


# ============================================================
# STEP 2 — TIME PERIOD
# ============================================================

elif st.session_state.step == 2:

    st.header("Step 2: Time Period Selection")

    st.success(
        f"City selected: **{st.session_state.city}**"
    )

    period = st.selectbox(
        "What time period would you like to examine?",
        [
            "Real-time/Current",
            "Past 7 Days",
            "Seasonal Average",
            "Custom Date Range",
        ],
    )

    custom_start = None
    custom_end = None

    if period == "Custom Date Range":

        custom_start = st.date_input(
            "Start date",
            value=date.today() - timedelta(days=6)
        )

        custom_end = st.date_input(
            "End date",
            value=date.today()
        )

        if custom_end > date.today():
            st.warning("Future dates cannot be fetched from the historical dataset.")

    if st.button("Continue to Step 3", type="primary"):

        if period == "Custom Date Range":
            if custom_start > custom_end:
                st.error("Start date must be before or equal to end date.")
                st.stop()

            if custom_end > date.today():
                st.error("Please choose an end date that is not in the future.")
                st.stop()

        st.session_state.period = period
        st.session_state.custom_start = custom_start
        st.session_state.custom_end = custom_end
        st.session_state.step = 3
        st.rerun()


# ============================================================
# STEP 3 — POLLUTANT SELECTION
# ============================================================

elif st.session_state.step == 3:

    st.header("Step 3: Pollutant Selection")

    st.success(
        f"City: **{st.session_state.city}**  |  "
        f"Period: **{st.session_state.period}**"
    )

    pollutants = st.multiselect(
        "Which key air quality parameters do you want to include in your dataset?",
        [
            "PM2.5",
            "PM10",
            "NO2",
            "O3",
            "CO",
            "SO2",
            "Overall AQI",
        ],
        default=["PM2.5", "PM10", "Overall AQI"],
    )

    if st.button("Continue to Step 4", type="primary"):

        if not pollutants:
            st.error("Please select at least one parameter.")
            st.stop()

        st.session_state.pollutants = pollutants
        st.session_state.step = 4
        st.rerun()


# ============================================================
# STEP 4 — VISUALIZATION
# ============================================================

elif st.session_state.step == 4:

    st.header("Step 4: Visualization Choice")

    st.success(
        f"City: **{st.session_state.city}**  |  "
        f"Period: **{st.session_state.period}**  |  "
        f"Parameters: **{', '.join(st.session_state.pollutants)}**"
    )

    visualization = st.radio(
        "How would you like to present this data?",
        [
            "Bar Chart vs WHO Limits",
            "Line Graph over Time",
            "Radar Comparison Plot",
        ],
    )

    if st.button("Continue to Step 5", type="primary"):
        st.session_state.visualization = visualization
        st.session_state.step = 5
        st.rerun()


# ============================================================
# STEP 5 — DATA FETCHING & SYNTHESIS
# ============================================================

elif st.session_state.step == 5:

    st.header("Step 5: Data Fetching & Synthesis")

    st.write(
        f"**City:** {st.session_state.city}  \n"
        f"**Time period:** {st.session_state.period}  \n"
        f"**Parameters:** {', '.join(st.session_state.pollutants)}  \n"
        f"**Visualization:** {st.session_state.visualization}"
    )

    if st.button("🚀 Run Air Quality Analysis", type="primary"):

        try:

            with st.spinner(
                "Fetching the air-quality dataset..."
            ):

                period = st.session_state.period

                if period == "Real-time/Current":

                    data = fetch_current(
                        st.session_state.latitude,
                        st.session_state.longitude,
                    )

                    df = current_to_dataframe(data)
                    is_current = True
                    period_label = "Current snapshot"

                else:

                    start, end, period_label = get_period_dates(
                        period,
                        st.session_state.custom_start,
                        st.session_state.custom_end,
                    )

                    data = fetch_historical(
                        st.session_state.latitude,
                        st.session_state.longitude,
                        start,
                        end,
                    )

                    df = historical_to_dataframe(data)
                    is_current = False

                st.session_state.df = df
                st.session_state.results = {
                    "period_label": period_label,
                    "is_current": is_current,
                }

            st.success("Air-quality dataset retrieved successfully.")

        except Exception as exc:
            st.error(
                "The data request failed. "
                f"Details: {exc}"
            )
            st.stop()

    # --------------------------------------------------------
    # SHOW RESULTS AFTER DATA HAS BEEN FETCHED
    # --------------------------------------------------------

    if st.session_state.df is not None:

        df = st.session_state.df
        is_current = st.session_state.results["is_current"]

        st.subheader(
            f"Dataset — {st.session_state.city}"
        )

        available = [
            p for p in st.session_state.pollutants
            if p in df.columns
        ]

        st.dataframe(
            df[["Time"] + available].tail(200),
            use_container_width=True,
        )

        # ----------------------------------------------------
        # CURRENT AQI CARD
        # ----------------------------------------------------

        if "Overall AQI" in df.columns:

            aqi_value = get_summary_value(
                df,
                "Overall AQI",
                is_current
            )

            if aqi_value is not None:

                st.metric(
                    "Overall US AQI",
                    f"{aqi_value:.0f}",
                    get_aqi_category(aqi_value),
                )

        # ----------------------------------------------------
        # ASCII PLOT
        # ----------------------------------------------------

        st.subheader("ASCII Air-Quality Plot")

        st.code(
            make_ascii_plot(
                df,
                st.session_state.pollutants,
                is_current,
            ),
            language="text",
        )

        # ----------------------------------------------------
        # SELECTED VISUALIZATION
        # ----------------------------------------------------

        st.subheader(
            st.session_state.visualization
        )

        visualization = st.session_state.visualization

        if visualization == "Bar Chart vs WHO Limits":

            fig = make_bar_chart(
                df,
                st.session_state.pollutants,
                is_current,
            )

            if fig:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            if "Overall AQI" in st.session_state.pollutants:
                st.info(
                    "Overall AQI is shown separately because WHO AQG "
                    "values are pollutant concentrations, not AQI values."
                )

        elif visualization == "Line Graph over Time":

            fig = make_line_chart(
                df,
                st.session_state.pollutants,
            )

            if fig:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

        elif visualization == "Radar Comparison Plot":

            fig = make_radar_chart(
                df,
                st.session_state.pollutants,
                is_current,
            )

            if fig:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            if "Overall AQI" in st.session_state.pollutants:
                st.info(
                    "Overall AQI is excluded from the radar normalization "
                    "because it is an index rather than a concentration "
                    "with a WHO guideline value."
                )

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        generate_report(
            st.session_state.city,
            df,
            st.session_state.pollutants,
            is_current,
        )

        # ----------------------------------------------------
        # DATA SOURCE / NOTES
        # ----------------------------------------------------

        st.subheader("Data & Method Notes")

        st.write(
            "Pollutant and AQI data are retrieved from the Open-Meteo "
            "Air Quality API. City coordinates are resolved through the "
            "Open-Meteo Geocoding API."
        )

        st.write(
            "For historical periods, PM2.5, PM10, NO2, CO and SO2 are "
            "summarized using daily means; O3 is summarized using the "
            "daily maximum 8-hour rolling mean. Overall AQI is summarized "
            "as the mean of the returned US AQI values."
        )

        st.write(
            "The WHO comparison uses the 2021 WHO Global Air Quality "
            "Guidelines. WHO guideline values are health-based reference "
            "levels and are not themselves an AQI scale."
        )

        # ----------------------------------------------------
        # RESET
        # ----------------------------------------------------

        if st.button("🔄 Start New Analysis"):
            reset_app()
            st.rerun()
