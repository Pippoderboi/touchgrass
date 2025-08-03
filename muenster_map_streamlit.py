from streamlit_folium import st_folium
import streamlit as st
import geopandas as gpd
import pandas as pd
import os
import folium
from folium.plugins import MarkerCluster
from formatting_openhour import format_opening_hours

# ---- Setup ----
st.set_page_config(layout="wide")
st.title("Münster Map")

# Base paths
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, "raw_data_geojson")

# Base map
muenster = folium.Map(location=[51.96, 7.62], zoom_start=12.5)

# Helper to create clustered groups
def create_clustered_feature_group(name, min_zoom=13, show=True):
    fg = folium.FeatureGroup(name=name, show=show)
    cluster = MarkerCluster(
        name=name,
        options={
            'maxClusterRadius': 80,
            'disableClusteringAtZoom': min_zoom,
            'spiderfyDistanceMultiplier': 2
        }
    ).add_to(fg)
    return cluster, fg

# ---- Sidebar ----
st.sidebar.header("Kategorien auswählen")
show_museen = st.sidebar.checkbox("Museen", False)
show_buechereien = st.sidebar.checkbox("Büchereien", False)
show_sport_drinnen = st.sidebar.checkbox("Sportstätten drinnen", False)
show_sport_draussen = st.sidebar.checkbox("Sportstätten draußen", False)
show_tischtennis = st.sidebar.checkbox("Tischtennisplatten", False)
show_wickelplaetze = st.sidebar.checkbox("Wickelplätze", False)
show_giveboxen = st.sidebar.checkbox("Give Boxen", False)
show_kinos = st.sidebar.checkbox("Kinos", False)
show_kinder = st.sidebar.checkbox("Spielplätze", False)
show_friedhof = st.sidebar.checkbox("Friedhöfe", False)
show_refill = st.sidebar.checkbox("Refillstationen", False)
show_restaurants = st.sidebar.checkbox("Restaurants", False)
show_cafes = st.sidebar.checkbox("Cafés", False)
show_bars = st.sidebar.checkbox("Bars",False)
show_toiletten = st.sidebar.checkbox("Toiletten", False)
show_baeder = st.sidebar.checkbox("Bäder", False)
show_sauna = st.sidebar.checkbox("Saunen", False)
show_theater = st.sidebar.checkbox("Theater", False)
show_gruen = st.sidebar.checkbox("Grünflächen", False)

# ---- Categories ----

# Museen
if show_museen:
    museen_cluster, museen_group = create_clustered_feature_group('Museen', min_zoom=15)
    museen = gpd.read_file(os.path.join(data_dir, 'museen_mit_opening_hours.geojson'))
    for idx, row in museen.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address_parts = []
            if 'STR_NAME' in row and pd.notnull(row['STR_NAME']):
                address_parts.append(str(row['STR_NAME']))
                if 'HSNR' in row and pd.notnull(row['HSNR']):
                    address_parts.append(str(int(row['HSNR'])))
            if 'PLZ' in row and pd.notnull(row['PLZ']):
                address_parts.append(', ' + str(int(row['PLZ']))) 
            if address_parts:
                popup_lines.append(f"<b>Adresse:</b> {' '.join(address_parts)}")
            if 'opening_hours_osm' in row and pd.notnull(row['opening_hours_osm']) and row['opening_hours_osm'] != 'null':
                formatted_hours = format_opening_hours(row['opening_hours_osm'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            if 'HOMEPAGE' in row and pd.notnull(row['HOMEPAGE']):
                website = str(row['HOMEPAGE']).strip()
                if website:
                    popup_lines.append(f"<b>Homepage:</b> <a href='{website}' target='_blank'>{website}</a>")
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='purple', icon='museum', prefix='fa')
                ).add_to(museen_cluster)
    museen_group.add_to(muenster)

# Büchereien
if show_buechereien:
    buechereien_cluster, buechereien_group = create_clustered_feature_group('Büchereien', min_zoom=15)
    buechereien = gpd.read_file(os.path.join(data_dir, 'buechereien_mit_opening_hours.geojson'))
    for idx, row in buechereien.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address_parts = []
            if 'STR_NAME' in row and pd.notnull(row['STR_NAME']):
                address_parts.append(str(row['STR_NAME']))
                if 'HSNR' in row and pd.notnull(row['HSNR']):
                    address_parts.append(str(int(row['HSNR'])))
            if 'PLZ' in row and pd.notnull(row['PLZ']):
                address_parts.append(', ' + str(int(row['PLZ'])))
            if address_parts:
                popup_lines.append(f"<b>Adresse:</b> {' '.join(address_parts)}")
            if 'TEL' in row and pd.notnull(row['TEL']):
                popup_lines.append(f"<b>Telefonnummer:</b> {row['TEL']}")
            if 'OPENING HOURS' in row and pd.notnull(row['OPENING HOURS']):
                formatted_hours = format_opening_hours(row['OPENING HOURS'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            if 'LINK1' in row and pd.notnull(row['LINK1']):
                website = str(row['LINK1']).strip()
                if website:
                    popup_lines.append(f"<b>Homepage:</b> <a href='{website}' target='_blank'>{website}</a>")
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='orange', icon='book', prefix='fa')
                ).add_to(buechereien_cluster)
    buechereien_group.add_to(muenster)

if show_sport_drinnen or show_sport_draussen:
    sport_drinnen_cluster, sport_drinnen_group = create_clustered_feature_group('Sportstätte drinnen', min_zoom=15)
    sport_draussen_cluster, sport_draussen_group = create_clustered_feature_group('Sportstätte draußen', min_zoom=15)
    
    sportstaetten = gpd.read_file(os.path.join(data_dir, 'sportstaetten_mit_opening_hours.geojson'))

    INDOOR_SPORTS = [
        'Krafträume', 'Dreifachhalle', 'Einfachhallen', 'Gymnastikräume',
        'Zweifachhalle', 'Gymnastikraum'
    ]

    for idx, row in sportstaetten.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            is_indoor = row['Teilprodukt'] in INDOOR_SPORTS if pd.notnull(row['Teilprodukt']) else False
            
            if is_indoor and not show_sport_drinnen:
                continue
            if not is_indoor and not show_sport_draussen:
                continue
            
            popup_lines = []
            
            # Name
            if 'Name' in row and pd.notnull(row['Name']):
                popup_lines.append(f"<b>Name:</b> {row['Name']}")
            
            # Type
            if 'Produkt' in row and pd.notnull(row['Produkt']):
                popup_lines.append(f"<b>Art:</b> {row['Produkt']}")
            
            # Teilprodukt
            if 'Teilprodukt' in row and pd.notnull(row['Teilprodukt']):
                popup_lines.append(f"<b>Teilprodukt:</b> {row['Teilprodukt']}")
            
            # Address
            address_parts = []
            if 'Strname' in row and pd.notnull(row['Strname']):
                address_parts.append(str(row['Strname']))
                if 'Hsnr' in row and pd.notna(row['Hsnr']):
                    address_parts.append(str(int(row['Hsnr'])))
            if 'Plz' in row and pd.notnull(row['Plz']):
                address_parts.append(', ' + str(int(row['Plz'])))
            if address_parts:
                popup_lines.append(f"<b>Adresse:</b> {' '.join(address_parts)}")
            
            # Opening hours
            if 'OPENING HOURS' in row and pd.notna(row['OPENING HOURS']):
                formatted_hours = format_opening_hours(row['OPENING HOURS'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            # Add marker
            marker = folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(
                    color='red' if is_indoor else 'cadetblue',
                    icon='dumbbell' if is_indoor else 'volleyball-ball',
                    prefix='fa'
                )
            )
            
            if is_indoor:
                marker.add_to(sport_drinnen_cluster)
            else:
                marker.add_to(sport_draussen_cluster)
    
    if show_sport_drinnen:
        sport_drinnen_group.add_to(muenster)
    if show_sport_draussen:
        sport_draussen_group.add_to(muenster)


# ---- Tischtennisplatten ----
if show_tischtennis:
    tischtennis_cluster, tischtennis_group = create_clustered_feature_group('Tischtennisplatten', min_zoom=15)
    tischtennis = gpd.read_file(os.path.join(data_dir, 'tischtennisplatten_muenster.geojson'))

    for idx, row in tischtennis.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            
            popup_text = "<br>".join(
                f"<b>{col.title()}:</b> {row[col]}"
                for col in ['ort', 'material']
                if col in tischtennis.columns and pd.notnull(row[col])
            )
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color='pink', icon='table-tennis', prefix='fa')
            ).add_to(tischtennis_cluster)
    
    tischtennis_group.add_to(muenster)
# ---- Wickelplätze ----
if show_wickelplaetze:
    wickelplaetze_cluster, wickelplaetze_group = create_clustered_feature_group('Wickelplätze', min_zoom=15)
    wickelplaetze = gpd.read_file(os.path.join(data_dir, 'still-und-wickelplaetze-muenster-2023.geojson'))

    for idx, row in wickelplaetze.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            # Name
            if 'Name' in row and pd.notnull(row['Name']):
                popup_lines.append(f"<b>Name:</b> {row['Name']}")
            
            # Address & Stockwerk
            address = []
            if 'Straße' in row and pd.notnull(row['Straße']):
                address.append(str(row['Straße']))
                if 'Stockwerk' in row and pd.notnull(row['Stockwerk']):
                    address.append(f"Stockwerk: {row['Stockwerk']}")
            if address:
                popup_lines.append(f"<b>Adresse:</b> {', '.join(address)}")
            
            # Type
            if 'Typ' in row and pd.notnull(row['Typ']):
                popup_lines.append(f"<b>Art:</b> {row['Typ']}")
            
            # Add marker
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='lightblue', icon='baby', prefix='fa')
                ).add_to(wickelplaetze_cluster)
    
    wickelplaetze_group.add_to(muenster)


# ---- Give Boxen ----
if show_giveboxen:
    give_boxen_cluster, give_boxen_group = create_clustered_feature_group('Give Boxen', min_zoom=15)
    give_boxen = gpd.read_file(os.path.join(data_dir, 'give_boxen.geojson'))

    for idx, row in give_boxen.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            # Name
            if 'Bezeichnung' in row and pd.notnull(row['Bezeichnung']):
                popup_lines.append(f"<b>Name:</b> {row['Bezeichnung']}")
            
            # Address
            if 'Adresse (ungefähr)' in row and pd.notnull(row['Adresse (ungefähr)']):
                popup_lines.append(f"<b>Adresse:</b> {row['Adresse (ungefähr)']}")
            
            # Betreiber
            if 'Betreiber' in row and pd.notnull(row['Betreiber']):
                popup_lines.append(f"<b>Betreiber:</b> {row['Betreiber']}")
            
            # Website
            if 'Infos im Internet' in row and pd.notnull(row['Infos im Internet']):
                website = str(row['Infos im Internet']).strip()
                if website:
                    popup_lines.append(f"<b>Homepage:</b> <a href='{website}' target='_blank'>{website}</a>")
            
            # Opening hours
            if 'Öffnungszeiten' in row and pd.notnull(row['Öffnungszeiten']):
                formatted_hours = format_opening_hours(row['Öffnungszeiten'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            # Add marker
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='beige', icon='box-open', prefix='fa')
                ).add_to(give_boxen_cluster)
    
    give_boxen_group.add_to(muenster)


# ---- Kinos ----
if show_kinos:
    kinos_cluster, kinos_group = create_clustered_feature_group('Kinos', min_zoom=15)
    kinos = gpd.read_file(os.path.join(data_dir, 'kinos.geojson'))

    for idx, row in kinos.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            # Name
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            
            # Address with HSNR + PLZ
            if 'STR_NAME' in row and pd.notnull(row['STR_NAME']):
                address = str(row['STR_NAME'])
                if 'HSNR' in row and pd.notnull(row['HSNR']):
                    address += f" {int(row['HSNR'])}"
                if 'PLZ' in row and pd.notnull(row['PLZ']):
                    address += f", {int(row['PLZ'])}"
                popup_lines.append(f"<b>Adresse:</b> {address}")
            
            # Website
            if 'HOMEPAGE' in row and pd.notnull(row['HOMEPAGE']):
                popup_lines.append(f"<b>Homepage:</b> <a href='{row['HOMEPAGE']}' target='_blank'>{row['HOMEPAGE']}</a>")
            
            # Opening hours
            if 'opening_hours' in row and pd.notnull(row['opening_hours']):
                formatted_hours = format_opening_hours(row['opening_hours'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            # Add marker
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='green', icon='ticket', prefix='fa')
                ).add_to(kinos_cluster)
    
    kinos_group.add_to(muenster)
# ---- Spielplätze ----
if show_kinder:
    kinder_cluster, kinder_group = create_clustered_feature_group('Spielplätze', min_zoom=15)
    kinder = gpd.read_file(os.path.join(data_dir, 'spielplaetze.geojson'))

    for idx, row in kinder.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            
            name = str(row['Name'])
            formatted_name = ('SP ' + name[2:].strip().title()) if name.startswith('SP') else name.strip().title()
            
            popup_lines = [f"<b>Name:</b> {formatted_name}"]
            
            if 'Ball' in row and pd.notnull(row['Ball']) and row['Ball'] in [1, 2]:
                popup_lines.append("Ballspielplatz vorhanden")
            if 'Skater' in row and pd.notnull(row['Skater']) and str(row['Skater']).strip().lower() == 'ja':
                popup_lines.append("Skateanlage vorhanden")
            if 'Streetball' in row and pd.notnull(row['Streetball']) and str(row['Streetball']).strip().lower() == 'ja':
                popup_lines.append("Streetballplatz vorhanden")
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='cadetblue', icon='child', prefix='fa')
            ).add_to(kinder_cluster)
    
    kinder_group.add_to(muenster)


# ---- Friedhöfe ----
if show_friedhof:
    friedhof_cluster, friedhof_group = create_clustered_feature_group('Friedhöfe', min_zoom=15)
    friedhof = gpd.read_file(os.path.join(data_dir, 'friedhoefe.geojson'))

    for idx, row in friedhof.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            if 'HOMEPAGE' in row and pd.notnull(row['HOMEPAGE']):
                popup_lines.append(f"<b>Homepage:</b> <a href='{row['HOMEPAGE']}' target='_blank'>{row['HOMEPAGE']}</a>")
            
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='darkblue', icon='cross', prefix='fa')
                ).add_to(friedhof_cluster)
    
    friedhof_group.add_to(muenster)


# ---- Refillstationen ----
if show_refill:
    refill_cluster, refill_group = create_clustered_feature_group('Refillstationen', min_zoom=15)
    refill = gpd.read_file(os.path.join(data_dir, 'refill_stations.geojson'))

    for idx, row in refill.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            
            popup_lines = []
            for col in ['Name', 'Straße', 'PLZ', 'Beschreibung', 'Homepage']:
                if col in row and pd.notnull(row[col]):
                    if col == 'Homepage':
                        popup_lines.append(f"<b>{col}:</b> <a href='{row[col]}' target='_blank'>{row[col]}</a>")
                    else:
                        popup_lines.append(f"<b>{col}:</b> {row[col]}")
            
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='blue', icon='tint', prefix='fa')
                ).add_to(refill_cluster)
    
    refill_group.add_to(muenster)


# ---- Gastronomie ----
if show_restaurants or show_cafes or show_bars:
    restaurant_cluster, restaurant_group = create_clustered_feature_group('Restaurants', min_zoom=15)
    bar_cluster, bar_group = create_clustered_feature_group('Bars', min_zoom=15)
    cafe_cluster, cafe_group = create_clustered_feature_group('Cafés', min_zoom=15)
    
    gastro = gpd.read_file(os.path.join(data_dir, 'muenster_gastronomie.geojson'))

    for idx, row in gastro.iterrows():
        if row.geometry and pd.notnull(row.geometry):
            lon, lat = row.geometry.x, row.geometry.y
            amenity = str(row.get('amenity', '')).lower()
            
            # Determine which group to show
            if amenity == 'cafe' and not show_cafes:
                continue
            if amenity in ['bar', 'pub'] and not show_bars:
                continue
            if amenity not in ['cafe', 'bar', 'pub'] and not show_restaurants:
                continue

            popup_lines = []
            if 'name' in row and pd.notnull(row['name']):
                popup_lines.append(f"<b>Name:</b> {row['name']}")
            
            # Address
            address_parts = []
            if 'addr:street' in row and pd.notnull(row['addr:street']):
                address_parts.append(str(row['addr:street']))
                if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
                    address_parts.append(str(row['addr:housenumber']) + ',')
            if 'addr:postcode' in row and pd.notnull(row['addr:postcode']):
                address_parts.append(str(row['addr:postcode']))
            if address_parts:
                popup_lines.append(f"<b>Adresse:</b> {' '.join(address_parts)}")
            
            # Phone
            if 'contact:phone' in row and pd.notnull(row['contact:phone']):
                popup_lines.append(f"<b>Telefonnummer:</b> {row['contact:phone']}")
            
            # Website
            if 'website' in row and pd.notnull(row['website']):
                popup_lines.append(f"<b>Homepage:</b> <a href='{row['website']}' target='_blank'>{row['website']}</a>")
            
            # Opening hours
            if 'opening_hours' in row and pd.notnull(row['opening_hours']):
                formatted_hours = format_opening_hours(row['opening_hours'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            # Determine category
            if amenity == 'cafe':
                group, icon, color = cafe_cluster, 'coffee', 'red'
            elif amenity in ['bar', 'pub']:
                group, icon, color = bar_cluster, 'beer', 'darkred'
            else:
                group, icon, color = restaurant_cluster, 'cutlery', 'lightred'
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(group)
    
    if show_restaurants:
        restaurant_group.add_to(muenster)
    if show_bars:
        bar_group.add_to(muenster)
    if show_cafes:
        cafe_group.add_to(muenster)

# ---- Toiletten ----
if show_toiletten:
    toiletten_cluster, toiletten_group = create_clustered_feature_group('Toiletten', min_zoom=15)
    toiletten = gpd.read_file(os.path.join(data_dir, 'toiletten-mit-oz.geojson'))

    for idx, row in toiletten.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'Name' in row and pd.notnull(row['Name']):
                popup_lines.append(f"<b>Name:</b> {row['Name']}")
            if 'Barrierefrei' in row and pd.notnull(row['Barrierefrei']):
                popup_lines.append(f"<b>Barrierefrei:</b> {row['Barrierefrei']}")
            
            # Address
            address = ''
            if 'addr:street' in row and pd.notnull(row['addr:street']):
                address += row['addr:street']
            if 'addr:housenumber' in row and pd.notnull(row['addr:housenumber']):
                address += f" {row['addr:housenumber']}"
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
            
            # Opening hours
            if 'Öffnungszeiten' in row and pd.notnull(row['Öffnungszeiten']):
                formatted_hours = format_opening_hours(row['Öffnungszeiten'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='gray', icon='restroom', prefix='fa')
            ).add_to(toiletten_cluster)
    
    toiletten_group.add_to(muenster)
# ---- Bäder ----
if show_baeder:
    baeder_cluster, baeder_group = create_clustered_feature_group('Bäder', min_zoom=15)
    baeder = gpd.read_file(os.path.join(data_dir, 'baeder.geojson'))

    for idx, row in baeder.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            if 'LINK1' in row and pd.notnull(row['LINK1']):
                popup_lines.append(f"<b>Homepage:</b> <a href='{row['LINK1']}' target='_blank'>{row['LINK1']}</a>")
            if 'opening_hours' in row and pd.notnull(row['opening_hours']):
                formatted_hours = format_opening_hours(row['opening_hours'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                icon=folium.Icon(color='lightblue', icon='swimming-pool', prefix='fa')
            ).add_to(baeder_cluster)
    
    baeder_group.add_to(muenster)


# ---- Saunen ----
if show_sauna:
    sauna_cluster, sauna_group = create_clustered_feature_group('Saunen', min_zoom=15)
    sauna = gpd.read_file(os.path.join(data_dir, 'sauna.geojson'))

    for idx, row in sauna.iterrows():
        if row.geometry and row.geometry.is_valid:
            if row.geometry.geom_type == 'Polygon':
                point = row.geometry.centroid
                lon, lat = point.x, point.y
            else:
                lon, lat = row.geometry.x, row.geometry.y
            
            popup_lines = []
            if 'name' in row and pd.notnull(row['name']):
                popup_lines.append(f"<b>Name:</b> {row['name']}")
            if 'opening_hours' in row and pd.notnull(row['opening_hours']):
                formatted_hours = format_opening_hours(str(row['opening_hours']))
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            if 'phone' in row and pd.notnull(row['phone']):
                popup_lines.append(f"<b>Telefon:</b> {row['phone']}")
            if 'website' in row and pd.notnull(row['website']):
                website = str(row['website']).strip()
                if not website.startswith(('http://', 'https://')):
                    website = 'https://' + website
                popup_lines.append(f"<b>Homepage:</b> <a href='{website}' target='_blank'>{website}</a>")
            
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='darkblue', icon='hot-tub', prefix='fa')
                ).add_to(sauna_cluster)
    
    sauna_group.add_to(muenster)


# ---- Theater ----
if show_theater:
    theater_cluster, theater_group = create_clustered_feature_group('Theater', min_zoom=15)
    theater = gpd.read_file(os.path.join(data_dir, 'theater.geojson'))

    for idx, row in theater.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address_parts = []
            if 'STR_NAME' in row and pd.notnull(row['STR_NAME']):
                address_parts.append(str(row['STR_NAME']))
                if 'HSNR' in row and pd.notnull(row['HSNR']):
                    address_parts.append(str(int(row['HSNR'])) + ',')
            if 'PLZ' in row and pd.notnull(row['PLZ']):
                address_parts.append(str(int(row['PLZ'])))
            if address_parts:
                popup_lines.append(f"<b>Adresse:</b> {' '.join(address_parts)}")
            if 'TEL' in row and pd.notnull(row['TEL']):
                popup_lines.append(f"<b>Telefonnummer:</b> {row['TEL']}")
            if 'HOMEPAGE' in row and pd.notnull(row['HOMEPAGE']):
                popup_lines.append(f"<b>Homepage:</b> <a href='{row['HOMEPAGE']}' target='_blank'>{row['HOMEPAGE']}</a>")
            if 'opening_hours' in row and pd.notnull(row['opening_hours']):
                formatted_hours = format_opening_hours(row['opening_hours'])
                popup_lines.append(f"<b>Öffnungszeiten:</b><br>{formatted_hours}")
            
            if popup_lines:
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup("<br>".join(popup_lines), max_width=300),
                    icon=folium.Icon(color='darkpurple', icon='theater-masks', prefix='fa')
                ).add_to(theater_cluster)
    
    theater_group.add_to(muenster)


# ---- Grünflächen ----
if show_gruen:
    gruenflaechen_cluster, gruenflaechen_group = create_clustered_feature_group('Grünflächen', min_zoom=14)
    gruenflaechen = gpd.read_file(os.path.join(data_dir, 'gruenflaechen.geojson'))
    
    for col in gruenflaechen.select_dtypes(include=['datetime64']).columns:
        gruenflaechen[col] = gruenflaechen[col].astype(str)

    def style_function(feature):
        return {
            'fillColor': '#78c679',
            'color': '#2ca25f',
            'weight': 1,
            'fillOpacity': 0.7,
            'opacity': 0.8
        }

    folium.GeoJson(
        gruenflaechen,
        name='Grünflächen',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['name'],
            aliases=[''],
            localize=True,
            sticky=True,
            style="""
                font-size: 14px;
                background-color: #F0EFEF;
                border: 1px solid #2ca25f;
                border-radius: 3px;
                padding: 5px;
            """
        )
    ).add_to(gruenflaechen_group)
    
    gruenflaechen_group.add_to(muenster)


# ---- Layer control & Display ----
folium.LayerControl().add_to(muenster)
st_folium(muenster, width=1200, height=800)

