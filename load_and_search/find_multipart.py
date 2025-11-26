import xml.etree.ElementTree as ET

ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

def find_multipart_name(file_path):
    context = ET.iterparse(file_path, events=('end',))
    for event, elem in context:
        if elem.tag == f"{{{ns['ns']}}}DocumentedName":
            parts = elem.findall(".//ns:DocumentedNamePart", ns)
            if len(parts) > 1:
                print(f"Found multipart name in ID: {elem.attrib.get('FixedRef')}")
                full_name = []
                for part in parts:
                    val = part.find(".//ns:NamePartValue", ns)
                    if val is not None:
                        full_name.append(val.text)
                print(f"Parts: {full_name}")
                return # Stop after finding one
            elem.clear()

if __name__ == "__main__":
    find_multipart_name('docs/sdn_advanced.xml')
