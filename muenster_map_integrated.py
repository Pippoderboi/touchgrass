from streamlit_folium import st_folium
import time
import streamlit as st
import streamlit.components.v1 as components 
import geopandas as gpd
import pandas as pd
import os
import folium
import re
from folium.plugins import MarkerCluster
from folium.plugins import LocateControl
from formatting_openhour import format_opening_hours
from functools import lru_cache
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Grund-Setup 
base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, "raw_data_geojson")

# ---- Empfehlungsalgorithmus Integration ----
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
    """Einzelne Empfehlung mit Score für Debugging"""
    kategorie: str
    score: int
    grund: str = ""

class EmpfehlungsAlgorithmus:
    """
    Hauptklasse für den Empfehlungsalgorithmus
    """
    
    def __init__(self):
        self.min_score = 6  # Mindest-Score für Empfehlungen
        self.fallback_score = 5  # Fallback wenn zu wenig Empfehlungen
        self.min_empfehlungen = 2  # Mindestanzahl Empfehlungen
        
        # Sport-Kategorien
        self.INDOOR_SPORTS = [
            'Krafträume', 'Dreifachhalle', 'Einfachhallen', 'Gymnastikräume',
            'Zweifachhalle', 'Gymnastikraum'
        ]
        
        self.OUTDOOR_SPORTS = [
            'Skateanlage', 'Skateanlagen', 'Speckbrettanlage', 'Speckbrettanlagen',
            'Beachvolleyballanlage', 'Beachvolleyballanlagen', 'Trimmanlage', 
            'Trimmanlagen', 'Bouleanlage', 'Bouleanlagen'
        ]
        
        # Scoring-Matrix: Kategorie -> {stimmung/sozial: punkte}
        self.kategorien_scores = {
            'drinnen': {
                'bäder': {'aktiv': 4, 'entspannt': 2, 'kulturell': 1, 'ruhe': 2, 'gesellschaft': 3},
                'saunen': {'aktiv': 1, 'entspannt': 5, 'kulturell': 1, 'ruhe': 4, 'gesellschaft': 2},
                'büchereien': {'aktiv': 1, 'entspannt': 3, 'kulturell': 4, 'ruhe': 4, 'gesellschaft': 2},
                'kinos': {'aktiv': 1, 'entspannt': 3, 'kulturell': 4, 'ruhe': 4, 'gesellschaft': 4},
                'theater': {'aktiv': 1, 'entspannt': 2, 'kulturell': 5, 'ruhe': 2, 'gesellschaft': 3},
                'museen': {'aktiv': 1, 'entspannt': 3, 'kulturell': 5, 'ruhe': 4, 'gesellschaft': 3},
                'indoor_sports': {'aktiv': 5, 'entspannt': 1, 'kulturell': 1, 'ruhe': 1, 'gesellschaft': 4},
            },
            'draussen': {
                'bäder': {'aktiv': 4, 'entspannt': 3, 'kulturell': 1, 'ruhe': 3, 'gesellschaft': 3},
                'friedhöfe': {'aktiv': 1, 'entspannt': 4, 'kulturell': 2, 'ruhe': 5, 'gesellschaft': 1},
                'give_boxen': {'aktiv': 3, 'entspannt': 3, 'kulturell': 3, 'ruhe': 5, 'gesellschaft': 1},
                'grünflächen': {'aktiv': 3, 'entspannt': 5, 'kulturell': 1, 'ruhe': 3, 'gesellschaft': 3},
                'spielplätze': {'aktiv': 4, 'entspannt': 2, 'kulturell': 1, 'ruhe': 1, 'gesellschaft': 4},
                'tischtennisplatten': {'aktiv': 4, 'entspannt': 1, 'kulturell': 1, 'ruhe': 1, 'gesellschaft': 5},
                'outdoor_sports': {'aktiv': 5, 'entspannt': 1, 'kulturell': 1, 'ruhe': 2, 'gesellschaft': 3},
            }
        }
        
        # Modifier-Kategorien (immer hinzugefügt)
        self.immer_dabei = ['refill_stationen', 'toiletten']
        
        # Kinder-spezifische Kategorien
        self.kinder_kategorien = {
            'beide': ['still_wickelplätze'],
            'draussen': ['spielplätze']  # Wird nur draußen hinzugefügt wenn nicht schon da
        }
        
        # Gastronomie-Kategorien
        self.gastronomie_kategorien = ['restaurants', 'cafés']

    def empfehlung_generieren(self, 
                            ort: Ort, 
                            stimmung: Stimmung, 
                            sozial: Sozial, 
                            kinder: bool = False, 
                            gastronomie: bool = False,
                            debug: bool = False) -> tuple[List[str], List[Empfehlung]]:
        """
        Generiert Empfehlungen basierend auf den Eingaben
        
        Returns:
            Tuple[List[str], List[Empfehlung]]: (finale_empfehlungen, debug_infos)
        """
        
        # Schritt 1: Verfügbare Kategorien basierend auf Ort
        verfügbare_kategorien = list(self.kategorien_scores[ort.value].keys())
        
        # Schritt 2: Scoring für jede Kategorie
        empfehlungen_mit_score = []
        
        for kategorie in verfügbare_kategorien:
            scores = self.kategorien_scores[ort.value][kategorie]
            
            # Berechne Gesamtscore: Stimmung + Sozial
            stimmungs_score = scores[stimmung.value]
            sozial_score = scores[sozial.value]
            gesamt_score = stimmungs_score + sozial_score
            
            empfehlung = Empfehlung(
                kategorie=kategorie,
                score=gesamt_score,
                grund=f"{stimmung.value}:{stimmungs_score} + {sozial.value}:{sozial_score}"
            )
            empfehlungen_mit_score.append(empfehlung)
        
        # Schritt 3: Filterung nach Score
        gefilterte_empfehlungen = [e for e in empfehlungen_mit_score if e.score >= self.min_score]
        
        # Fallback: Wenn zu wenig Empfehlungen, senke Schwellenwert
        if len(gefilterte_empfehlungen) < self.min_empfehlungen:
            gefilterte_empfehlungen = [e for e in empfehlungen_mit_score if e.score >= self.fallback_score]
        
        # Sortiere nach Score (höchste zuerst)
        gefilterte_empfehlungen.sort(key=lambda x: x.score, reverse=True)
        
        # Schritt 4: Extrahiere Kategorien für Modifier
        basis_kategorien = [e.kategorie for e in gefilterte_empfehlungen]
        
        # Schritt 5: Modifier anwenden
        finale_kategorien = self._modifier_anwenden(basis_kategorien, ort, kinder, gastronomie)
        
        if debug:
            return finale_kategorien, empfehlungen_mit_score
        else:
            return finale_kategorien, gefilterte_empfehlungen

    def _modifier_anwenden(self, basis_kategorien: List[str], ort: Ort, kinder: bool, gastronomie: bool) -> List[str]:
        """
        Wendet alle Modifier auf die Basis-Empfehlungen an
        """
        finale_kategorien = []
        
        # Spezielle Behandlung für Sport-Kategorien
        for kategorie in basis_kategorien:
            if kategorie == 'indoor_sports':
                # Füge alle Indoor-Sport-Unterkategorien hinzu
                finale_kategorien.extend(self.INDOOR_SPORTS)
            elif kategorie == 'outdoor_sports':
                # Füge alle Outdoor-Sport-Unterkategorien hinzu
                finale_kategorien.extend(self.OUTDOOR_SPORTS)
            else:
                finale_kategorien.append(kategorie)
        
        # Immer-dabei Kategorien hinzufügen
        finale_kategorien.extend(self.immer_dabei)
        
        # Kinder-Modifier
        if kinder:
            # Immer hinzufügen
            finale_kategorien.extend(self.kinder_kategorien['beide'])
            
            # Draußen-spezifisch hinzufügen (nur wenn noch nicht vorhanden)
            if ort == Ort.DRAUSSEN:
                for kategorie in self.kinder_kategorien['draussen']:
                    if kategorie not in finale_kategorien:
                        finale_kategorien.append(kategorie)
        
        # Gastronomie-Modifier
        if gastronomie:
            finale_kategorien.extend(self.gastronomie_kategorien)
        
        return finale_kategorien

# ---- Mapping Dictionary ----
KATEGORIE_MAPPING = {
    'museen': 'show_museen',
    'büchereien': 'show_buechereien',
    'tischtennisplatten': 'show_tischtennis',
    'still_wickelplätze': 'show_wickelplaetze',
    'give_boxen': 'show_giveboxen',
    'kinos': 'show_kinos',
    'spielplätze': 'show_kinder',
    'friedhöfe': 'show_friedhof',
    'refill_stationen': 'show_refill',
    'restaurants': 'show_restaurants',
    'cafés': 'show_cafes',
    'bars': 'show_bars',
    'toiletten': 'show_toiletten',
    'bäder': 'show_baeder',
    'saunen': 'show_sauna',
    'theater': 'show_theater',
    'grünflächen': 'show_gruen',
    'indoor_sports': 'show_sport_drinnen',
    'outdoor_sports': 'show_sport_draussen',
   # INDOOR SPORTS - alle Unterkategorien
   'Krafträume': 'show_sport_drinnen',
   'Dreifachhalle': 'show_sport_drinnen', 
   'Einfachhallen': 'show_sport_drinnen',
   'Gymnastikräume': 'show_sport_drinnen',
   'Zweifachhalle': 'show_sport_drinnen',
   'Gymnastikraum': 'show_sport_drinnen',
   # OUTDOOR SPORTS - alle Unterkategorien  
   'Skateanlage': 'show_sport_draussen',
   'Skateanlagen': 'show_sport_draussen',
   'Speckbrettanlage': 'show_sport_draussen',
   'Speckbrettanlagen': 'show_sport_draussen',
   'Beachvolleyballanlage': 'show_sport_draussen',
   'Beachvolleyballanlagen': 'show_sport_draussen',
   'Trimmanlage': 'show_sport_draussen',
   'Trimmanlagen': 'show_sport_draussen',
   'Bouleanlage': 'show_sport_draussen',
   'Bouleanlagen': 'show_sport_draussen'
}

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

# ---- Streamlit Algorithmus Interface ----
def run_algorithm():
    """
    Führt den Empfehlungsalgorithmus mit Streamlit Interface durch
    """
    algorithmus = EmpfehlungsAlgorithmus()
    
    st.title("🗺️ Empfehlungsalgorithmus für Orte und Aktivitäten")
    st.markdown("---")
    
    # Session State für Algorithmus-Schritte
    if 'algorithm_step' not in st.session_state:
        st.session_state.algorithm_step = 0
    if 'algorithm_data' not in st.session_state:
        st.session_state.algorithm_data = {}
    
    # Schritt 0: Start
    if st.session_state.algorithm_step == 0:
        st.markdown("### Willkommen! 👋")
        st.markdown("Ich helfe dir dabei, die perfekten Orte und Aktivitäten in Münster zu finden.")
        if st.button("🚀 Los geht's!", type="primary"):
            st.session_state.algorithm_step = 1
            st.rerun()
    
    # Schritt 1: Ort
    elif st.session_state.algorithm_step == 1:
        st.markdown("### 1️⃣ Möchtest du drinnen oder draußen etwas machen?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Drinnen", type="primary", use_container_width=True):
                st.session_state.algorithm_data['ort'] = Ort.DRINNEN
                st.session_state.algorithm_step = 2
                st.rerun()
        with col2:
            if st.button("🌳 Draußen", type="primary", use_container_width=True):
                st.session_state.algorithm_data['ort'] = Ort.DRAUSSEN
                st.session_state.algorithm_step = 2
                st.rerun()
    
    # Schritt 2: Stimmung
    elif st.session_state.algorithm_step == 2:
        st.markdown("### 2️⃣ Wie ist deine Stimmung heute?")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💪 Aktiv\nIch will mich bewegen!", type="primary", use_container_width=True):
                st.session_state.algorithm_data['stimmung'] = Stimmung.AKTIV
                st.session_state.algorithm_step = 3
                st.rerun()
        with col2:
            if st.button("🧘 Entspannt\nIch möchte zur Ruhe kommen", type="primary", use_container_width=True):
                st.session_state.algorithm_data['stimmung'] = Stimmung.ENTSPANNT
                st.session_state.algorithm_step = 3
                st.rerun()
        with col3:
            if st.button("🎭 Kulturell\nIch will etwas lernen/erleben", type="primary", use_container_width=True):
                st.session_state.algorithm_data['stimmung'] = Stimmung.KULTURELL
                st.session_state.algorithm_step = 3
                st.rerun()
    
    # Schritt 3: Sozial
    elif st.session_state.algorithm_step == 3:
        st.markdown("### 3️⃣ Suchst du eher Ruhe oder Gesellschaft?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤫 Ruhe\nIch möchte für mich sein", type="primary", use_container_width=True):
                st.session_state.algorithm_data['sozial'] = Sozial.RUHE
                st.session_state.algorithm_step = 4
                st.rerun()
        with col2:
            if st.button("👥 Gesellschaft\nIch möchte andere Menschen treffen", type="primary", use_container_width=True):
                st.session_state.algorithm_data['sozial'] = Sozial.GESELLSCHAFT
                st.session_state.algorithm_step = 4
                st.rerun()
    
    # Schritt 4: Modifier - Kinder
    elif st.session_state.algorithm_step == 4:
        st.markdown("---")
        st.markdown("### 🧒 Hast du Kinder dabei?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ja", type="primary", use_container_width=True):
                st.session_state.algorithm_data['kinder'] = True
                st.session_state.algorithm_step = 5
                st.rerun()
        with col2:
            if st.button("❌ Nein", type="secondary", use_container_width=True):
                st.session_state.algorithm_data['kinder'] = False
                st.session_state.algorithm_step = 5
                st.rerun()
    
    # Schritt 5: Modifier - Gastronomie
    elif st.session_state.algorithm_step == 5:
        st.markdown("### 🍽️ Möchtest du gerne etwas essen oder trinken?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ja", type="primary", use_container_width=True):
                st.session_state.algorithm_data['gastronomie'] = True
                st.session_state.algorithm_step = 6
                st.rerun()
        with col2:
            if st.button("❌ Nein", type="secondary", use_container_width=True):
                st.session_state.algorithm_data['gastronomie'] = False
                st.session_state.algorithm_step = 6
                st.rerun()
    
    # Schritt 6: Ergebnis generieren
    elif st.session_state.algorithm_step == 6:
        st.markdown("### 🤔 Lass mich überlegen...")
        
        with st.spinner("Empfehlungen werden generiert..."):
            time.sleep(1)  # Kurze Pause für UX
            
            empfehlungen, debug_info = algorithmus.empfehlung_generieren(
                ort=st.session_state.algorithm_data['ort'],
                stimmung=st.session_state.algorithm_data['stimmung'],
                sozial=st.session_state.algorithm_data['sozial'],
                kinder=st.session_state.algorithm_data['kinder'],
                gastronomie=st.session_state.algorithm_data['gastronomie'],
                debug=True
            )
            
            st.session_state.algorithm_recommendations = empfehlungen
            st.session_state.algorithm_debug = debug_info
            st.session_state.algorithm_completed = True
            st.session_state.algorithm_step = 7
            st.rerun()
    
    # Schritt 7: Ergebnisse anzeigen
    elif st.session_state.algorithm_step == 7:
        st.success("🎯 Deine persönlichen Empfehlungen sind bereit!")
        
        # Aktiviere entsprechende Checkboxes
        for kategorie in st.session_state.algorithm_recommendations:
            if kategorie in KATEGORIE_MAPPING:
                checkbox_name = KATEGORIE_MAPPING[kategorie]
                st.session_state[checkbox_name] = True
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗺️ Zur Karte", type="primary", use_container_width=True):
                st.session_state.show_map = True
                st.rerun()
        with col2:
            if st.button("🔄 Neue Empfehlung", type="secondary", use_container_width=True):
                # Reset algorithm
                st.session_state.algorithm_step = 0
                st.session_state.algorithm_data = {}
                st.session_state.algorithm_completed = False
                # Reset alle checkboxes
                for key in st.session_state.keys():
                    if key.startswith('show_'):
                        st.session_state[key] = False
                st.rerun()

def show_map_interface():
    """
    Zeigt die Karten-Interface mit Sidebar
    """
    # ---- Setup ----
    st.set_page_config(layout="wide")
    st.title("🗺️ Münster Map - Deine Empfehlungen")
    
    # Button für neue Empfehlung oben
    if st.button("🔄 Neue Empfehlung starten", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


    #Base map
    if "map_view" not in st.session_state:
        st.session_state.map_view = {"center": [51.96, 7.62], "zoom": 12.5}

    center = st.session_state.map_view["center"]
    zoom   = st.session_state.map_view["zoom"]

    muenster = folium.Map(location=center, zoom_start=zoom)

    # Add Location Control
    LocateControl(auto_start=False).add_to(muenster)

    # ---- Sidebar ----
    st.sidebar.header("Kategorien auswählen")
    st.sidebar.markdown("*Empfohlene Kategorien sind bereits aktiviert*")
    
    # Initialize all checkbox states if not exist
    checkbox_defaults = {
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
    
    for key, default in checkbox_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # Checkboxes 
    show_museen = st.sidebar.checkbox("Museen",  key="show_museen")
    show_buechereien = st.sidebar.checkbox("Büchereien",  key="show_buechereien")
    show_sport_drinnen = st.sidebar.checkbox("Sportstätten drinnen",  key="show_sport_drinnen")
    show_sport_draussen = st.sidebar.checkbox("Sportstätten draußen",  key="show_sport_draussen")
    show_tischtennis = st.sidebar.checkbox("Tischtennisplatten",  key="show_tischtennis")
    show_wickelplaetze = st.sidebar.checkbox("Wickelplätze",  key="show_wickelplaetze")
    show_giveboxen = st.sidebar.checkbox("Give Boxen",  key="show_giveboxen")
    show_kinos = st.sidebar.checkbox("Kinos",  key="show_kinos")
    show_kinder = st.sidebar.checkbox("Spielplätze",  key="show_kinder")
    show_friedhof = st.sidebar.checkbox("Friedhöfe",  key="show_friedhof")
    show_refill = st.sidebar.checkbox("Refillstationen", key="show_refill")
    show_restaurants = st.sidebar.checkbox("Restaurants", key="show_restaurants")
    show_cafes = st.sidebar.checkbox("Cafés", key="show_cafes")
    show_bars = st.sidebar.checkbox("Bars",key="show_bars")
    show_toiletten = st.sidebar.checkbox("Toiletten", key="show_toiletten")
    show_baeder = st.sidebar.checkbox("Bäder",  key="show_baeder")
    show_sauna = st.sidebar.checkbox("Saunen",  key="show_sauna")
    show_theater = st.sidebar.checkbox("Theater",  key="show_theater")
    show_gruen = st.sidebar.checkbox("Grünflächen",  key="show_gruen")
    
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
    # Geolocation 
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

# ---- Main App Logic ----
def main():
    """
    Hauptfunktion der App
    """
    # Initialize session state
    if 'algorithm_completed' not in st.session_state:
        st.session_state.algorithm_completed = False
    if 'show_map' not in st.session_state:
        st.session_state.show_map = False
    
    # App Logic
    if not st.session_state.algorithm_completed or not st.session_state.show_map:
        # Zeige Algorithmus
        run_algorithm()
    else:
        # Zeige Karte
        show_map_interface()

if __name__ == "__main__":
    main()