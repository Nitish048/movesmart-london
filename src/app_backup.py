
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(
    page_title="MoveSmart London | Route Intelligence",
    page_icon="🚲",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROUTES_FILE = PROJECT_ROOT / "data" / "analytics" / "top_20_routes_mapped.csv"

st.title("🚲 MoveSmart London")
st.subheader("Bike Mobility & Route Intelligence")
st.caption(
    "Historical TfL Santander Cycles journeys | "
    "31 January – 6 March 2018"
)

if not ROUTES_FILE.exists():
    st.error(f"Route data not found: {ROUTES_FILE}")
    st.stop()

routes = pd.read_csv(ROUTES_FILE)

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

missing_columns = [
    col for col in required_columns if col not in routes.columns
]

if missing_columns:
    st.error(f"Missing required columns: {missing_columns}")
    st.stop()

routes = routes.dropna(
    subset=[
        "StartLatitude",
        "StartLongitude",
        "EndLatitude",
        "EndLongitude",
    ]
).copy()

if routes.empty:
    st.warning("No routes have complete coordinates.")
    st.stop()

routes["Rank"] = routes["Rank"].astype(int)
routes["TripCount"] = routes["TripCount"].astype(int)

# Sidebar controls
st.sidebar.header("Map filters")

min_trips = int(routes["TripCount"].min())
max_trips = int(routes["TripCount"].max())

trip_threshold = st.sidebar.slider(
    "Minimum journeys on a route",
    min_value=min_trips,
    max_value=max_trips,
    value=min_trips,
)

filtered = routes[routes["TripCount"] >= trip_threshold].copy()

route_options = {
    f"#{int(row['Rank'])}: {row['StartStation Name']} → "
    f"{row['EndStation Name']} ({int(row['TripCount'])} trips)": int(row["Rank"])
    for _, row in filtered.iterrows()
}

selected_labels = st.sidebar.multiselect(
    "Highlight routes",
    options=list(route_options.keys()),
    default=list(route_options.keys())[:5],
)

selected_ranks = {
    route_options[label] for label in selected_labels
}

filtered["Selected"] = filtered["Rank"].isin(selected_ranks)

# Summary metrics
total_routes = len(filtered)
total_trips = int(filtered["TripCount"].sum())
highest_route = filtered.loc[filtered["TripCount"].idxmax()]

c1, c2, c3 = st.columns(3)
c1.metric("Routes displayed", f"{total_routes:,}")
c2.metric("Journeys across displayed routes", f"{total_trips:,}")
c3.metric("Highest route count", f"{int(highest_route['TripCount']):,}")

st.info(
    "Lines show straight connections between station coordinates, "
    "not the actual streets cyclists followed. Coordinates are from "
    "the current TfL station list and may differ from historical locations."
)

# Route layer: line thickness represents relative journey count.
line_data = filtered.copy()
line_data["width"] = (
    2 + 6 * line_data["TripCount"] / max_trips
)
line_data["color"] = line_data["Selected"].apply(
    lambda selected: [230, 75, 45, 220]
    if selected
    else [55, 125, 190, 150]
)

route_layer = pdk.Layer(
    "LineLayer",
    data=line_data,
    get_source_position="[StartLongitude, StartLatitude]",
    get_target_position="[EndLongitude, EndLatitude]",
    get_width="width",
    get_color="color",
    width_min_pixels=2,
    pickable=True,
    auto_highlight=True,
)

# Station layer: show both start and end stations.
starts = filtered[
    ["StartStation Name", "StartLatitude", "StartLongitude", "TripCount"]
].rename(columns={
    "StartStation Name": "Station",
    "StartLatitude": "Latitude",
    "StartLongitude": "Longitude",
})

ends = filtered[
    ["EndStation Name", "EndLatitude", "EndLongitude", "TripCount"]
].rename(columns={
    "EndStation Name": "Station",
    "EndLatitude": "Latitude",
    "EndLongitude": "Longitude",
})

stations = pd.concat([starts, ends], ignore_index=True)
stations = (
    stations.groupby(["Station", "Latitude", "Longitude"], as_index=False)
    ["TripCount"].sum()
)

station_layer = pdk.Layer(
    "ScatterplotLayer",
    data=stations,
    get_position="[Longitude, Latitude]",
    get_radius=65,
    radius_min_pixels=3,
    radius_max_pixels=12,
    get_fill_color=[20, 160, 120, 190],
    get_line_color=[255, 255, 255, 220],
    line_width_min_pixels=1,
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=51.5074,
    longitude=-0.1278,
    zoom=11,
    pitch=0,
)

deck = pdk.Deck(
    layers=[route_layer, station_layer],
    initial_view_state=view_state,
    tooltip={
        "html": (
            "<b>{Station}</b><br/>"
            "Journeys on connected routes: {TripCount}"
        ),
        "style": {"backgroundColor": "#222", "color": "white"},
    },
    map_style="light",
)

st.pydeck_chart(deck, use_container_width=True)

st.subheader("Most-travelled routes")
display_columns = [
    "Rank",
    "StartStation Name",
    "EndStation Name",
    "TripCount",
    "AverageDurationMinutes",
]
st.dataframe(
    filtered[display_columns].sort_values("Rank"),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Data source: TfL Santander Cycles historical journey records. "
    "The ranking covers the available sample period only."
)
