from streamlit_folium import st_folium
import time
import streamlit as st
import streamlit.components.v1 as components 
from streamlit_js_eval import get_geolocation
import geopandas as gpd
import pandas as pd
import os
import folium
import re
from folium.plugins import MarkerCluster
from folium.plugins import LocateControl
from geopy.distance import geodesic
from formatting_openhour import format_opening_hours
from functools import lru_cache
from typing import Optional, List, Dict, Any

def _first_val(row: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in row and pd.notnull(row[k]):
            return str(row[k]).strip()
    return None

def _normalize_plz(plz: Optional[str]) -> Optional[str]:
    if plz is None:
        return None
    s = str(plz).strip()
    # Hole eine 5-stellige PLZ aus gemischten Strings (z.B. "48143.0" oder "48143 Münster")
    m = re.search(r'\b(\d{5})\b', s)
    return m.group(1) if m else s

def format_address(
    row,
    street_keys=("addr:street","STR_NAME","Strname","Straße","street","strasse"),
    hnr_keys=("addr:housenumber","HSNR","Hsnr","Hausnummer","hnr"),
    plz_keys=("addr:postcode","PLZ","Plz","postcode","zip"),
    city="Münster",
):
    def first(keys):
        for k in keys:
            if k in row and pd.notnull(row[k]):
                return str(row[k]).strip()
        return None

    def normalize_hnr(h):
        if h is None:
            return None
        if isinstance(h, float):
            return str(int(h)) if h.is_integer() else str(h).rstrip("0").rstrip(".")
        s = str(h).strip()
        m = re.fullmatch(r'(\d+)(?:\.0+)?', s)
        return m.group(1) if m else s

    def normalize_plz(p):
        if p is None:
            return None
        s = str(p).strip()
        m = re.search(r'\b(\d{5})\b', s)
        return m.group(1) if m else None

    street = first(street_keys)
    hnr    = normalize_hnr(first(hnr_keys))
    plz    = normalize_plz(first(plz_keys))

    # Wenn keine Straße vorhanden → keine PLZ, kein Münster
    if not street:
        return ""

    # Straße + ggf. Hausnummer
    main_parts = [street]
    if hnr:
        main_parts.append(hnr)
    main = " ".join(main_parts).strip()

    # Falls PLZ vorhanden → Komma + PLZ + Münster
    if plz:
        return f"{main}, {plz} {city}"
    else:
        return main

# ----Cache -Loader for geo files
@lru_cache(maxsize=8192)
def fmt_hours_cached(s: str) -> str:
    return format_opening_hours(s)

@st.cache_data (show_spinner=False)
def preprocess_gastro(path: str, mtime:float):
    gdf = gpd.read_file(path)
    gdf= gdf[gdf.geometry.notnull()].copy()
    gdf["lon"]=gdf.geometry.x
    gdf["lat"]=gdf.geometry.y
    gdf["amenity_lc"] = gdf.get("amenity","").str.lower()
    
    def popup_html(row:pd.Series)-> str:
        lines=[]
        name=row.get("name")
        if pd.notnull(name):
            lines.append(f"<b>Name:</b> {name}")
        # Adresse
        address = format_address(row)
        if address:
            lines.append(f"<b>Adresse:</b> {address}")

        phone = row.get("contact:phone")
        if pd.notnull(phone):
            lines.append(f"<b>Telefonnummer:</b> {phone}")

        website = row.get("website")
        if pd.notnull(website):
            lines.append(f"<b>Homepage:</b> <a href='{website}' target='_blank'>{website}</a>")

        oh = row.get("opening_hours")
        if pd.notnull(oh):
            lines.append(f"<b>Öffnungszeiten:</b><br>{fmt_hours_cached(str(oh))}")

        return "<br>".join(lines)

    gdf["popup"] = gdf.apply(popup_html, axis=1)

    def to_list(df):
        # [(lat, lon, popup_html), ...]
        return list(zip(df["lat"].tolist(), df["lon"].tolist(), df["popup"].tolist()))

    cafes = to_list(gdf[gdf["amenity_lc"] == "cafe"])
    bars  = to_list(gdf[gdf["amenity_lc"].isin(["bar", "pub"])])
    rest  = to_list(gdf[~gdf["amenity_lc"].isin(["cafe", "bar", "pub"])])

    return {"cafes": cafes, "bars": bars, "restaurants": rest}        

DEBUG_CACHE = False

@st.cache_data (show_spinner=False)
def _load_gdf_cached(path: str, mtime: float):
    return gpd.read_file(path)

def cached_read(filename:str):
    path= os.path.join(data_dir, filename)
    mtime=os.path.getmtime(path)

    t0 =time.perf_counter()
    gdf =_load_gdf_cached(path,mtime)
    dt=time.perf_counter()-t0
    if DEBUG_CACHE:
        label="HIT" if dt <0.01 else "MISS"
        st.caption(f"⏱️ {os.path.basename(filename)} geladen in {dt:.4f}s — {label}")
    return gdf

# ---- Setup ----
st.set_page_config(layout="wide")
st.title("Münster Map")

# Base paths
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, "raw_data_geojson")

#Base map

if "map_view" not in st.session_state:
    st.session_state.map_view = {"center": [51.96, 7.62], "zoom": 12.5}

center = st.session_state.map_view["center"]
zoom   = st.session_state.map_view["zoom"]

muenster = folium.Map(location=center, zoom_start=zoom)

# Add Location Control
LocateControl(auto_start=False).add_to(muenster)

# Helper to create clustered groups
def create_clustered_feature_group(name, min_zoom=13, show=True):
    fg = folium.FeatureGroup(name=name, show=show)
    cluster = MarkerCluster(
        name=name,
        options={
            "maxClusterRadius": 80,
            "disableClusteringAtZoom": min_zoom,
            "spiderfyDistanceMultiplier": 2,
            # clientseitiges chunked Loading
            "chunkedLoading": True,     # Marker in Blöcken einfügen
            "chunkInterval": 100,       # ms Arbeitszeit pro Block (Default: ~200)
            "chunkDelay": 25,           # ms Pause zwischen Blöcken
            # Optional: spart CPU beim Hover (Polygon-Abdeckung)
            "showCoverageOnHover": False
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
    museen = cached_read('museen_mit_opening_hours.geojson')
    for idx, row in museen.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address = format_address(row)
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
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
    buechereien = cached_read('buechereien_mit_opening_hours.geojson')
    for idx, row in buechereien.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address = format_address(row)
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
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

#Sportstätten

if show_sport_drinnen or show_sport_draussen:
    sport_drinnen_cluster, sport_drinnen_group = create_clustered_feature_group('Sportstätte drinnen', min_zoom=15)
    sport_draussen_cluster, sport_draussen_group = create_clustered_feature_group('Sportstätte draußen', min_zoom=15)
    
    sportstaetten = cached_read('sportstaetten_mit_opening_hours.geojson')

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
            address = format_address(row)
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
            
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
    tischtennis = cached_read('tischtennisplatten_muenster.geojson')

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
    wickelplaetze = cached_read('still-und-wickelplaetze-muenster-2023.geojson')

    for idx, row in wickelplaetze.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            # Name
            if 'Name' in row and pd.notnull(row['Name']):
                popup_lines.append(f"<b>Name:</b> {row['Name']}")
            
            # Address & Stockwerk
            address = format_address(row)
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
            
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
    give_boxen = cached_read('give_boxen.geojson')

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
    kinos = cached_read('kinos.geojson')

    for idx, row in kinos.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            # Name
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            
            # Address with HSNR + PLZ
            address = format_address(row)
            if address:
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
    kinder = cached_read('spielplaetze.geojson')

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
    friedhof = cached_read('friedhoefe.geojson')

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
    refill = cached_read('refill_stations.geojson')

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

# ---- Gastronomie (vorverarbeitet + gecached) ----
if show_restaurants or show_cafes or show_bars:
    restaurant_cluster, restaurant_group = create_clustered_feature_group('Restaurants', min_zoom=15)
    bar_cluster, bar_group = create_clustered_feature_group('Bars', min_zoom=15)
    cafe_cluster, cafe_group = create_clustered_feature_group('Cafés', min_zoom=15)

    gastro_path = os.path.join(data_dir, 'muenster_gastronomie.geojson')
    g = preprocess_gastro(gastro_path, os.path.getmtime(gastro_path))  # liest + cached + baut Marker-Listen

    if show_cafes:
        for lat, lon, html in g["cafes"]:
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(html, max_width=300),
                icon=folium.Icon(color='red', icon='coffee', prefix='fa')
            ).add_to(cafe_cluster)

    if show_bars:
        for lat, lon, html in g["bars"]:
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(html, max_width=300),
                icon=folium.Icon(color='darkred', icon='beer', prefix='fa')
            ).add_to(bar_cluster)

    if show_restaurants:
        for lat, lon, html in g["restaurants"]:
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(html, max_width=300),
                icon=folium.Icon(color='lightred', icon='cutlery', prefix='fa')
            ).add_to(restaurant_cluster)

    if show_restaurants:
        restaurant_group.add_to(muenster)
    if show_bars:
        bar_group.add_to(muenster)
    if show_cafes:
        cafe_group.add_to(muenster)

# ---- Toiletten ----
if show_toiletten:
    toiletten_cluster, toiletten_group = create_clustered_feature_group('Toiletten', min_zoom=15)
    toiletten = cached_read('toiletten-mit-oz.geojson')

    for idx, row in toiletten.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'Name' in row and pd.notnull(row['Name']):
                popup_lines.append(f"<b>Name:</b> {row['Name']}")
            if 'Barrierefrei' in row and pd.notnull(row['Barrierefrei']):
                popup_lines.append(f"<b>Barrierefrei:</b> {row['Barrierefrei']}")
            
            # Address
            address = format_address(row)
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
    baeder = cached_read('baeder.geojson')

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
    sauna = cached_read('sauna.geojson')

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
    theater = cached_read('theater.geojson')

    for idx, row in theater.iterrows():
        if row.geometry:
            lon, lat = row.geometry.x, row.geometry.y
            popup_lines = []
            
            if 'NAME' in row and pd.notnull(row['NAME']):
                popup_lines.append(f"<b>Name:</b> {row['NAME']}")
            address = format_address(row)
            if address:
                popup_lines.append(f"<b>Adresse:</b> {address}")
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
    gruenflaechen = cached_read('gruenflaechen.geojson')
    
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

# -----------------------------
# Geolocation (minimal, ohne Refresh-Button)
# -----------------------------

# Container für Hinweise
location_container = st.empty()

# Session-State vorbereiten
if "user_location" not in st.session_state:
    st.session_state.user_location = None

# Geolocation-Component: fragt Browser-Standort ab
geo_val = components.html("""
<script>
(function(){
  function requestLocation() {
    if (!navigator.geolocation) {
      Streamlit.setComponentValue({lat: 51.96, lng: 7.62, accuracy: 1000, error: true});
      return;
    }
    navigator.geolocation.getCurrentPosition(
      function(position) {
        const { latitude: lat, longitude: lng, accuracy } = position.coords;
        Streamlit.setComponentValue({ lat: lat, lng: lng, accuracy: accuracy, error: false });
      },
      function() {
        Streamlit.setComponentValue({ lat: 51.96, lng: 7.62, accuracy: 1000, error: true });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }
  document.addEventListener("DOMContentLoaded", function(){ setTimeout(requestLocation, 500); });
})();
</script>
""", height=0)

# Rückgabewert übernehmen und Hinweis ausblenden
if isinstance(geo_val, dict) and "lat" in geo_val and "lng" in geo_val:
    st.session_state.user_location = {
        "lat": geo_val["lat"],
        "lng": geo_val["lng"],
        "accuracy": geo_val.get("accuracy", 0),
        "error": geo_val.get("error", False),
    }
    location_container.empty()   # Nachricht sofort weg

# Wenn Standort vorhanden: Marker + Center-Button
if st.session_state.user_location:
    user_lat = st.session_state.user_location['lat']
    user_lng = st.session_state.user_location['lng']
    accuracy = st.session_state.user_location.get('accuracy', 0)

    folium.CircleMarker(
        location=[user_lat, user_lng],
        radius=10,
        color='#3388ff',
        fill=True,
        fill_color='#3388ff',
        fill_opacity=0.7,
        popup=f"Ihr Standort (Genauigkeit: {accuracy:.0f}m)"
    ).add_to(muenster)

    if accuracy > 0:
        folium.Circle(
            location=[user_lat, user_lng],
            radius=accuracy,
            color='#3388ff',
            fill=True,
            fill_color='#3388ff',
            fill_opacity=0.2,
            popup=f'Genauigkeit: {accuracy:.0f} Meter'
        ).add_to(muenster)

    if st.button('Karte auf meinen Standort zentrieren'):
        st.session_state.map_view = {"center": [user_lat, user_lng], "zoom": 15}
#else:
 #   location_container.warning("Warte auf Standortermittlung... Bitte erlauben Sie den Zugriff auf Ihren Standort.")

# ---- Layer control & Display ----
folium.LayerControl().add_to(muenster)

# Karte rendern (Map-Interaktionen lösen KEINEN Rerun mehr aus)
map_event = st_folium(
    muenster,
    width=1200,
    height=800,
    key="map",
    returned_objects=[],  # weiterhin leer -> keine Reruns durch Pan/Zoom
    center=st.session_state.map_view["center"],
    zoom=st.session_state.map_view["zoom"],
)

# Falls unser JS via Streamlit.setComponentValue(...) Daten geschickt hat:
if isinstance(map_event, dict) and "lat" in map_event and "lng" in map_event:
    st.session_state.user_location = {
        "lat": map_event["lat"],
        "lng": map_event["lng"],
        "accuracy": map_event.get("accuracy", 0),
        "error": map_event.get("error", False),
    }
    location_container.empty()  # Warnung sofort weg

