import xml.etree.ElementTree as ET
import io

xml_data = """<DistinctParty FixedRef="36">                                                                     
      <Comment />                                                                                     
      <Profile ID="36" PartySubTypeID="3">                                                            
        <Identity ID="4375" FixedRef="36" Primary="true" False="false">                               
          <Alias FixedRef="36" AliasTypeID="1400" Primary="false" LowQuality="false">                 
            <DocumentedName ID="13178" FixedRef="36" DocNameStatusID="2">                             
              <DocumentedNamePart>                                                                    
                <NamePartValue NamePartGroupID="19387" ScriptID="215" ScriptStatusID="1" Acronym="fals
e">AERO-CARIBBEAN</NamePartValue>                                                                     
              </DocumentedNamePart>                                                                   
            </DocumentedName>                                                                         
          </Alias>                                                                                    
          <Alias FixedRef="36" AliasTypeID="1403" Primary="true" LowQuality="false">                  
            <DocumentedName ID="4375" FixedRef="36" DocNameStatusID="1">                              
              <DocumentedNamePart>                                                                    
                <NamePartValue NamePartGroupID="6700" ScriptID="215" ScriptStatusID="1" Acronym="false
">AEROCARIBBEAN AIRLINES</NamePartValue>                                                              
              </DocumentedNamePart>                                                                   
            </DocumentedName>                                                                         
          </Alias>                                                                                    
        </Identity>                                                                                   
      </Profile>                                                                                      
    </DistinctParty>"""

root = ET.fromstring(xml_data)
ns = {'ns': 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML'} # I need to check the namespace from the file header

# The snippet didn't have the namespace declaration, but the file header did. 
# Header: xmlns="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"
# So tags are likely namespaced.

# Let's try parsing with namespace handling
for distinct_party in [root]:
    fixed_ref = distinct_party.attrib.get('FixedRef')
    print(f"ID: {fixed_ref}")
    for alias in distinct_party.findall(".//Alias"): # This might fail if namespace is required and I didn't include it in the snippet parsing, but in real file it is namespaced.
        # In this snippet, there is no xmlns defined on DistinctParty, so it has no namespace effectively unless inherited.
        # But in the real file, the root <Sanctions> has the default namespace.
        # So in the real file, "DistinctParty" is "{https://...}DistinctParty".
        pass
