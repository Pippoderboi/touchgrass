# Project Start Date: 2025-06
from turtle import color
import geopandas as gpd
import pandas as pd
import os 
import folium 
from folium.plugins import MarkerCluster

#defining original directory
original_dir = os.getcwd()

#choosing directory and getting an overview over files
os.chdir('raw_data_geojson')
print("Current working directory:", os.getcwd())



try:
    for file in os.listdir('.'):
        if file.endswith('.geojson'):
            try:
               
                data = gpd.read_file(file)
                print(f"Successfully loaded {file}")
                
                print(f"CRS: {data.crs}")  # Coordinate Reference System
                print(f"Number of features: {len(data)}")
                print(f"Columns: {data.columns.tolist()}")
                print("\nFirst 5 rows:")
                print(data.head())
                
            except Exception as e:
                print(f"Error processing {file}: {e}")
                
except Exception as e:
    print(f"Something went wrong: {e}")

# Create a map using folium 

muenster = folium.Map(location=[51.96, 7.62], zoom_start=12.5)
marker_cluster=MarkerCluster().add_to(muenster)

# Add Tischtennisplatten 
tischtennis=gpd.read_file('tischtennisplatten_muenster.geojson')
columns_to_show = ['ort','material']
for idx, row in tischtennis.iterrows():
    if row.geometry:
        lon, lat= row.geometry.x, row.geometry.y
        popup_text = "<br>".join(
            f"<b>{col.title()}:</b> {row[col]}" # Change of titles  
                for col in columns_to_show 
                if col in tischtennis.columns and pd.notnull(row[col])
        )
        folium.Marker(
            location=[lat,lon],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color='blue', icon='table-tennis', prefix='fa')
        ).add_to(marker_cluster)

# Add Kinos 
kinos=gpd.read_file('kinos.geojson')
columns_to_show = ['NAME', 'STR_NAME', 'HOMEPAGE']

for idx, row in kinos.iterrows():
    if row.geometry:
        # Extract coordinates
        lon, lat = row.geometry.x, row.geometry.y
        
        # Create popup content
        popup_lines = []
        for col in columns_to_show:
            if col in row and pd.notnull(row[col]):
                # For STR_NAME, append HSNR if it exists
                if col == 'STR_NAME':
                    address = str(row[col])
                    if 'HSNR' in row and pd.notnull(row['HSNR']):
                        address += f" {int(row['HSNR'])}" #convert to int to remove decimal
                    popup_lines.append(f"<b>Address:</b> {address}")
                # Handle HOMEPAGE 
                elif col == 'HOMEPAGE' and 'http' in str(row[col]):
                    popup_lines.append(f"<b>Homepage:</b> <a href='{row[col]}' target='_blank'>{row[col]}</a>")
                # For NAME, just add it normally
                elif col == 'NAME':
                    popup_lines.append(f"<b>Name:</b> {row[col]}")
        
        if popup_lines:  # Only add marker if there's something to show
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='green', icon='film', prefix='fa')
            ).add_to(marker_cluster)

# Add Kinderspielplätze 
kinder=gpd.read_file('spielplaetze.geojson')
columns_to_show=['Name']
for idx, row in kinder.iterrows():
    if row.geometry:
        lon, lat= row.geometry.x, row.geometry.y
        # Format the values in the name column, so that the street names are not in caps
        name =str(row['Name'])
        if name.startswith('SP'):
            formatted_name ='SP'+' '+name[2:].strip().title()
        else:
            formatted_name=name.strip().title()

        popup_text = "<br>".join(
            f"<b>{col}:</b> {formatted_name if col == 'Name' else row[col]}" 
                for col in columns_to_show 
                if col in kinder.columns and pd.notnull(row[col])
        )
        folium.Marker(
            location=[lat,lon],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color='lightred', icon='child-reaching', prefix='fa')
        ).add_to(marker_cluster)

# Add Friedhöfe
friedhof=gpd.read_file('friedhoefe.geojson')
columns_to_show = ['NAME','HOMEPAGE']

for idx, row in friedhof.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        for col in columns_to_show:
            if col in row and pd.notnull(row[col]):
                #Format column name for display ( first letter capitalized)
                display_name=col[0].upper()+col[1:].lower() if col else col
                # Make URLs clickable
                if col.lower() == 'homepage' and 'http' in str(row[col]):
                    popup_lines.append(f"<b>{display_name}:</b> <a href='{row[col]}' target='_blank'>{row[col]}</a>")
                else:
                    popup_lines.append(f"<b>{display_name}:</b> {row[col]}")
        
        if popup_lines:  # Only add marker if there's something to show
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='darkblue', icon='cross', prefix='fa')
            ).add_to(marker_cluster)


# Add Refill Stationen 
refill=gpd.read_file('refill_stations.geojson')
columns_to_show = ['Name','Straße','PLZ','Beschreibung','Homepage']

for idx, row in refill.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        for col in columns_to_show:
            if col in row and pd.notnull(row[col]):
                # Make URLs clickable
                if col == 'Homepage' and 'http' in str(row[col]):
                    popup_lines.append(f"<b>{col}:</b> <a href='{row[col]}' target='_blank'>{row[col]}</a>")
                else:
                    popup_lines.append(f"<b>{col}:</b> {row[col]}")
        
        if popup_lines:  # Only add marker if there's something to show
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='pink', icon='tint', prefix='fa')
            ).add_to(marker_cluster)

#Add Gastronomie 
gastro=gpd.read_file('muenster_gastronomie.geojson')
columns_to_show=['name','addr:street','addr:housenumber','contact:phone','opening_hours','website']
for idx, row in gastro.iterrows():
    if row.geometry and pd.notnull(row.geometry):
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        # Manually add name first if it exists
        if 'name' in row and pd.notnull(row['name']):
            popup_lines.append(f"<b>Name:</b> {row['name']}")

        # Create address from street and housenumber
        address = ""
        if 'addr:street' in row and pd.notnull(row['addr:street']):
            address += row['addr:street']
        if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
            address += f" {row['addr:housenumber']}"
        if address:
            popup_lines.append(f"<b>Address:</b> {address.strip()}")

        # Add other details, excluding ones already handled
        other_cols = ['contact:phone', 'opening_hours', 'website']
        for col in other_cols:
            if col in row and pd.notnull(row[col]):
                display_name = col.replace('_', ' ').replace(':', ' ').title()
                # Make website URL clickable
                if col == 'website' and 'http' in str(row[col]):
                    popup_lines.append(f"<b>{display_name}:</b> <a href='{row[col]}' target='_blank'>{row[col]}</a>")
                else:
                    popup_lines.append(f"<b>{display_name}:</b> {row[col]}")

        if popup_lines:  # Only add marker if there's something to show
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='lightred', icon='utensils', prefix='fa')
            ).add_to(marker_cluster)


# Add layer control (only need to do this once after all layers are added)
folium.LayerControl().add_to(muenster)

# Go back to original directory and save map 
os.chdir(original_dir)
muenster.save("muenster_map.html")