import pandas as pd
def format_opening_hours(hours_str):
    if not hours_str or pd.isna(hours_str):
        return "No opening hours available"
    
    try:
        # Remove PH (public holidays) from the string
        cleaned_str = hours_str.replace('PH,', '').replace(',PH', '').replace('PH', '')
        
        # Split into day groups
        day_groups = [g.strip() for g in cleaned_str.split(';') if g.strip()]
        formatted_groups = []
        
        for group in day_groups:
            if not group:
                continue
                
            # Check for "off" status first
            if 'off' in group.lower():
                day_part = group.split('off', 1)[0].strip()
                if day_part:
                    formatted_groups.append(f"{day_part}: Closed")
                continue
                
            # Split into days and times
            if ' ' in group:
                days_part, times_part = group.split(' ', 1)
                times_part = times_part.strip()
            else:
                days_part = group
                times_part = ''
            
            # Clean up days (remove any remaining PH and empty entries)
            days = []
            for day in days_part.split(','):
                day = day.strip()
                if day and day != 'PH':
                    days.append(day)
            
            if not days:
                continue
                
            # Format the days
            if len(days) == 2 and all(d in ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'] for d in days):
                day_range = f"{days[0]}-{days[1]}"
            else:
                day_range = ', '.join(days)
            
            # Clean up and format the times
            if times_part and 'off' not in times_part.lower():
                # Handle multiple time ranges
                time_ranges = [t.strip() for t in times_part.split(',') if t.strip()]
                times = ', '.join(time_ranges)
                formatted_groups.append(f"{day_range}: {times}")
            elif not times_part:
                formatted_groups.append(day_range)
        
        if not formatted_groups:
            return "No opening hours available"
            
        return '<br>'.join(formatted_groups)
    except Exception as e:
        print(f"Error formatting opening hours: {e}")
        # Return original but with PH removed and cleaned up
        cleaned = hours_str.replace('PH', '').replace(' ,', ',').replace(',,', ',').strip(' ,;')
        return cleaned if cleaned else "No opening hours available"