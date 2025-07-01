# Project Start Date: 2025-06
from turtle import color
import geopandas as gpd
import pandas as pd
import os 
import folium 
from folium.plugins import MarkerCluster
from formatting_openhour import format_opening_hours

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

# Add Museen
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
museen = gpd.read_file(os.path.join(script_dir, 'raw_data_geojson', 'museen_mit_opening_hours.geojson'))
for idx, row in museen.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['NAME']}</strong><br>" \
                    f"Adresse: {row['STR_NAME']} {row['HSNR']}<br>" \
                    f"PLZ: {int(row['PLZ'])}<br>"
        
        # Add opening hours if available
        if 'opening_hours_osm' in row and pd.notna(row['opening_hours_osm']) and row['opening_hours_osm'] != 'null':
            formatted_hours = format_opening_hours(row['opening_hours_osm'])
            popup_text += f"Öffnungszeiten: {formatted_hours}<br>"
        else:
            popup_text += "Keine Öffnungszeiten verfügbar<br>"
            
        popup_text += f"Homepage: <a href='{row['HOMEPAGE']}' target='_blank'>{row['HOMEPAGE']}</a>"
        
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color='purple', icon='museum', prefix='fa')
        ).add_to(marker_cluster)

# Add Buechereien
buechereien = gpd.read_file(os.path.join(script_dir, 'raw_data_geojson', 'buechereien.geojson'))
for idx, row in buechereien.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['NAME']}</strong><br>" \
                    f"Telefon: {row['TEL']}<br>" \
                    f"Zusatzservice: {row['ZUSATZ_SERVICE']}<br>" \
                    f"Homepage: <a href='{row['LINK1']}' target='_blank'>{row['LINK1']}</a>"
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color='orange', icon='book', prefix='fa')
        ).add_to(marker_cluster)

# Add Sportstaetten
sportstaetten = gpd.read_file(os.path.join(script_dir, 'raw_data_geojson', 'sportstaetten_mit_opening_hours.geojson'))
for idx, row in sportstaetten.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        hsnr = int(row['Hsnr']) if pd.notna(row['Hsnr']) else ''
        popup_text = f"<strong>{row['Produkt']}</strong><br>" \
                    f"Typ: {row['Teilprodukt']}<br>" \
                    f"Adresse: {row['Strname']} {hsnr}<br>" \
                    f"PLZ: {int(row['Plz'])}"
        
        # Add opening hours if available
        if 'OPENING HOURS' in row and pd.notna(row['OPENING HOURS']):
            formatted_hours = format_opening_hours(row['OPENING HOURS'])
            popup_text += f"Öffnungszeiten: {formatted_hours}<br>"
        
        icon = folium.Icon(color='red', icon='flag', prefix='fa')
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=icon
        ).add_to(marker_cluster)

# Add Still & Wickelplätze
wickelplaetze_path = os.path.join(script_dir, 'raw_data_geojson', 'still-und-wickelplaetze-muenster-2023.geojson')
print(f"Loading Still & Wickelplätze from: {wickelplaetze_path}")
wickelplaetze = gpd.read_file(wickelplaetze_path)
print(f"Loaded {len(wickelplaetze)} Still & Wickelplätze")

for idx, row in wickelplaetze.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['Name']}</strong><br>" \
                    f"Adresse: {row['Straße']}<br>" \
                    f"Stockwerk: {row['Stockwerk'] if pd.notna(row['Stockwerk']) else 'nicht angegeben'}<br>" \
                    f"Typ: {row['Typ']}"
        icon = folium.Icon(color='lightblue', icon='baby', prefix='fa')
        marker = folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=icon
        )
        marker.add_to(marker_cluster)
        print(f"Added marker for {row['Name']} at {lat}, {lon}")

# Add Give Boxen
give_boxen = gpd.read_file('give_boxen.geojson')
for idx, row in give_boxen.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['Bezeichnung']}</strong><br>" \
                    f"Adresse: {row['Adresse (ungefähr)']}<br>" \
                    f"Betreiber: {row['Betreiber']}<br>" \
                    f"Mehr Info: <a href='{row['Infos im Internet']}' target='_blank'>{row['Infos im Internet']}</a>"
        
        # Add opening hours if available
        if 'Öffnungszeiten' in row and pd.notna(row['Öffnungszeiten']):
            formatted_hours = format_opening_hours(row['Öffnungszeiten'])
            popup_text += f"Öffnungszeiten: {formatted_hours}<br>"
        
        folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color='blue', icon='gift')
        ).add_to(marker_cluster)

# Add Kinos 
kinos=gpd.read_file('kinos.geojson')
columns_to_show = ['NAME', 'STR_NAME', 'HOMEPAGE','opening_hours']

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
                # Add Opening Hours
                elif col =='opening_hours':
                    formatted_hours= format_opening_hours(row[col])
                    popup_lines.append(f"<b>Opening Hours:</b><br>{formatted_hours}") 
        
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
                elif col =='opening_hours':
                    formatted_hours= format_opening_hours(row[col])
                    popup_lines.append(f"<b>{display_name}:</b><br>{formatted_hours}")
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