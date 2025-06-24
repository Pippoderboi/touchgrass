import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point
import json
import time

def get_osm_opening_hours(lat, lon, radius=500):
    """Query OpenStreetMap for opening hours near a specific location"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
        node(around:{radius},{lat},{lon})["opening_hours"];
        way(around:{radius},{lat},{lon})["opening_hours"];
        relation(around:{radius},{lat},{lon})["opening_hours"];
    );
    out body;
    >;
    out skel qt;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()
        data = response.json()
        
        # Extract opening hours from the results
        opening_hours = []
        for element in data['elements']:
            if 'tags' in element and 'opening_hours' in element['tags']:
                opening_hours.append(element['tags']['opening_hours'])
                
        if opening_hours:
            return opening_hours[0]  # Return first found opening hours
        return None
    except Exception as e:
        print(f"Error fetching opening hours: {e}")
        return None

def update_facilities_with_opening_hours(input_file, output_file):
    """Update GeoJSON file with opening hours from OSM"""
    print(f"Loading {input_file}")
    gdf = gpd.read_file(input_file)
    
    # Add opening hours column if it doesn't exist
    if 'OPENING HOURS' not in gdf.columns:
        gdf['OPENING HOURS'] = None
    
    # Process each facility
    for idx, row in gdf.iterrows():
        if row.geometry:
            lat, lon = row.geometry.y, row.geometry.x
            name = row.get('NAME') or row.get('Name', 'Unknown facility')
            print(f"Fetching opening hours for {name} at {lat}, {lon}")
            
            # Get opening hours from OSM
            opening_hours = get_osm_opening_hours(lat, lon)
            
            if opening_hours:
                print(f"Found opening hours: {opening_hours}")
                gdf.at[idx, 'OPENING HOURS'] = opening_hours
            else:
                print("No opening hours found")
            
            # Be nice to the API
            time.sleep(1)
    
    # Save the updated GeoJSON
    gdf.to_file(output_file, driver='GeoJSON')
    print(f"Saved updated GeoJSON to {output_file}")

if __name__ == "__main__":
    # Process libraries
    update_facilities_with_opening_hours(
        'raw_data_geojson/buechereien.geojson',
        'buechereien_mit_opening_hours.geojson'
    )
    
    # Process sport facilities
    update_facilities_with_opening_hours(
        'raw_data_geojson/sportstaetten.geojson',
        'sportstaetten_mit_opening_hours.geojson'
    )
