import xml.etree.ElementTree as ET


def get_metadata_list_xml(file_path):
    """Extract columns from a CSV file.
    Parameters
    ----------
    filename : str
        Name of the XMl file containing the data to extract. 
    
    Returns
    -------
    list of triplets
        Extracted metadata in a list of triplets format. 
    """
    avus = []
    mytree = ET.parse(file_path)
    myroot = mytree.getroot()
    for x in myroot.findall('avu'):
        attribute = x.find('attribute').text
        value = x.find('value').text
        unit_el = x.find('units')
        unit = unit_el.text if unit_el is not None else '' 
        avus.append([attribute, value, unit])
    
    return avus
