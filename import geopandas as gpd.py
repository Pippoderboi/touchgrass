import geopandas as gpd
import requests
from shapely.geometry import Point
import time

# Lade deine Museen-Datei
museen = gpd.read_file("raw_data_geojson/museen.geojson")

# Neue Spalte für Öffnungszeiten hinzufügen
museen["opening_hours_osm"] = None

def get_opening_hours_from_osm(name, lat, lon):
    """
    Suche nach einem Museum in der Nähe mit übereinstimmendem Namen
    und gib ggf. die Öffnungszeiten aus OSM zurück.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json][timeout:15];
    node["tourism"="museum"]["name"="{name}"](around:100,{lat},{lon});
    out tags;
    """
    try:
        response = requests.get(overpass_url, params={'data': query})
        data = response.json()
        for el in data.get('elements', []):
            tags = el.get("tags", {})
            if "opening_hours" in tags:
                return tags["opening_hours"]
    except Exception as e:
        print(f"Fehler bei '{name}': {e}")
    return None

# Schleife über alle Museen
for idx, row in museen.iterrows():
    name = row.get("NAME", "")
    if row.geometry and name:
        lon, lat = row.geometry.x, row.geometry.y
        print(f"Suche Öffnungszeiten für: {name}")
        opening_hours = get_opening_hours_from_osm(name, lat, lon)
        museen.at[idx, "opening_hours_osm"] = opening_hours
        time.sleep(1.5)  # Überlastung der API vermeiden

# Speichern
museen.to_file("museen_mit_opening_hours.geojson", driver="GeoJSON")
print("Fertig! Datei gespeichert als museen_mit_opening_hours.geojson")