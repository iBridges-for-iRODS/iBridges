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
    'xml': {
        'func': get_metadata_list_xml,
        'description': '',
        'reference': '',
    },
}


def parse(file_path):
    file = Path(file_path)
    if not file.exists():
        return []

    file_extension = Path(file_path).suffix
    if file_extension in type_mapper:
        return type_mapper[file_extension].func
