import json

# Read the original file
with open('raw_data_geojson/sportstaetten.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update the properties in each feature
for feature in data['features']:
    properties = feature['properties']
    # Check if Produkt exists and rename it to Name
    if 'Produkt' in properties:
        properties['Name'] = properties.pop('Produkt')
    # Also check if 'name' exists (lowercase) and rename it to 'Name' (uppercase)
    if 'name' in properties:
        properties['Name'] = properties.pop('name')

# Write the updated data back to the file
with open('raw_data_geojson/sportstaetten.geojson', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
