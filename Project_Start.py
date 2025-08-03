# Project Start Date: 2025-06
from turtle import color
import geopandas as gpd
import pandas as pd
import os 
import folium 
from folium.plugins import MarkerCluster, LocateControl
from folium import FeatureGroup, LayerControl, Map
from formatting_openhour import format_opening_hours
import math

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

# Create a map using folium with# Create a map centered on Münster
m = folium.Map(location=[51.9607, 7.6261], zoom_start=13, control_scale=True)

# Add CSS for the radius slider control
radius_control = """
<div style="position: fixed; 
            top: 20px; 
            right: 20px; 
            z-index: 1000; 
            background: white; 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            width: 220px;">
    <div style="margin-bottom: 10px; font-weight: bold;">
        <i class="fa fa-arrows-alt-h" style="margin-right: 5px;"></i> Umkreis: 
        <span id="radiusValue">1</span> km
    </div>
    <input type="range" 
           id="radiusSlider" 
           min="0.5" 
           max="10" 
           step="0.5" 
           value="1" 
           style="width: 100%;">
    <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 12px; color: #666;">
        <span>0.5 km</span>
        <span>10 km</span>
    </div>
</div>
"""

# Add the radius control to the map
m.get_root().html.add_child(folium.Element(radius_control))

# Add JavaScript for radius slider
radius_js = """
<script>
// Store all markers with their layer groups
var allMarkers = [];
var currentRadius = 1000; // Default 1km in meters
var userPosition = null;

// Function to calculate distance between two points in meters
function getDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI/180;
    const φ2 = lat2 * Math.PI/180;
    const Δφ = (lat2-lat1) * Math.PI/180;
    const Δλ = (lon2-lon1) * Math.PI/180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c;
}

// Function to update marker visibility based on radius
function updateMarkersByRadius() {
    if (!userPosition) return;
    
    allMarkers.forEach(marker => {
        const markerLatLng = marker.getLatLng();
        const distance = getDistance(
            userPosition.lat, 
            userPosition.lng,
            markerLatLng.lat,
            markerLatLng.lng
        );
        
        if (distance <= currentRadius) {
            marker.addTo(marker._group);
            marker.setOpacity(1.0);
        } else {
            marker.setOpacity(0.3);
        }
    });
}

// Store original addTo method
var originalAddTo = L.Marker.prototype.addTo;
L.Marker.prototype.addTo = function(map) {
    allMarkers.push(this);
    this._group = map; // Store the group this marker belongs to
    return originalAddTo.call(this, map);
};

// Handle location found and slider changes
document.addEventListener('DOMContentLoaded', function() {
    const slider = document.getElementById('radiusSlider');
    const radiusValue = document.getElementById('radiusValue');
    
    // Update radius when slider changes
    slider.addEventListener('input', function() {
        currentRadius = parseFloat(this.value) * 1000; // Convert km to meters
        radiusValue.textContent = this.value;
        updateMarkersByRadius();
    });
    
    // Listen for location found event
    document._map.on('locationfound', function(e) {
        userPosition = e.latlng;
        updateMarkersByRadius();
    });
    
    // Trigger initial update
    updateMarkersByRadius();
});
</script>
"""

# Add the JavaScript to the map
m.get_root().html.add_child(folium.Element(radius_js))

# Add location control with simpler marker style
locate_control = LocateControl(
    position='topleft',
    drawCircle=False,  # Disable circle drawing to avoid serialization issues
    flyTo=True,
    keepCurrentZoomLevel=False,
    showPopup=True,
    showCompass=True,
    icon='location-arrow',
    icon_color='#0078A8',
    circleStyle={
        'weight': 2,
        'color': '#0078A8',
        'fillColor': '#0078A8',
        'fillOpacity': 0.2
    }
)
locate_control.add_to(m)

# Function to calculate distance between two points in kilometers
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

#function to create a feature group with clustering

def create_clustered_feature_group(name, min_zoom=13, show=True):
    fg = folium.FeatureGroup(name=name, show=show)
    return MarkerCluster(
        name=name,
        options={
            'maxClusterRadius': 80,  # Adjust cluster size
            'disableClusteringAtZoom': min_zoom,  # Start showing individual markers at this zoom
            'spiderfyDistanceMultiplier': 2  # How far markers spread out when clicked
        }
    ).add_to(fg), fg


#Creating clustered feature groups
# Find a reasonable min_zoom for every group

museen_cluster, museen_group = create_clustered_feature_group('Museen', min_zoom=15)
buechereien_cluster, buechereien_group = create_clustered_feature_group('Büchereien',min_zoom=15)
sportstaetten_cluster, sportstaetten_group = create_clustered_feature_group('Sportstätten',min_zoom=15)
tischtennis_cluster, tischtennis_group = create_clustered_feature_group('Tischtennisplatten',min_zoom=15)
wickelplaetze_cluster, wickelplaetze_group = create_clustered_feature_group('Wickelplätze',min_zoom=15)
give_boxen_cluster, give_boxen_group = create_clustered_feature_group('Give Boxen',min_zoom=15)
kinos_cluster, kinos_group = create_clustered_feature_group('Kinos',min_zoom=15)
kinder_cluster, kinder_group = create_clustered_feature_group('Spielplätze',min_zoom=15)
friedhof_cluster, friedhof_group = create_clustered_feature_group('Friedhöfe',min_zoom=15)
refill_cluster, refill_group = create_clustered_feature_group('Refillstationen',min_zoom=15)
gastro_cluster, gastro_group = create_clustered_feature_group('Gastronomie',min_zoom=20)
toiletten_cluster, toiletten_group = create_clustered_feature_group('Toiletten',min_zoom=15)
baeder_cluster, baeder_group = create_clustered_feature_group('Bäder',min_zoom=15)
theater_cluster, theater_group = create_clustered_feature_group('Theater',min_zoom=15)
gruenflaechen_cluster, gruenflaechen_group = create_clustered_feature_group('Grünflächen',min_zoom=15)

# Helper function to create markers with consistent styling
def create_marker(lat, lon, popup_text, icon_color, icon_name):
    return folium.Marker(
        location=[lat, lon],
        popup=popup_text,
        icon=folium.Icon(color=icon_color, icon=icon_name, prefix='fa')
    )

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
        create_marker(lat, lon, popup_text, 'blue', 'table-tennis').add_to(m)

# Add Museen
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
museen = gpd.read_file(os.path.join(script_dir, 'raw_data_geojson', 'museen_mit_opening_hours.geojson'))

# Add location control with simpler marker style
locate_control = LocateControl(
    position='topleft',
    drawCircle=False,  # Disable circle drawing to avoid serialization issues
    flyTo=True,
    keepCurrentZoomLevel=False,
    showPopup=True,
    showCompass=True,
    icon='location-arrow',
    icon_color='#0078A8',
    circleStyle={
        'weight': 2,
        'color': '#0078A8',
        'fillColor': '#0078A8',
        'fillOpacity': 0.2
    }
)
locate_control.add_to(m)


# Add Museen markers with initial visibility
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
        
        create_marker(lat, lon, popup_text, 'purple', 'museum').add_to(m)

# Add Buechereien
buechereien = gpd.read_file('buechereien_mit_opening_hours.geojson')
for idx, row in buechereien.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['NAME']}</strong><br>" \
                    f"Telefon: {row['TEL']}<br>" \
                    f"Öffnungszeiten: {format_opening_hours(row.get('OPENING HOURS'))}<br>" \
                    f"Homepage: <a href='{row['LINK1']}' target='_blank'>{row['LINK1']}</a>"
        create_marker(lat, lon, popup_text, 'orange', 'book').add_to(buechereien_group)

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
            popup_text += f"<br>Öffnungszeiten: {formatted_hours}"
        
        create_marker(lat, lon, popup_text, 'green', 'soccer-ball-o').add_to(sportstaetten_group)

# Add Still & Wickelplätze
wickelplaetze = gpd.read_file('still-und-wickelplaetze-muenster-2023.geojson')

for idx, row in wickelplaetze.iterrows():
    if row.geometry:
        lon, lat = row.geometry.x, row.geometry.y
        popup_text = f"<strong>{row['Name']}</strong><br>" \
                    f"Adresse: {row['Straße']}<br>" \
                    f"Stockwerk: {row['Stockwerk'] if pd.notna(row['Stockwerk']) else 'nicht angegeben'}<br>" \
                    f"Typ: {row['Typ']}"
        marker = folium.Marker(
            location=[lat, lon],
            popup=popup_text,
            icon=folium.Icon(color='lightblue',icon='baby',prefix='fa')
        ).add_to(wickelplaetze_cluster)


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
            icon=folium.Icon(color='blue', icon='box-open',prefix='fa')
        ).add_to(give_boxen_cluster)

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
                icon=folium.Icon(color='green', icon='ticket', prefix='fa')
            ).add_to(kinos_cluster)

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
        ).add_to(kinder_cluster)

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
            ).add_to(friedhof_cluster)  


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
            ).add_to(refill_cluster)

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
            ).add_to(gastro_cluster)


#Add Toiletten
toiletten=gpd.read_file('toiletten.geojson')
columns_to_show=['NAME','BARRIEREFREI','opening_hours','website']
for idx, row in toiletten.iterrows():
    if row.geometry and pd.notnull(row.geometry):
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        # Manually add name first if it exists
        if 'NAME' in row and pd.notnull(row['NAME']):
            popup_lines.append(f"<b>Name:</b> {row['NAME']}")

        # Create address from street and housenumber
        address = ""
        if 'addr:street' in row and pd.notnull(row['addr:street']):
            address += row['addr:street']
        if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
            address += f" {row['addr:housenumber']}"
        if address:
            popup_lines.append(f"<b>Address:</b> {address.strip()}")

        # Add other details, excluding ones already handled
        other_cols = ['BARRIEREFREI', 'opening_hours', 'website']
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
                icon=folium.Icon(color='black', icon='female', prefix='fa')
            ).add_to(toiletten_cluster)

#Add Bäder 
baeder=gpd.read_file('baeder.geojson')
columns_to_show=['NAME','addr:street','addr:housenumber','contact:phone','opening_hours','LINK1']
for idx, row in baeder.iterrows():
    if row.geometry and pd.notnull(row.geometry):
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        # Manually add name first if it exists
        if 'NAME' in row and pd.notnull(row['NAME']):
            popup_lines.append(f"<b>Name:</b> {row['NAME']}")

        # Create address from street and housenumber
        address = ""
        if 'addr:street' in row and pd.notnull(row['addr:street']):
            address += row['addr:street']
        if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
            address += f" {row['addr:housenumber']}"
        if address:
            popup_lines.append(f"<b>Address:</b> {address.strip()}")

        # Add other details, excluding ones already handled
        other_cols = ['contact:phone', 'opening_hours', 'LINK1']
        for col in other_cols:
            if col in row and pd.notnull(row[col]):
                display_name = col.replace('_', ' ').replace(':', ' ').title()
                # Make website URL clickable
                if col == 'LINK1' and 'http' in str(row[col]):
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
                icon=folium.Icon(color='darkblue', icon='life-ring', prefix='fa')
            ).add_to(baeder_cluster)

#Add Theater 
theater=gpd.read_file('theater.geojson')
columns_to_show=['NAME','addr:street','addr:housenumber','contact:phone','opening_hours','LINK1']
for idx, row in theater.iterrows():
    if row.geometry and pd.notnull(row.geometry):
        lon, lat = row.geometry.x, row.geometry.y
        
        popup_lines = []
        # Manually add name first if it exists
        if 'NAME' in row and pd.notnull(row['NAME']):
            popup_lines.append(f"<b>Name:</b> {row['NAME']}")

        # Create address from street and housenumber
        address = ""
        if 'addr:street' in row and pd.notnull(row['addr:street']):
            address += row['addr:street']
        if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
            address += f" {row['addr:housenumber']}"
        if address:
            popup_lines.append(f"<b>Address:</b> {address.strip()}")

        # Add other details, excluding ones already handled
        other_cols = ['contact:phone', 'opening_hours', 'LINK1']
        for col in other_cols:
            if col in row and pd.notnull(row[col]):
                display_name = col.replace('_', ' ').replace(':', ' ').title()
                # Make website URL clickable
                if col == 'LINK1' and 'http' in str(row[col]):
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
                icon=folium.Icon(color='darkpurple', icon='ticket-alt', prefix='fa')
            ).add_to(theater_cluster)

# Add all feature groups to the map
for group in [museen_group, buechereien_group, sportstaetten_group, tischtennis_group,
              wickelplaetze_group, give_boxen_group, kinos_group, kinder_group,
              friedhof_group, refill_group, gastro_group, toiletten_group, baeder_group, theater_group, gruenflaechen_group]:
    group.add_to(m)

# Add layer control (only need to do this once after all layers are added)
folium.LayerControl().add_to(m)

# Go back to original directory and save map 
os.chdir(original_dir)
m.save("muenster_map.html")