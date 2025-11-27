import xml.etree.ElementTree as ET
import json
import sys
from normalization_logic import normalize_name

# Namespace map
ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

def parse_and_convert(input_file, output_file):
    print(f"Parsing {input_file}...")
    
    # In-memory lookups
    country_map = {}      # ID -> Name
    location_map = {}     # LocationID -> {address, city, country...}
    profile_programs = {} # ProfileID -> set(programs)
    
    # Pass 1: Reference Values (Countries)
    print("Pass 1: Loading Country Codes...")
    context = ET.iterparse(input_file, events=('end',))
    for event, elem in context:
        if elem.tag == f"{{{ns['ns']}}}Country":
            c_id = elem.attrib.get('ID')
            if c_id:
                country_map[c_id] = elem.text.strip() if elem.text else None
        elif elem.tag == f"{{{ns['ns']}}}ReferenceValueSets":
            elem.clear()
            break # Done with references
    del context

    # Pass 2: Locations
    print("Pass 2: Loading Locations...")
    context = ET.iterparse(input_file, events=('end',))
    for event, elem in context:
        if elem.tag == f"{{{ns['ns']}}}Location":
            loc_id = elem.attrib.get('ID')
            
            loc_data = {
                'address_lines': [],
                'city': None,
                'state': None,
                'postal_code': None,
                'country': None
            }
            
            # Country
            loc_country = elem.find("ns:LocationCountry", ns)
            if loc_country is not None:
                c_id = loc_country.attrib.get('CountryID')
                loc_data['country'] = country_map.get(c_id)
            
            # Parts
            for part in elem.findall("ns:LocationPart", ns):
                type_id = part.attrib.get('LocPartTypeID')
                val_elem = part.find("ns:LocationPartValue", ns)
                val = val_elem.text.strip() if val_elem is not None and val_elem.text else None
                
                if val:
                    if type_id in ['1451', '1452', '1453']: # Address 1, 2, 3
                        loc_data['address_lines'].append(val)
                    elif type_id == '1454': # City
                        loc_data['city'] = val
                    elif type_id == '1455': # State
                        loc_data['state'] = val
                    elif type_id == '1456': # Postal Code
                        loc_data['postal_code'] = val
            
            # Flatten address lines
            final_loc = {
                'address_line': ", ".join(loc_data['address_lines']) if loc_data['address_lines'] else None,
                'city': loc_data['city'],
                'state': loc_data['state'],
                'postal_code': loc_data['postal_code'],
                'country': loc_data['country']
            }
            
            location_map[loc_id] = final_loc
            elem.clear()
            
        elif elem.tag == f"{{{ns['ns']}}}Locations":
            # End of Locations block
            elem.clear()
            break
    del context

    # Pass 3: Sanctions Entries (Programs)
    # Note: SanctionsEntries usually come AFTER DistinctParty, so we might need to read the whole file
    # or rely on the fact that we are doing a full pass now.
    # Wait, if SanctionsEntries are at the end, we need to parse them BEFORE DistinctParty if we want to write in one go?
    # OR we collect them all now in a quick pass.
    
    print("Pass 3: Loading Sanctions Programs...")
    context = ET.iterparse(input_file, events=('end',))
    sanctions_found = False
    for event, elem in context:
        if elem.tag == f"{{{ns['ns']}}}SanctionsEntry":
            sanctions_found = True
            profile_id = elem.attrib.get('ProfileID')
            
            # Extract program from SanctionsMeasure
            for measure in elem.findall("ns:SanctionsMeasure", ns):
                comment = measure.find("ns:Comment", ns)
                if comment is not None and comment.text:
                    if profile_id not in profile_programs:
                        profile_programs[profile_id] = set()
                    profile_programs[profile_id].add(comment.text.strip())
            
            elem.clear()
    del context
    
    if not sanctions_found:
        print("Warning: No SanctionsEntries found in Pass 3.")

    # Pass 4: Distinct Parties (Main Output)
    print("Pass 4: Processing Entities and Writing Output...")
    with open(output_file, 'w', encoding='utf-8') as f_out:
        context = ET.iterparse(input_file, events=('end',))
        count = 0
        
        for event, elem in context:
            if elem.tag == f"{{{ns['ns']}}}DistinctParty":
                entity_id = elem.attrib.get('FixedRef')
                profile = elem.find("ns:Profile", ns)
                
                if profile is not None:
                    profile_id = profile.attrib.get('ID')
                    party_sub_type_id = profile.attrib.get('PartySubTypeID')
                    
                    # Determine Type
                    entity_type = "Unknown"
                    if party_sub_type_id == '1': entity_type = "Vessel"
                    elif party_sub_type_id == '2': entity_type = "Aircraft"
                    elif party_sub_type_id == '3': entity_type = "Entity"
                    elif party_sub_type_id == '4': entity_type = "Individual"

                    # Get Programs
                    programs = list(profile_programs.get(profile_id, []))
                    
                    # Get Names
                    aliases = []
                    identity = profile.find("ns:Identity", ns) # Usually Identity is inside Profile
                    if identity is not None:
                         for alias in identity.findall(".//ns:Alias", ns):
                            is_primary = alias.attrib.get('Primary') == 'true'
                            
                            full_name_parts = []
                            doc_name = alias.find(".//ns:DocumentedName", ns)
                            if doc_name is not None:
                                for part in doc_name.findall(".//ns:DocumentedNamePart", ns):
                                    val = part.find(".//ns:NamePartValue", ns)
                                    if val is not None and val.text:
                                        full_name_parts.append(val.text.strip())
                            
                            full_name = " ".join(full_name_parts)
                            if full_name:
                                aliases.append({
                                    'full_name': full_name,
                                    'normalized_name': normalize_name(full_name),
                                    'is_primary': is_primary,
                                    'type_id': alias.attrib.get('AliasTypeID')
                                })

                    # Get Addresses (Locations)
                    entity_addresses = []
                    for feature in profile.findall("ns:Feature", ns):
                        if feature.attrib.get('FeatureTypeID') == '25': # Location Feature
                            ver_loc = feature.find(".//ns:VersionLocation", ns)
                            if ver_loc is not None:
                                loc_id = ver_loc.attrib.get('LocationID')
                                if loc_id in location_map:
                                    entity_addresses.append(location_map[loc_id])
                    
                    # Remarks/Comment
                    comment_elem = elem.find("ns:Comment", ns)
                    remarks = comment_elem.text.strip() if comment_elem is not None and comment_elem.text else None

                    record = {
                        'entity_id': int(entity_id) if entity_id else None,
                        'names': aliases,
                        'type': entity_type,
                        'programs': programs,
                        'addresses': entity_addresses,
                        'remarks': remarks
                    }
                    
                    f_out.write(json.dumps(record) + '\n')
                    count += 1
                
                elem.clear()
                # Clear root refs occasionally
                if count % 1000 == 0:
                     pass

    print(f"Finished. Processed {count} entities. Output saved to {output_file}")

if __name__ == "__main__":
    input_path = 'docs/sdn_advanced.xml'
    output_path = 'sdn_entities.jsonl'
    parse_and_convert(input_path, output_path)