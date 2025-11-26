import xml.etree.ElementTree as ET
import sys

ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

def parse_xml(file_path):
    try:
        # Register namespace to simplify output if possible, though ET.iterparse is tricky with this
        ET.register_namespace('', ns['ns'])
        
        events = ET.iterparse(file_path, events=('end',))
        for event, elem in events:
            # Check if the tag ends with DistinctParty (ignoring namespace for match if we want to be lazy, or fully qualified)
            if elem.tag == f"{{{ns['ns']}}}DistinctParty":
                fixed_ref = elem.attrib.get('FixedRef')
                print(f"Found Entity ID: {fixed_ref}")
                
                # Find aliases
                aliases = []
                for alias in elem.findall(".//ns:Alias", ns):
                    is_primary = alias.attrib.get('Primary') == 'true'
                    name_val = alias.find(".//ns:NamePartValue", ns)
                    if name_val is not None:
                        aliases.append({
                            'name': name_val.text,
                            'is_primary': is_primary
                        })
                
                print("Aliases:", aliases)
                
                # Clear element to save memory
                elem.clear()
                
                # specific stop after 1 for verification
                break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parse_xml('docs/sdn_advanced.xml')
