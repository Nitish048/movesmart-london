
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="MoveSmart London | Mobility Intelligence",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent.parent

ROUTES_FILE = ROOT / "data" / "analytics" / "top_20_routes_mapped.csv"
APP_TITLE = "MoveSmart London"

# ---------------------------------------------------------
# STYLING
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        .hero {
            padding: 22px 24px;
            border-radius: 16px;
            background: linear-gradient(120deg, #102c3b, #176b67);
            color: white;
            margin-bottom: 22px;
        }

        .hero h1 {
            color: white;
            margin-bottom: 6px;
        }

        .hero p {
            color: #d6eeea;
            margin-bottom: 0;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            padding: 14px;
            border-radius: 12px;
        }

        .small-note {
            color: #777;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# LOAD AND VALIDATE DATA
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🚲 MoveSmart London</h1>
        <p>Bike Mobility Intelligence · Route Discovery · Station Analytics</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Historical TfL Santander Cycles journeys · "
    "31 January – 6 March 2018"
)

if not ROUTES_FILE.exists():
    st.error(f"Route data not found: {ROUTES_FILE}")
    st.info("Run src/prepare_route_map.py before starting this app.")
    st.stop()

@st.cache_data
def load_routes(path_string):
    return pd.read_csv(path_string)

routes = load_routes(str(ROUTES_FILE))

required_columns = [
    "Rank",
    "StartStation Name",
    "EndStation Name",
    "TripCount",
    "AverageDurationMinutes",
    "StartLatitude",
    "StartLongitude",
    "EndLatitude",
    "EndLongitude",
]

missing = [column for column in required_columns if column not in routes.columns]

if missing:
    st.error(f"Required columns missing from route data: {missing}")
    st.stop()

routes = routes.dropna(
    subset=[
        "StartStation Name",
        "EndStation Name",
        "StartLatitude",
        "StartLongitude",
        "EndLatitude",
        "EndLongitude",
        "TripCount",
    ]
).copy()

routes["Rank"] = routes["Rank"].astype(int)
routes["TripCount"] = routes["TripCount"].astype(int)

if routes.empty:
    st.warning("No routes have complete coordinates.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.title("🎛️ Map Controls")
st.sidebar.caption("Explore the most frequently travelled routes.")

min_count = int(routes["TripCount"].min())
max_count = int(routes["TripCount"].max())

trip_threshold = st.sidebar.slider(
    "Minimum journeys per route",
    min_value=min_count,
    max_value=max_count,
    value=min_count,
)

filtered = routes[routes["TripCount"] >= trip_threshold].copy()

if filtered.empty:
    st.warning("No routes match this filter.")
    st.stop()

route_labels = {
    (
        f"#{int(row['Rank'])} · "
        f"{row['StartStation Name']} → {row['EndStation Name']}"
    ): int(row["Rank"])
    for _, row in filtered.iterrows()
}

selected_labels = st.sidebar.multiselect(
    "Highlight routes",
    options=list(route_labels.keys()),
    default=list(route_labels.keys())[:5],
    help="Highlighted routes appear in orange. Other routes appear in blue.",
)

selected_ranks = {route_labels[label] for label in selected_labels}

show_station_labels = st.sidebar.checkbox(
    "Show station names on map",
    value=False,
    help="Turn on labels to see station names directly on the map.",
)

show_all_routes = st.sidebar.checkbox(
    "Show all filtered routes",
    value=True,
)

if not show_all_routes:
    if selected_ranks:
        filtered = filtered[filtered["Rank"].isin(selected_ranks)].copy()
    else:
        filtered = filtered.iloc[0:0].copy()

if filtered.empty:
    st.info("Select one or more routes in the sidebar to display them.")
    st.stop()

filtered["IsHighlighted"] = filtered["Rank"].isin(selected_ranks)

# ---------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------
total_trips = int(filtered["TripCount"].sum())
highest = filtered.loc[filtered["TripCount"].idxmax()]
average_duration = float(filtered["AverageDurationMinutes"].mean())

start_names = set(filtered["StartStation Name"])
end_names = set(filtered["EndStation Name"])
unique_stations = len(start_names | end_names)

k1, k2, k3, k4 = st.columns(4)

k1.metric("Routes displayed", f"{len(filtered):,}")
k2.metric("Trips on displayed routes", f"{total_trips:,}")
k3.metric("Stations represented", f"{unique_stations:,}")
k4.metric("Mean route duration", f"{average_duration:.1f} min")

st.divider()

# ---------------------------------------------------------
# PREPARE ROUTE LAYER
# ---------------------------------------------------------
max_visible_count = max(int(filtered["TripCount"].max()), 1)

line_data = filtered.copy()

line_data["LineWidth"] = (
    2.0 + 7.0 * line_data["TripCount"] / max_visible_count
)

line_data["LineColor"] = line_data["IsHighlighted"].apply(
    lambda highlighted: [242, 105, 66, 230]
    if highlighted
    else [42, 133, 190, 170]
)

route_layer = pdk.Layer(
    "LineLayer",
    data=line_data,
    get_source_position="[StartLongitude, StartLatitude]",
    get_target_position="[EndLongitude, EndLatitude]",
    get_width="LineWidth",
    get_color="LineColor",
    width_min_pixels=2,
    width_max_pixels=10,
    pickable=True,
    auto_highlight=True,
)

# ---------------------------------------------------------
# PREPARE STATION MARKERS
# ---------------------------------------------------------
start_points = filtered[
    [
        "StartStation Name",
        "StartLatitude",
        "StartLongitude",
        "TripCount",
    ]
].rename(
    columns={
        "StartStation Name": "Station",
        "StartLatitude": "Latitude",
        "StartLongitude": "Longitude",
    }
)

end_points = filtered[
    [
        "EndStation Name",
        "EndLatitude",
        "EndLongitude",
        "TripCount",
    ]
].rename(
    columns={
        "EndStation Name": "Station",
        "EndLatitude": "Latitude",
        "EndLongitude": "Longitude",
    }
)

station_points = pd.concat(
    [start_points, end_points],
    ignore_index=True,
)

station_points = (
    station_points.groupby(
        ["Station", "Latitude", "Longitude"],
        as_index=False,
    )
    .agg(RouteTripCount=("TripCount", "sum"))
)

station_points["MarkerRadius"] = (
    45 + 20 * station_points["RouteTripCount"]
    / max(int(station_points["RouteTripCount"].max()), 1)
)

station_layer = pdk.Layer(
    "ScatterplotLayer",
    data=station_points,
    get_position="[Longitude, Latitude]",
    get_radius="MarkerRadius",
    radius_min_pixels=5,
    radius_max_pixels=15,
    get_fill_color=[20, 160, 120, 220],
    get_line_color=[255, 255, 255, 240],
    line_width_min_pixels=1,
    pickable=True,
    auto_highlight=True,
)

# ---------------------------------------------------------
# OPTIONAL STATION LABEL LAYER
# ---------------------------------------------------------
layers = [route_layer, station_layer]

if show_station_labels:
    label_layer = pdk.Layer(
        "TextLayer",
        data=station_points,
        get_position="[Longitude, Latitude]",
        get_text="Station",
        get_size=11,
        get_color=[25, 45, 55, 255],
        get_text_anchor="start",
        get_alignment_baseline="center",
        get_pixel_offset=[8, 0],
        pickable=True,
    )

    layers.append(label_layer)

# ---------------------------------------------------------
# MAP VIEW AND TOOLTIP
# ---------------------------------------------------------
all_latitudes = pd.concat(
    [filtered["StartLatitude"], filtered["EndLatitude"]],
    ignore_index=True,
)

all_longitudes = pd.concat(
    [filtered["StartLongitude"], filtered["EndLongitude"]],
    ignore_index=True,
)

center_latitude = float(all_latitudes.mean())
center_longitude = float(all_longitudes.mean())

view_state = pdk.ViewState(
    latitude=center_latitude,
    longitude=center_longitude,
    zoom=11,
    pitch=0,
)

tooltip = {
    "html": """
        <div style="font-family:Arial; padding:8px; min-width:220px;">
            <div style="font-size:12px; opacity:0.8;">ROUTE DETAILS</div>
            <b>{StartStation Name}</b>
            <div style="color:#777;">↓ to</div>
            <b>{EndStation Name}</b>
            <hr/>
            <div>Rank: <b>#{Rank}</b></div>
            <div>Journeys: <b>{TripCount}</b></div>
            <div>Average duration: <b>{AverageDurationMinutes} min</b></div>
        </div>
    """,
    "style": {
        "backgroundColor": "#172033",
        "color": "white",
        "fontSize": "12px",
        "padding": "10px",
        "borderRadius": "8px",
    },
}

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="light",
)

# ---------------------------------------------------------
# MAP AND LEGEND
# ---------------------------------------------------------
left, right = st.columns([3, 1], gap="large")

with left:
    st.subheader("🗺️ Interactive Route Map")
    st.caption(
        "Hover over a route line for its origin, destination, rank, "
        "journey count and average duration. Hover over station markers "
        "to see station names."
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
        height=620,
        key="movesmart_route_map",
    )

with right:
    st.subheader("Map Legend")

    st.markdown(
        """
        <div style="padding:12px; border:1px solid #ddd; border-radius:10px;">
            <p>🟠 <b>Orange line</b><br/>Highlighted route</p>
            <p>🔵 <b>Blue line</b><br/>Other routes</p>
            <p>🟢 <b>Green circle</b><br/>Bike station</p>
            <p><b>Line thickness</b><br/>Relative journey count</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Highest-volume route")

    st.write(f"**#{int(highest['Rank'])}**")
    st.write(f"**From:** {highest['StartStation Name']}")
    st.write(f"**To:** {highest['EndStation Name']}")
    st.metric("Journeys", f"{int(highest['TripCount']):,}")
    st.metric(
        "Average duration",
        f"{float(highest['AverageDurationMinutes']):.2f} min",
    )

st.caption(
    "Station marker size represents the sum of trip counts across "
    "the displayed routes touching that station; it is not a live bike count."
)

# ---------------------------------------------------------
# ROUTE RANKINGS
# ---------------------------------------------------------
st.divider()
st.subheader("🏆 Most-travelled Routes")

search = st.text_input(
    "Search origin or destination",
    placeholder="Example: Waterloo, King's Cross, Hyde Park...",
)

table_data = filtered.copy()

if search.strip():
    search_text = search.strip().casefold()

    mask = (
        table_data["StartStation Name"].str.casefold().str.contains(
            search_text, regex=False
        )
        | table_data["EndStation Name"].str.casefold().str.contains(
            search_text, regex=False
        )
    )

    table_data = table_data[mask]

display_columns = [
    "Rank",
    "StartStation Name",
    "EndStation Name",
    "TripCount",
    "AverageDurationMinutes",
]

st.dataframe(
    table_data[display_columns].sort_values("Rank"),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", format="%d"),
        "StartStation Name": st.column_config.TextColumn("Origin"),
        "EndStation Name": st.column_config.TextColumn("Destination"),
        "TripCount": st.column_config.NumberColumn(
            "Journeys", format="%d"
        ),
        "AverageDurationMinutes": st.column_config.NumberColumn(
            "Average duration (min)", format="%.2f"
        ),
    },
)

# ---------------------------------------------------------
# ROUTE DETAIL PANEL
# ---------------------------------------------------------
st.divider()
st.subheader("🔎 Route Explorer")

route_choices = {
    (
        f"#{int(row['Rank'])} · "
        f"{row['StartStation Name']} → {row['EndStation Name']}"
    ): int(row["Rank"])
    for _, row in filtered.sort_values("Rank").iterrows()
}

chosen_label = st.selectbox(
    "Choose a route for more details",
    list(route_choices.keys()),
)

chosen_rank = route_choices[chosen_label]

detail = filtered.loc[filtered["Rank"] == chosen_rank].iloc[0]

d1, d2 = st.columns(2)

with d1:
    st.markdown("#### Origin")
    st.write(detail["StartStation Name"])
    st.caption(
        f"Latitude: {detail['StartLatitude']:.6f} · "
        f"Longitude: {detail['StartLongitude']:.6f}"
    )

with d2:
    st.markdown("#### Destination")
    st.write(detail["EndStation Name"])
    st.caption(
        f"Latitude: {detail['EndLatitude']:.6f} · "
        f"Longitude: {detail['EndLongitude']:.6f}"
    )

r1, r2, r3 = st.columns(3)

r1.metric("Route rank", f"#{int(detail['Rank'])}")
r2.metric("Journeys", f"{int(detail['TripCount']):,}")
r3.metric(
    "Average duration",
    f"{float(detail['AverageDurationMinutes']):.2f} min",
)

# ---------------------------------------------------------
# LIMITATIONS AND DATA NOTES
# ---------------------------------------------------------
with st.expander("Data source and interpretation"):
    st.markdown(
        """
        - **Source:** TfL Santander Cycles journey-history records.
        - **Period:** 31 January–6 March 2018.
        - **Route definition:** A directed pair of starting and ending stations.
          The reverse direction is counted separately.
        - **Map lines:** Straight connections between station coordinates,
          not verified street-level cycling paths.
        - **Coordinates:** Current TfL station locations matched to historical
          records by station ID and name. They may not reflect the exact
          station location in 2018.
        - **Coverage:** Routes without complete candidate coordinates are
          excluded from this map.
        - **Demand:** Marker sizes summarise the displayed route records;
          they do not indicate current bike availability.
        """
    )

st.caption(
    "MoveSmart London · Student portfolio project · "
    "Historical data is not a live availability feed."
)
