import re

def split_opening_groups(hours_str):
    # Splitte an Semikolon ODER an Komma, WENN danach ein Tag kommt (für mehr Flexibilität)
    parts = re.split(r";|\s*,\s*(?=[A-Za-z]{2,3}\b)", hours_str)
    result = [part.strip().strip(';') for part in parts if part.strip()]
    return result

def expand_days(day_str):
    tage_reihenfolge = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    tage_map = {tag: i for i, tag in enumerate(tage_reihenfolge)}
    # Feiertage vorher entfernen!
    day_str = re.sub(r'\b(PH|FT|Feiertag|Feiertags)\b,?', '', day_str, flags=re.IGNORECASE)
    day_str = day_str.strip(", ")
    result = []
    parts = [d for d in day_str.replace(' ', '').split(',') if d]
    for part in parts:
        if '-' in part:
            segs = part.split('-')
            if len(segs) >= 2:
                start, end = segs[0], segs[-1]
                if start in tage_map and end in tage_map:
                    idx_start = tage_map[start]
                    idx_end = tage_map[end]
                    if idx_end >= idx_start:
                        result.extend(tage_reihenfolge[idx_start:idx_end+1])
                    else:
                        result.extend(tage_reihenfolge[idx_start:] + tage_reihenfolge[:idx_end+1])
        elif part in tage_map:
            result.append(part)
    return result

def format_opening_hours(hours_str):
    # 24/7 ersetzen
    if re.fullmatch(r'\s*24/7\s*', hours_str):
        hours_str = 'Mo-Su 00:00-24:00'
    else:
        hours_str = re.sub(r'24/7', '00:00-24:00', hours_str)
    # Spezialfälle und Fehler
    hours_str = hours_str.replace('closed', 'geschlossen').replace('off', 'geschlossen')
    hours_str = hours_str.replace('irregular hours', 'Unregelmäßige Öffnungszeiten')
    hours_str = hours_str.replace('every', 'jeden').replace('?', 'Keine Öffnungszeiten verfügbar')
    # Mappings für Tagesnamen
    day_mapping = {
        'montag':'Mo', 'dienstag':'Di', 'mittwoch':'Mi','donnerstag':'Do',
        'freitag':'Fr','samstag':'Sa', 'sonntag':'So',
        'monday':'Mo','tuesday':'Di','wednesday':'Mi','thursday':'Do',
        'friday':'Fr','saturday':'Sa','sunday':'So',
        'mo': 'Mo', 'di': 'Di', 'mi': 'Mi', 'do': 'Do',
        'fr': 'Fr', 'sa': 'Sa', 'so': 'So',
        'mon': 'Mo', 'die': 'Di', 'mit': 'Mi', 'don': 'Do',
        'fre': 'Fr', 'sam': 'Sa', 'son': 'So',
        'tu': 'Di', 'tue': 'Di', 'tues': 'Di',
        'th': 'Do', 'thu': 'Do', 'thur': 'Do', 'thurs': 'Do',
        'we': 'Mi', 'su': 'So',
    }
    for de_day, abbr in sorted(day_mapping.items(), key=lambda x: -len(x[0])):
        hours_str = re.sub(r'\b' + re.escape(de_day) + r'\b', abbr, hours_str, flags=re.IGNORECASE)

    day_groups = split_opening_groups(hours_str)
    tage_reihenfolge = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    tage_zeiten = {tag: None for tag in tage_reihenfolge}

    for group in day_groups:
        m = re.match(r'([A-Za-z ,\-]+)\s+([0-9]{1,2}:[0-9]{2}-[0-9]{1,2}:[0-9]{2}(?:,[0-9]{1,2}:[0-9]{2}-[0-9]{1,2}:[0-9]{2})*)', group)
        if m:
            days_part = m.group(1).strip(" :")
            times_part = m.group(2).strip()
            tage_liste = expand_days(days_part)
            for tag in tage_liste:
                tage_zeiten[tag] = times_part

    lines = []
    for tag in tage_reihenfolge:
        if tage_zeiten[tag]:
            lines.append(f"{tag}: {tage_zeiten[tag]}")
    return "<br>".join(lines) if lines else "Keine Öffnungszeiten verfügbar"
