import folium
import os
from pathlib import Path

# Get the script directory
script_dir = str(Path(__file__).parent)

# Create a custom icon
sport_icon = folium.Icon(color='red', icon='flag', prefix='fa')

# Read the existing GeoJSON file
sportstaetten = gpd.read_file(os.path.join(script_dir, 'sportstaetten_mit_opening_hours.geojson'))

# Create a new GeoJSON file with the custom icon
sportstaetten.to_file(os.path.join(script_dir, 'sportstaetten_mit_opening_hours.geojson'), driver='GeoJSON')
