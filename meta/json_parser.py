import json


# {"avus": [{"attribute": "a", "value": "b", "units": "c"},
#           {"attribute": "x", "value": "y"}]}


def get_metadata_list_json(file_path):
    
    with open(file_path) as json_file:
        avus_dict = json.load(json_file)
        try:
            return [[avu["attribute"], avu["value"], avu.get("units", '')] for avu in avus_dict["avus"]]
        except KeyError:
            return [] 

    return []