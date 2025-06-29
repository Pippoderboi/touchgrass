import json

# Read the original file
with open('raw_data_geojson/sportstaetten.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update the properties in each feature
for feature in data['features']:
    properties = feature['properties']
    # Rename Name to Kategorie
    if 'Name' in properties:
        properties['Kategorie'] = properties.pop('Name')
    # Rename Teilprodukt to Typ
    if 'Teilprodukt' in properties:
        properties['Typ'] = properties.pop('Teilprodukt')

# Write the updated data back to the file
with open('raw_data_geojson/sportstaetten.geojson', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
