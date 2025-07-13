import pandas as pd
import re
def format_opening_hours(hours_str):
    if not hours_str or pd.isna(hours_str):
        return "No opening hours available"
    
    try:
        # Handle special German characters and irregular opening hours
        hours_str = hours_str.replace('geschlossen', 'Closed')
        hours_str = hours_str.replace('unregelmäßig', 'Irregular hours')
        hours_str = hours_str.replace('jeden', 'every')
        hours_str = hours_str.replace('vom', 'from')
        hours_str = hours_str.replace('bis', 'to')
        hours_str = hours_str.replace('?', 'No opening hours available')
        hours_str = hours_str.replace('off', 'close')
        hours_str = hours_str.replace('24/7', 'always open')
        
        # Create mapping for German day abbreviations
        
        day_mapping = {
            'Montag':'Mon', 'Dienstag':'Tue', 'Mittwoch':'Wed','Donnerstag':'Thu',
            'Freitag':'Fri','Samstag':'Sat', 'Sonntag':'Sun',
            'Mo': 'Mon', 'Di': 'Tue', 'Mi': 'Wed', 'Do': 'Thu', 
            'Fr': 'Fri', 'Sa': 'Sat', 'So': 'Sun'
        }
        # First process full day names (longer strings first)
        for de_day, en_day in sorted(day_mapping.items(), key=lambda x: -len(x[0])):
        # Use word boundaries to match whole words only
            hours_str = re.sub(r'\b' + re.escape(de_day) + r'\b', en_day, hours_str, flags=re.IGNORECASE)
        
        # Process day names using regex for whole word matches, case-insensitive
        # Sort by length in descending order to match longer strings first
        for de_day, en_day in sorted(day_mapping.items(), key=lambda x: -len(x[0])):
            hours_str = re.sub(r'\b' + re.escape(de_day) + r'\b', en_day, hours_str, flags=re.IGNORECASE)

        # Fix common typos
        hours_str = hours_str.replace('Sunnntag', 'Sun')
        hours_str = hours_str.replace('Sonnntag', 'Sun')
        
        # Handle special case where "geschlossen" appears
        if 'Closed' in hours_str:
            # Split by Closed and add colon if missing
            parts = hours_str.split('Closed', 1)
            if len(parts) > 1 and not parts[0].strip().endswith(':'):
                hours_str = f"{parts[0].strip()}: Closed{parts[1]}"
        
        # Remove PH (public holidays) from the string
        cleaned_str = hours_str.replace('PH,', '').replace(',PH', '').replace('PH', '')
        
        # Split into day groups
        day_groups = [g.strip() for g in cleaned_str.split(';') if g.strip()]
        formatted_groups = []
        processed_days = set()  # Track processed days to avoid duplicates
        
        for group in day_groups:
            if not group:
                continue
                
            # Check for closed status
            if 'Closed' in group:
                day_part = group.split('Closed', 1)[0].strip()
                if day_part and day_part not in processed_days:
                    formatted_groups.append(f"{day_part}: Closed")
                    processed_days.add(day_part)
                continue
                
            # Check for irregular hours
            if 'Irregular hours' in group:
                formatted_groups.append("Irregular opening hours")
                continue
                
            # Split into days and times
            if ' ' in group and ':' in group:
                # Split at the last space before times start
                last_space = group.rfind(' ')
                days_part = group[:last_space].strip()
                times_part = group[last_space:].strip()
            elif ':' in group:
                days_part, times_part = group.split(':', 1)
                days_part = days_part.strip()
                times_part = times_part.strip()
            else:
                days_part = group
                times_part = ''

            #Debug
            print(f"Before cleanup - days_part: '{days_part}' | times_part: '{times_part}'")  

            # Clean up and format the times
            if times_part and 'Closed' not in times_part:
                # Remove extra spaces in times
                times_part = times_part.replace(' :', ':').replace(': ', ':')
                # Handle multiple time ranges
                time_ranges = [t.strip() for t in times_part.split(',') if t.strip()]
                times = ', '.join(time_ranges)
                if days_part not in processed_days:
                    formatted_groups.append(f"{days_part}: {times}")
                    processed_days.add(days_part)
            elif not times_part:
                if days_part not in processed_days:
                    formatted_groups.append(days_part)
                    processed_days.add(days_part)

        if not formatted_groups:
            return "No opening hours available"
        
        # Remove duplicate colons
        cleaned_groups = []
        for group in formatted_groups:
            # Remove duplicate colons
            while '::' in group:
                group = group.replace('::', ':')
            cleaned_groups.append(group)
        
        # Join with <br> and remove duplicates
        return '<br>'.join(cleaned_groups)

    except Exception as e:
        print(f"Error formatting opening hours: {e}")
        # Return original but with PH removed and cleaned up
        cleaned = hours_str.replace('PH', '').replace(' ,', ',').replace(',,', ',').strip(' ,;')
        return cleaned if cleaned else "No opening hours available"

    return '<br>'.join(formatted_groups)