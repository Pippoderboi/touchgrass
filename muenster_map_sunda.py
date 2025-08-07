from streamlit_folium import st_folium
import streamlit as st
import geopandas as gpd
import pandas as pd
import os
import folium
from folium.plugins import MarkerCluster
from formatting_openhour import format_opening_hours
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# ---- Algorithmus Classes ----
class Ort(Enum):
    DRINNEN = "drinnen"
    DRAUSSEN = "draussen"

class Stimmung(Enum):
    AKTIV = "aktiv"
    ENTSPANNT = "entspannt"
    KULTURELL = "kulturell"

class Sozial(Enum):
    RUHE = "ruhe"
    GESELLSCHAFT = "gesellschaft"

@dataclass
class Empfehlung:
    kategorie: str
    score: int
    grund: str = ""

class EmpfehlungsAlgorithmus:
    def __init__(self):
        self.min_score = 4
        self.fallback_score = 3
        self.min_empfehlungen = 3
        
        self.INDOOR_SPORTS = [
            'krafträume', 'dreifachhalle', 'einfachhallen', 'gymnastikräume',
            'zweifachhalle', 'gymnastikraum'
        ]
        
        self.OUTDOOR_SPORTS = [
            'skateanlage', 'skateanlagen', 'speckbrettanlage', 'speckbrettanlagen',
            'beachvolleyballanlage', 'beachvolleyballanlagen', 'trimmanlage', 
            'trimmanlagen', 'bouleanlage', 'bouleanlagen'
        ]
        
        self.kategorien_scores = {
            'drinnen': {
                'bäder': {'aktiv': 3, 'entspannt': 3, 'kulturell': 0, 'ruhe': 2, 'gesellschaft': 2},
                'saunen': {'aktiv': 1, 'entspannt': 3, 'kulturell': 1, 'ruhe': 3, 'gesellschaft': 2},
                'büchereien': {'aktiv': 1, 'entspannt': 3, 'kulturell': 3, 'ruhe': 3, 'gesellschaft': 1},
                'kinos': {'aktiv': 1, 'entspannt': 2, 'kulturell': 3, 'ruhe': 2, 'gesellschaft': 2},
                'theater': {'aktiv': 1, 'entspannt': 2, 'kulturell': 3, 'ruhe': 2, 'gesellschaft': 3},
                'museen': {'aktiv': 2, 'entspannt': 2, 'kulturell': 3, 'ruhe': 3, 'gesellschaft': 2},
                'indoor_sports': {'aktiv': 3, 'entspannt': 1, 'kulturell': 0, 'ruhe': 1, 'gesellschaft': 3},
            },
            'draussen': {
                'bäder': {'aktiv': 3, 'entspannt': 3, 'kulturell': 0, 'ruhe': 2, 'gesellschaft': 2},
                'friedhöfe': {'aktiv': 1, 'entspannt': 3, 'kulturell': 2, 'ruhe': 3, 'gesellschaft': 0},
                'give_boxen': {'aktiv': 2, 'entspannt': 2, 'kulturell': 1, 'ruhe': 2, 'gesellschaft': 2},
                'grünflächen': {'aktiv': 3, 'entspannt': 3, 'kulturell': 0, 'ruhe': 3, 'gesellschaft': 2},
                'spielplätze': {'aktiv': 3, 'entspannt': 2, 'kulturell': 0, 'ruhe': 1, 'gesellschaft': 3},
                'tischtennisplatten': {'aktiv': 3, 'entspannt': 1, 'kulturell': 0, 'ruhe': 2, 'gesellschaft': 3},
                'outdoor_sports': {'aktiv': 3, 'entspannt': 1, 'kulturell': 0, 'ruhe': 1, 'gesellschaft': 2},
            }
        }
        
        self.immer_dabei = ['refill_stationen', 'toiletten']
        self.kinder_kategorien = {
            'beide': ['still_wickelplätze'],
            'draussen': ['spielplätze']
        }
        self.gastronomie_kategorien = ['restaurants', 'cafés']

    def empfehlung_generieren(self, ort: Ort, stimmung: Stimmung, sozial: Sozial, 
                            kinder: bool = False, gastronomie: bool = False) -> List[str]:
        verfügbare_kategorien = list(self.kategorien_scores[ort.value].keys())
        empfehlungen_mit_score = []
        
        for kategorie in verfügbare_kategorien:
            scores = self.kategorien_scores[ort.value][kategorie]
            stimmungs_score = scores[stimmung.value]
            sozial_score = scores[sozial.value]
            gesamt_score = stimmungs_score + sozial_score
            
            empfehlung = Empfehlung(
                kategorie=kategorie,
                score=gesamt_score,
                grund=f"{stimmung.value}:{stimmungs_score} + {sozial.value}:{sozial_score}"
            )
            empfehlungen_mit_score.append(empfehlung)
        
        gefilterte_empfehlungen = [e for e in empfehlungen_mit_score if e.score >= self.min_score]
        
        if len(gefilterte_empfehlungen) < self.min_empfehlungen:
            gefilterte_empfehlungen = [e for e in empfehlungen_mit_score if e.score >= self.fallback_score]
        
        gefilterte_empfehlungen.sort(key=lambda x: x.score, reverse=True)
        basis_kategorien = [e.kategorie for e in gefilterte_empfehlungen]
        finale_kategorien = self._modifier_anwenden(basis_kategorien, ort, kinder, gastronomie)
        
        return finale_kategorien

    def _modifier_anwenden(self, basis_kategorien: List[str], ort: Ort, kinder: bool, gastronomie: bool) -> List[str]:
        finale_kategorien = []
        
        for kategorie in basis_kategorien:
            if kategorie == 'indoor_sports':
                finale_kategorien.extend(self.INDOOR_SPORTS)
            elif kategorie == 'outdoor_sports':
                finale_kategorien.extend(self.OUTDOOR_SPORTS)
            else:
                finale_kategorien.append(kategorie)
        
        finale_kategorien.extend(self.immer_dabei)
        
        if kinder:
            finale_kategorien.extend(self.kinder_kategorien['beide'])
            if ort == Ort.DRAUSSEN:
                for kategorie in self.kinder_kategorien['draussen']:
                    if kategorie not in finale_kategorien:
                        finale_kategorien.append(kategorie)
        
        if gastronomie:
            finale_kategorien.extend(self.gastronomie_kategorien)
        
        return finale_kategorien

# ---- Mapping Dictionary ----
ALGORITHM_TO_STREAMLIT_MAPPING = {
    'museen': 'show_museen',
    'büchereien': 'show_buechereien',
    'krafträume': 'show_sport_drinnen',
    'dreifachhalle': 'show_sport_drinnen',
    'einfachhallen': 'show_sport_drinnen',
    'gymnastikräume': 'show_sport_drinnen',
    'zweifachhalle': 'show_sport_drinnen',
    'gymnastikraum': 'show_sport_drinnen',
    'skateanlage': 'show_sport_draussen',
    'skateanlagen': 'show_sport_draussen',
    'speckbrettanlage': 'show_sport_draussen',
    'speckbrettanlagen': 'show_sport_draussen',
    'beachvolleyballanlage': 'show_sport_draussen',
    'beachvolleyballanlagen': 'show_sport_draussen',
    'trimmanlage': 'show_sport_draussen',
    'trimmanlagen': 'show_sport_draussen',
    'bouleanlage': 'show_sport_draussen',
    'bouleanlagen': 'show_sport_draussen',
    'tischtennisplatten': 'show_tischtennis',
    'still_wickelplätze': 'show_wickelplaetze',
    'give_boxen': 'show_giveboxen',
    'kinos': 'show_kinos',
    'spielplätze': 'show_kinder',
    'friedhöfe': 'show_friedhof',
    'refill_stationen': 'show_refill',
    'restaurants': 'show_restaurants',
    'cafés': 'show_cafes',
    'toiletten': 'show_toiletten',
    'bäder': 'show_baeder',
    'saunen': 'show_sauna',
    'theater': 'show_theater',
    'grünflächen': 'show_gruen'
}

# ---- Setup ----
st.set_page_config(layout="wide", page_title="Münster Empfehlungen")

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'algorithm'
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'empfehlungen' not in st.session_state:
    st.session_state.empfehlungen = []

# ---- Algorithmus Landing Page ----
def run_algorithm():
    st.title("🏛️ Empfehlungsalgorithmus für Orte und Aktivitäten")
    st.markdown("---")
    
    algorithmus = EmpfehlungsAlgorithmus()
    
    if st.session_state.step == 1:
        st.header("1️⃣ Möchtest du drinnen oder draußen etwas machen?")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🏠 Drinnen", use_container_width=True, type="primary"):
                st.session_state.ort = Ort.DRINNEN
                st.session_state.step = 2
                st.rerun()
        
        with col2:
            if st.button("🌳 Draußen", use_container_width=True, type="primary"):
                st.session_state.ort = Ort.DRAUSSEN
                st.session_state.step = 2
                st.rerun()
    
    elif st.session_state.step == 2:
        st.header("2️⃣ Wie ist deine Stimmung heute?")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💪 Aktiv\nIch will mich bewegen!", use_container_width=True, type="primary"):
                st.session_state.stimmung = Stimmung.AKTIV
                st.session_state.step = 3
                st.rerun()
        
        with col2:
            if st.button("😌 Entspannt\nIch möchte zur Ruhe kommen", use_container_width=True, type="primary"):
                st.session_state.stimmung = Stimmung.ENTSPANNT
                st.session_state.step = 3
                st.rerun()
        
        with col3:
            if st.button("🎭 Kulturell\nIch will etwas lernen/erleben", use_container_width=True, type="primary"):
                st.session_state.stimmung = Stimmung.KULTURELL
                st.session_state.step = 3
                st.rerun()
    
    elif st.session_state.step == 3:
        st.header("3️⃣ Suchst du eher Ruhe oder Gesellschaft?")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧘 Ruhe\nIch möchte für mich sein", use_container_width=True, type="primary"):
                st.session_state.sozial = Sozial.RUHE
                st.session_state.step = 4
                st.rerun()
        
        with col2:
            if st.button("👥 Gesellschaft\nIch möchte andere Menschen treffen", use_container_width=True, type="primary"):
                st.session_state.sozial = Sozial.GESELLSCHAFT
                st.session_state.step = 4
                st.rerun()
    
    elif st.session_state.step == 4:
        st.header("🧒 Hast du Kinder dabei?")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Ja", use_container_width=True, type="primary"):
                st.session_state.kinder = True
                st.session_state.step = 5
                st.rerun()
        
        with col2:
            if st.button("❌ Nein", use_container_width=True, type="primary"):
                st.session_state.kinder = False
                st.session_state.step = 5
                st.rerun()
    
    elif st.session_state.step == 5:
        st.header("🍽️ Möchtest du gerne etwas essen oder trinken?")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Ja", use_container_width=True, type="primary"):
                st.session_state.gastronomie = True
                # Generiere Empfehlungen
                empfehlungen = algorithmus.empfehlung_generieren(
                    st.session_state.ort,
                    st.session_state.stimmung,
                    st.session_state.sozial,
                    st.session_state.kinder,
                    st.session_state.gastronomie
                )
                st.session_state.empfehlungen = empfehlungen
                st.session_state.page = 'map'
                st.session_state.step = 1  # Reset für nächste Runde
                st.rerun()
        
        with col2:
            if st.button("❌ Nein", use_container_width=True, type="primary"):
                st.session_state.gastronomie = False
                # Generiere Empfehlungen
                empfehlungen = algorithmus.empfehlung_generieren(
                    st.session_state.ort,
                    st.session_state.stimmung,
                    st.session_state.sozial,
                    st.session_state.kinder,
                    st.session_state.gastronomie
                )
                st.session_state.empfehlungen = empfehlungen
                st.session_state.page = 'map'
                st.session_state.step = 1  # Reset für nächste Runde
                st.rerun()

# ---- Map Functions ----
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

def run_map():
    st.title("🗺️ Deine personalisierte Münster Karte")
    
    # Button für neue Empfehlung
    if st.button("🔄 Neue Empfehlung erstellen", type="secondary"):
        st.session_state.page = 'algorithm'
        st.session_state.step = 1
        st.rerun()
    
    # Zeige Empfehlungen
    if st.session_state.empfehlungen:
        st.success(f"📍 Basierend auf deinen Antworten wurden {len(st.session_state.empfehlungen)} Kategorien für dich ausgewählt!")
        
        # Base paths
        base_dir = os.path.dirname(__file__)
        data_dir = os.path.join(base_dir, "raw_data_geojson")
        
        # Initialize all checkboxes to False
        checkbox_states = {
            'show_museen': False,
            'show_buechereien': False,
            'show_sport_drinnen': False,
            'show_sport_draussen': False,
            'show_tischtennis': False,
            'show_wickelplaetze': False,
            'show_giveboxen': False,
            'show_kinos': False,
            'show_kinder': False,
            'show_friedhof': False,
            'show_refill': False,
            'show_restaurants': False,
            'show_cafes': False,
            'show_bars': False,
            'show_toiletten': False,
            'show_baeder': False,
            'show_sauna': False,
            'show_theater': False,
            'show_gruen': False
        }
        
        # Set checkboxes based on algorithm recommendations
        for empfehlung in st.session_state.empfehlungen:
            if empfehlung in ALGORITHM_TO_STREAMLIT_MAPPING:
                checkbox_key = ALGORITHM_TO_STREAMLIT_MAPPING[empfehlung]
                checkbox_states[checkbox_key] = True
        
        # Sidebar
        st.sidebar.header("Kategorien auswählen")
        st.sidebar.markdown("*Basierend auf deinen Antworten vorausgewählt*")
        
        # Create checkboxes with pre-selected values
        show_museen = st.sidebar.checkbox("Museen", checkbox_states['show_museen'])
        show_buechereien = st.sidebar.checkbox("Büchereien", checkbox_states['show_buechereien'])
        show_sport_drinnen = st.sidebar.checkbox("Sportstätten drinnen", checkbox_states['show_sport_drinnen'])
        show_sport_draussen = st.sidebar.checkbox("Sportstätten draußen", checkbox_states['show_sport_draussen'])
        show_tischtennis = st.sidebar.checkbox("Tischtennisplatten", checkbox_states['show_tischtennis'])
        show_wickelplaetze = st.sidebar.checkbox("Wickelplätze", checkbox_states['show_wickelplaetze'])
        show_giveboxen = st.sidebar.checkbox("Give Boxen", checkbox_states['show_giveboxen'])
        show_kinos = st.sidebar.checkbox("Kinos", checkbox_states['show_kinos'])
        show_kinder = st.sidebar.checkbox("Spielplätze", checkbox_states['show_kinder'])
        show_friedhof = st.sidebar.checkbox("Friedhöfe", checkbox_states['show_friedhof'])
        show_refill = st.sidebar.checkbox("Refillstationen", checkbox_states['show_refill'])
        show_restaurants = st.sidebar.checkbox("Restaurants", checkbox_states['show_restaurants'])
        show_cafes = st.sidebar.checkbox("Cafés", checkbox_states['show_cafes'])
        show_bars = st.sidebar.checkbox("Bars", checkbox_states['show_bars'])
        show_toiletten = st.sidebar.checkbox("Toiletten", checkbox_states['show_toiletten'])
        show_baeder = st.sidebar.checkbox("Bäder", checkbox_states['show_baeder'])
        show_sauna = st.sidebar.checkbox("Saunen", checkbox_states['show_sauna'])
        show_theater = st.sidebar.checkbox("Theater", checkbox_states['show_theater'])
        show_gruen = st.sidebar.checkbox("Grünflächen", checkbox_states['show_gruen'])
        
        # Base map
        muenster = folium.Map(location=[51.96, 7.62], zoom_start=12.5)
        
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
        # For brevity, I'm not copying the entire map code, but it would be exactly the same
        
        # Layer control & Display
        folium.LayerControl().add_to(muenster)
        st_folium(muenster, width=1200, height=800)

# ---- Main App ----
def main():
    if st.session_state.page == 'algorithm':
        run_algorithm()
    elif st.session_state.page == 'map':
        run_map()

if __name__ == "__main__":
    main()