"""
Empfehlungsalgorithmus für Orte und Aktivitäten
Hybrid-Ansatz: Entscheidungsbaum + Scoring + Modifier
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

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
        self.min_score = 4  # Mindest-Score für Empfehlungen
        self.fallback_score = 3  # Fallback wenn zu wenig Empfehlungen
        self.min_empfehlungen = 3  # Mindestanzahl Empfehlungen
        
        # Sport-Kategorien
        self.INDOOR_SPORTS = [
            'krafträume', 'dreifachhalle', 'einfachhallen', 'gymnastikräume',
            'zweifachhalle', 'gymnastikraum'
        ]
        
        self.OUTDOOR_SPORTS = [
            'skateanlage', 'skateanlagen', 'speckbrettanlage', 'speckbrettanlagen',
            'beachvolleyballanlage', 'beachvolleyballanlagen', 'trimmanlage', 
            'trimmanlagen', 'bouleanlage', 'bouleanlagen'
        ]
        
        # Scoring-Matrix: Kategorie -> {stimmung/sozial: punkte}
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
        
        # Modifier-Kategorien (immer hinzugefügt)
        self.immer_dabei = ['refill_stationen', 'toiletten']
        
        # Kinder-spezifische Kategorien
        self.kinder_kategorien = {
            'beide': ['still_wickelplätze'],
            'draussen': ['spielplätze']  # Wird nur draußen hinzugefügt wenn nicht schon da
        }
        
        # Gastronomie-Kategorien (Bars entfernt aus Hauptalgorithmus)
        self.gastronomie_kategorien = ['restaurants', 'cafés']

    def empfehlung_generieren(self, 
                            ort: Ort, 
                            stimmung: Stimmung, 
                            sozial: Sozial, 
                            kinder: bool = False, 
                            gastronomie: bool = False,
                            debug: bool = False) -> Tuple[List[str], List[Empfehlung]]:
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

    def interaktive_abfrage(self) -> Tuple[List[str], List[Empfehlung]]:
        """
        Interaktive Benutzerabfrage für alle Parameter
        """
        print("🏛️  Empfehlungsalgorithmus für Orte und Aktivitäten")
        print("=" * 50)
        
        # Frage 1: Ort
        print("\n1️⃣  Möchtest du drinnen oder draußen etwas machen?")
        print("   (1) Drinnen")
        print("   (2) Draußen")
        
        while True:
            try:
                ort_wahl = int(input("👉 Deine Wahl (1 oder 2): "))
                if ort_wahl == 1:
                    ort = Ort.DRINNEN
                    break
                elif ort_wahl == 2:
                    ort = Ort.DRAUSSEN
                    break
                else:
                    print("❌ Bitte 1 oder 2 eingeben!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")
        
        # Frage 2: Stimmung
        print(f"\n2️⃣  Wie ist deine Stimmung heute?")
        print("   (1) Aktiv - Ich will mich bewegen!")
        print("   (2) Entspannt - Ich möchte zur Ruhe kommen")
        print("   (3) Kulturell - Ich will etwas lernen/erleben")
        
        while True:
            try:
                stimmungs_wahl = int(input("👉 Deine Wahl (1, 2 oder 3): "))
                if stimmungs_wahl == 1:
                    stimmung = Stimmung.AKTIV
                    break
                elif stimmungs_wahl == 2:
                    stimmung = Stimmung.ENTSPANNT
                    break
                elif stimmungs_wahl == 3:
                    stimmung = Stimmung.KULTURELL
                    break
                else:
                    print("❌ Bitte 1, 2 oder 3 eingeben!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")
        
        # Frage 3: Sozial
        print(f"\n3️⃣  Suchst du eher Ruhe oder Gesellschaft?")
        print("   (1) Ruhe - Ich möchte für mich sein")
        print("   (2) Gesellschaft - Ich möchte andere Menschen treffen")
        
        while True:
            try:
                sozial_wahl = int(input("👉 Deine Wahl (1 oder 2): "))
                if sozial_wahl == 1:
                    sozial = Sozial.RUHE
                    break
                elif sozial_wahl == 2:
                    sozial = Sozial.GESELLSCHAFT
                    break
                else:
                    print("❌ Bitte 1 oder 2 eingeben!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")
        
        print("\n" + "="*30 + " MODIFIER " + "="*30)
        
        # Modifier 1: Kinder
        print(f"\n🧒 Hast du Kinder dabei?")
        kinder_input = input("👉 (j/n): ").lower().strip()
        kinder = kinder_input.startswith('j')
        
        # Modifier 2: Gastronomie
        print(f"\n🍽️  Möchtest du gerne etwas essen oder trinken?")
        gastronomie_input = input("👉 (j/n): ").lower().strip()
        gastronomie = gastronomie_input.startswith('j')
        
        # Empfehlung generieren
        print(f"\n🤔 Lass mich überlegen...")
        empfehlungen, debug_info = self.empfehlung_generieren(
            ort=ort, 
            stimmung=stimmung, 
            sozial=sozial, 
            kinder=kinder, 
            gastronomie=gastronomie,
            debug=True
        )
        
        return empfehlungen, debug_info

    def schnelles_ergebnis(self) -> bool:
        """
        Schnelles Ergebnis mit vordefinierten Kategorien
        Returns: True wenn zurück zum Hauptmenü, False wenn beenden
        """
        print("\n⚡ SCHNELLES ERGEBNIS")
        print("=" * 50)
        print("Was brauchst du gerade?")
        print("   (1) Dringend!")
        print("   (2) Kulinarik - Ich möchte etwas essen oder trinken")
        
        while True:
            try:
                wahl = int(input("👉 Deine Wahl (1 oder 2): "))
                if wahl == 1:
                    return self._dringend_ergebnis()
                elif wahl == 2:
                    return self._kulinarik_ergebnis()
                else:
                    print("❌ Bitte 1 oder 2 eingeben!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")

    def _dringend_ergebnis(self) -> bool:
        """
        Zeigt dringende Services an
        """
        print("\n🚨 DRINGENDE HILFE")
        print("=" * 30)
        
        dringende_services = ['refill_stationen', 'toiletten', 'still_wickelplätze']
        
        print("📍 SOFORT VERFÜGBAR:")
        for i, service in enumerate(dringende_services, 1):
            print(f"   {i}. {service.replace('_', ' ').title()}")
        
        return self._frage_zurueck_hauptmenu()

    def _kulinarik_ergebnis(self) -> bool:
        """
        Kulinarische Optionen anzeigen
        """
        print("\n🍽️ KULINARIK")
        print("=" * 30)
        print("Wonach ist dir?")
        print("   (1) Café - Kaffee, Kuchen, leichte Snacks")
        print("   (2) Restaurant - Vollwertige Mahlzeiten")
        print("   (3) Bar - Getränke und Cocktails")
        
        kulinarik_optionen = {
            1: ('cafés', '☕ CAFÉ-EMPFEHLUNG'),
            2: ('restaurants', '🍽️ RESTAURANT-EMPFEHLUNG'),
            3: ('bars', '🍸 BAR-EMPFEHLUNG')
        }
        
        while True:
            try:
                wahl = int(input("👉 Deine Wahl (1, 2 oder 3): "))
                if wahl in kulinarik_optionen:
                    kategorie, titel = kulinarik_optionen[wahl]
                    
                    print(f"\n{titel}")
                    print("=" * len(titel))
                    print(f"📍 EMPFEHLUNG:")
                    print(f"   • {kategorie.replace('_', ' ').title()}")
                    
                    return self._frage_zurueck_hauptmenu()
                else:
                    print("❌ Bitte 1, 2 oder 3 eingeben!")
            except ValueError:
                print("❌ Bitte eine Zahl eingeben!")

    def empfehlungen_anzeigen(self, empfehlungen: List[str], debug_info: List[Empfehlung] = None):
        """
        Zeigt die finalen Empfehlungen schön formatiert an
        """
        print("\n" + "🎯" + "="*20 + " DEINE EMPFEHLUNGEN " + "="*20 + "🎯")
        
        # Kategorisiere Empfehlungen für bessere Darstellung
        haupt_empfehlungen = []
        sport_empfehlungen = []
        modifier_empfehlungen = []
        
        modifier_kategorien = self.immer_dabei + self.kinder_kategorien['beide'] + \
                             self.kinder_kategorien['draussen'] + self.gastronomie_kategorien
        
        for emp in empfehlungen:
            if emp in modifier_kategorien:
                modifier_empfehlungen.append(emp)
            elif emp in self.INDOOR_SPORTS or emp in self.OUTDOOR_SPORTS:
                sport_empfehlungen.append(emp)
            else:
                haupt_empfehlungen.append(emp)
        
        # Hauptempfehlungen
        if haupt_empfehlungen:
            print(f"\n📍 HAUPTEMPFEHLUNGEN:")
            for i, kategorie in enumerate(haupt_empfehlungen, 1):
                print(f"   {i}. {kategorie.replace('_', ' ').title()}")
        
        # Sport-Empfehlungen
        if sport_empfehlungen:
            print(f"\n🏃 SPORT-EMPFEHLUNGEN:")
            for kategorie in sport_empfehlungen:
                print(f"   • {kategorie.replace('_', ' ').title()}")
        
        # Zusätzliche Services
        if modifier_empfehlungen:
            print(f"\n🔧 ZUSÄTZLICHE SERVICES:")
            for kategorie in modifier_empfehlungen:
                print(f"   • {kategorie.replace('_', ' ').title()}")
        
        print(f"\n📊 GESAMT: {len(empfehlungen)} Empfehlungen")
        
        # Debug-Info wenn verfügbar
        if debug_info:
            print(f"\n🔍 DEBUG-INFO (alle bewerteten Kategorien):")
            for emp in sorted(debug_info, key=lambda x: x.score, reverse=True):
                status = "✅" if emp.score >= 4 else "❌"
                print(f"   {status} {emp.kategorie.replace('_', ' ').title()}: {emp.score} Punkte ({emp.grund})")

def main():
    """
    Hauptfunktion mit neuem Menü-System
    """
    algorithmus = EmpfehlungsAlgorithmus()
    
    while True:
        try:
            print("\n🏛️  Empfehlungsalgorithmus für Orte und Aktivitäten")
            print("=" * 60)
            print("Wie kann ich dir helfen?")
            print("   (1) Probier mich aus! - Personalisierte Empfehlungen")
            print("   (2) Schnelles Ergebnis - Vordefinierte Optionen")
            
            hauptwahl = int(input("👉 Deine Wahl (1 oder 2): "))
            
            if hauptwahl == 1:
                # Interaktive Abfrage (bestehender Algorithmus)
                empfehlungen, debug_info = algorithmus.interaktive_abfrage()
                algorithmus.empfehlungen_anzeigen(empfehlungen, debug_info)
                
                # Nochmal?
                print(f"\n{'='*60}")
                nochmal = input("🔄 Möchtest du eine weitere Empfehlung? (j/n): ").lower().strip()
                if not nochmal.startswith('j'):
                    break
                    
            elif hauptwahl == 2:
                # Schnelles Ergebnis
                zurueck_hauptmenu = algorithmus.schnelles_ergebnis()
                if not zurueck_hauptmenu:
                    break
                    
            else:
                print("❌ Bitte 1 oder 2 eingeben!")
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Auf Wiedersehen!")
            break
        except ValueError:
            print("❌ Bitte eine Zahl eingeben!")
        except Exception as e:
            print(f"\n❌ Ein Fehler ist aufgetreten: {e}")
            print("Versuche es bitte nochmal!")

if __name__ == "__main__":
    main()
