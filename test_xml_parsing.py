import xml.etree.ElementTree as ET
import json

ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

def _parse_countries(xml_root):
    country_map = {}
    for country_elem in xml_root.findall(".//ns:Country", ns):
        c_id = country_elem.attrib.get("ID")
        iso2 = country_elem.attrib.get("ISO2")
        name = country_elem.text.strip() if country_elem.text else None
        if c_id:
            country_map[c_id] = {"name": name, "iso2": iso2}
    return country_map

def _parse_locations(xml_root, country_map):
    location_map = {}
    for loc_elem in xml_root.findall(".//ns:Location", ns):
        loc_id = loc_elem.attrib.get("ID")
        loc_data = {
            "address_line": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": None,
            "country_iso2": None,
        }

        # Country
        loc_country = loc_elem.find("ns:LocationCountry", ns)
        if loc_country is not None:
            c_id = loc_country.attrib.get("CountryID")
            c_data = country_map.get(c_id)
            if c_data:
                loc_data["country"] = c_data.get("name")
                loc_data["country_iso2"] = c_data.get("iso2")

        # Parts
        address_lines = []
        for part in loc_elem.findall("ns:LocationPart", ns):
            type_id = part.attrib.get("LocPartTypeID")
            loc_part_value = part.find("ns:LocationPartValue", ns)
            val_elem = loc_part_value.find("ns:Value", ns) if loc_part_value is not None else None
            val = val_elem.text.strip() if val_elem is not None and val_elem.text else None

            if val:
                if type_id in ["1451", "1452", "1453"]:
                    address_lines.append(val)
                elif type_id == "1454":
                    loc_data["city"] = val
                elif type_id == "1455":
                    loc_data["state"] = val
                elif type_id == "1456":
                    loc_data["postal_code"] = val

        loc_data["address_line"] = ", ".join(address_lines) if address_lines else None
        location_map[loc_id] = loc_data
    return location_map

# Load XML
print("Loading XML...")
tree = ET.parse('sdn_advanced.xml')
root = tree.getroot()

countries = _parse_countries(root)
print(f"Parsed {len(countries)} countries.")
# Print a few
for cid in list(countries.keys())[:5]:
    print(f"  ID {cid}: {countries[cid]}")

locations = _parse_locations(root, countries)
print(f"Parsed {len(locations)} locations.")
# Print a few with data
count = 0
for lid in locations:
    if locations[lid]['country']:
        print(f"  Location {lid}: {locations[lid]}")
        count += 1
    if count >= 5:
        break
