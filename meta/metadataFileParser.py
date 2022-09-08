from meta.csv_parser import get_metadata_list_csv
from meta.xml_parser import get_metadata_list_xml

from pathlib import Path

type_mapper = {
    '.csv': {
        'func': get_metadata_list_csv,
        'description': 'CSV file containing triplets with a,v,u'
    },
    # 'json': {
    #     'func': get_metadata_list_from_json,
    #     'description': 'Json file containing '
    #     },
    '.xml': {
        'func': get_metadata_list_xml,
        'description': ''
    },
}


def parse(file_path):
    """Parses the metadata file specified by the file path against one of the known parsers based on the file 
    extension. In case a parser is not recognized for the specified file format, it retruns an empty list. 
    Suported parsers are CSV and XML.

    Parameters
    ----------
        file_path (str): string containing the full path of the metadata file  

   
    Returns
    -------
        list: list of a,v,u triplets containing the parsed metadata
    """
    file = Path(file_path)
    if not file.exists():
        return []

    file_extension = Path(file_path).suffix
    if file_extension in type_mapper:
        return type_mapper[file_extension]['func'](file_path)
    else:
        return []
