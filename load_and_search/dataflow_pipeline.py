import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, WorkerOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.transforms.combiners import Sample

import argparse
import xml.etree.ElementTree as ET
import json
import os
import re
import sys

# Namespace map - must be global or passed to DoFn
ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'}

from normalization_logic import normalize_name

# --- Helper functions for XML parsing, extracted from parse_to_jsonl.py ---
# These will run within the DoFn, so they need to be self-contained.


def _parse_countries(xml_root):
    # ... (existing code) ...
    country_map = {}
    for country_elem in xml_root.findall(".//ns:Country", ns):
        c_id = country_elem.attrib.get("ID")
        if c_id:
            country_map[c_id] = country_elem.text.strip() if country_elem.text else None
    return country_map

# ... (existing helper functions) ...

COUNTRY_NAME_TO_ISO_ALPHA2 = {
    "Cuba": "CU",
    "Panama": "PA",
    "Russia": "RU",
    "Afghanistan": "AF",
    "Iran": "IR",
    "United Kingdom": "GB",
    "Switzerland": "CH",
    "Spain": "ES",
    "Mexico": "MX",
    "Ukraine": "UA",
    # Add other countries as needed
}

class ConvertCountryCodeDoFn(beam.DoFn):
    def process(self, entity):
        new_addresses = []
        for addr in entity.get('addresses', []):
            country_name = addr.get('country')
            iso_code = COUNTRY_NAME_TO_ISO_ALPHA2.get(country_name, None)

            new_addr = addr.copy()
            if iso_code:
                new_addr['enriched_data'] = json.dumps({"iso_alpha_2_country_code": iso_code})
            else:
                new_addr['enriched_data'] = json.dumps({"error": "ISO code not found", "original_country": country_name})

            new_addresses.append(new_addr)

        entity['addresses'] = new_addresses
        yield entity

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
        }

        # Country
        loc_country = loc_elem.find("ns:LocationCountry", ns)
        if loc_country is not None:
            c_id = loc_country.attrib.get("CountryID")
            loc_data["country"] = country_map.get(c_id)

        # Parts
        address_lines = []
        for part in loc_elem.findall("ns:LocationPart", ns):
            type_id = part.attrib.get("LocPartTypeID")
            loc_part_value = part.find("ns:LocationPartValue", ns)
            
            # The actual value is inside a <Value> child element
            val_elem = loc_part_value.find("ns:Value", ns) if loc_part_value is not None else None
            val = (
                val_elem.text.strip()
                if val_elem is not None and val_elem.text
                else None
            )

            if val:
                if type_id in ["1451", "1452", "1453"]:  # Address 1, 2, 3
                    address_lines.append(val)
                elif type_id == "1454":  # City
                    loc_data["city"] = val
                elif type_id == "1455":  # State
                    loc_data["state"] = val
                elif type_id == "1456":  # Postal Code
                    loc_data["postal_code"] = val

        loc_data["address_line"] = ", ".join(address_lines) if address_lines else None
        location_map[loc_id] = loc_data
    return location_map


def _parse_sanctions_programs(xml_root):
    profile_programs = {}
    for sanctions_entry_elem in xml_root.findall(".//ns:SanctionsEntry", ns):
        profile_id = sanctions_entry_elem.attrib.get("ProfileID")
        if profile_id:
            # Extract program from SanctionsMeasure
            for measure in sanctions_entry_elem.findall("ns:SanctionsMeasure", ns):
                comment = measure.find("ns:Comment", ns)
                if comment is not None and comment.text:
                    if profile_id not in profile_programs:
                        profile_programs[profile_id] = (
                            set()
                        )  # Use set to avoid duplicates
                    profile_programs[profile_id].add(comment.text.strip())

    # Convert sets to lists for JSON serialization
    return {pid: list(programs) for pid, programs in profile_programs.items()}


class ParseSanctionsXmlDoFn(beam.DoFn):
    def process(self, element):
        # 'element' here is the entire XML content as a string
        xml_string = element
        root = ET.fromstring(xml_string.encode("utf-8"))

        # Pass 1: Reference Data (Countries)
        country_map = _parse_countries(root)

        # Pass 2: Locations
        location_map = _parse_locations(root, country_map)

        # Pass 3: Sanctions Entries (Programs)
        profile_programs = _parse_sanctions_programs(root)

        # Pass 4: Distinct Parties (Main Output)
        for elem in root.findall(".//ns:DistinctParty", ns):
            entity_id = elem.attrib.get('FixedRef')
            profile = elem.find("ns:Profile", ns)
            
            if profile is not None and entity_id:
                profile_id = profile.attrib.get('ID')
                party_sub_type_id = profile.attrib.get("PartySubTypeID")

                # Determine Type
                entity_type = "Unknown"
                if party_sub_type_id == "1":
                    entity_type = "Vessel"
                elif party_sub_type_id == "2":
                    entity_type = "Aircraft"
                elif party_sub_type_id == "3":
                    entity_type = "Entity"
                elif party_sub_type_id == "4":
                    entity_type = "Individual"

                # Get Programs
                programs = profile_programs.get(profile_id, [])

                # Get Names
                aliases = []
                identity = profile.find("ns:Identity", ns)
                if identity is not None:
                    for alias in identity.findall(".//ns:Alias", ns):
                        is_primary = alias.attrib.get("Primary") == "true"

                        full_name_parts = []
                        doc_name = alias.find(".//ns:DocumentedName", ns)
                        if doc_name is not None:
                            for part in doc_name.findall(
                                ".//ns:DocumentedNamePart", ns
                            ):
                                val = part.find(".//ns:NamePartValue", ns)
                                if val is not None and val.text:
                                    full_name_parts.append(val.text.strip())

                        full_name = " ".join(full_name_parts)
                        if full_name:
                            aliases.append(
                                {
                                    "full_name": full_name,
                                    "normalized_name": normalize_name(full_name),
                                    "is_primary": is_primary,
                                    "type_id": alias.attrib.get("AliasTypeID"),
                                }
                            )

                # Get Addresses (Locations)
                entity_addresses = []
                for feature in profile.findall("ns:Feature", ns):
                    if feature.attrib.get("FeatureTypeID") == "25":  # Location Feature
                        ver_loc = feature.find(".//ns:VersionLocation", ns)
                        if ver_loc is not None:
                            loc_id = ver_loc.attrib.get("LocationID")
                            if loc_id in location_map:
                                entity_addresses.append(location_map[loc_id])

                # Remarks/Comment
                comment_elem = elem.find("ns:Comment", ns)
                remarks = (
                    comment_elem.text.strip()
                    if comment_elem is not None and comment_elem.text
                    else None
                )

                record = {
                    'entity_id': int(entity_id),
                    'names': aliases,
                    'type': entity_type,
                    'programs': programs,
                    'addresses': entity_addresses,
                    'remarks': remarks,
                }
                yield record


class ReadFileContent(beam.DoFn):
    def process(self, file_path):
        from apache_beam.io.filesystems import FileSystems
        with FileSystems.open(file_path) as f:
            yield f.read().decode('utf-8')

def run(argv=None, save_main_session=True):
    parser = argparse.ArgumentParser()

    parser.add_argument(

        "--input_file",

        dest="input_file",

        required=True,

        help="Input XML file to process.",

    )

    parser.add_argument(

        "--output_table",

        dest="output_table",

        required=True,

        help="Output BigQuery table to write to, in the format PROJECT:DATASET.TABLE.",

    )

    parser.add_argument(

        "--runner",

        dest="runner",

        default="DirectRunner",

        help="Runner to use. E.g. DirectRunner, DataflowRunner.",

    )

    parser.add_argument(

        "--project", dest="project", required=True, help="GCP project id."

    )

    parser.add_argument(

        "--temp_location",

        dest="temp_location",

        required=True,

        help="GCS path for temporary files (e.g., gs://your-bucket/tmp).",  # Made required

    )



    args, pipeline_args = parser.parse_known_args(argv)



    pipeline_args.extend([

        "--sdk_container_image=asia-southeast1-docker.pkg.dev/agentspace-krozario/dataflow-templates/sanctions-pipeline:latest",

        "--sdk_location=container"

    ])



    pipeline_options = PipelineOptions(

        pipeline_args,

        runner=args.runner,

        project=args.project,

        temp_location=args.temp_location,

        region="asia-southeast1",  # Explicitly set region for DataflowRunner

    )



    with beam.Pipeline(options=pipeline_options) as p:

                # 1. No longer reading cache for Address Validation API

                # 2. Read XML

                # Read the entire file content as a single string to allow ElementTree parsing

                xml_content = (

                    p 

                    | "CreateInputPath" >> beam.Create([args.input_file])

                    | "ReadWholeXML" >> beam.ParDo(ReadFileContent())

                )

        

                # 3. Parse XML

                parsed_entities = xml_content | "ParseXML" >> beam.ParDo(

                    ParseSanctionsXmlDoFn()

                )

        

                # 4. Convert Country Codes (formerly Enrich Addresses)

                converted_entities = (

                    parsed_entities 

                    | 'ConvertCountryCodes' >> beam.ParDo(ConvertCountryCodeDoFn())

                )

                

                # No more new_cache_entries as we removed API calls

        

                        enriched_entities = converted_entities # Renamed for clarity

        

                

        

                        # 5. Write Converted Entities to Main Table

        

                        schema_path = os.path.join(os.path.dirname(__file__), '../queries/bq_schema.json')

        

                        with open(schema_path, "r") as f:

        

                            bigquery_schema = json.load(f)

        

                

        

                        enriched_entities | "WriteToBigQuery" >> WriteToBigQuery(

        

                            table=args.output_table,

        

                            schema={"fields": bigquery_schema},

        

                            write_disposition=beam.io.BigQueryDisposition.WRITE_TRUNCATE,

        

                            create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,

        

                        )

                

                # 6. No longer writing cache entries

        




if __name__ == "__main__":
    run()
