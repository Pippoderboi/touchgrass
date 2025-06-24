import json

# Read the original file
with open('raw_data_geojson/sportstaetten.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update the properties in each feature
for feature in data['features']:
    properties = feature['properties']
    if 'Produkt' in properties:
        # Rename Produkt to Name if it exists
        properties['Name'] = properties.pop('Produkt')

# Write the updated data back to the file
with open('raw_data_geojson/sportstaetten.geojson', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
