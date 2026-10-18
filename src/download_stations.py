
import json
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = "https://api.tfl.gov.uk/BikePoint/"

output_dir = Path("data") / "raw"
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "tfl_bikepoint_locations.json"

request = Request(
    API_URL,
    headers={"User-Agent": "MoveSmartLondon-StudentProject/1.0"},
)

print("Downloading station locations from TfL...")

with urlopen(request, timeout=60) as response:
    data = json.load(response)

if not isinstance(data, list):
    raise ValueError("Unexpected API response: expected a list.")

if not data:
    raise ValueError("The API returned an empty station list.")

with output_file.open("w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

print(f"Stations downloaded: {len(data):,}")
print(f"Saved to: {output_file}")

first_station = data[0]
print("Example station:", first_station.get("commonName"))
print("Latitude:", first_station.get("lat"))
print("Longitude:", first_station.get("lon"))
