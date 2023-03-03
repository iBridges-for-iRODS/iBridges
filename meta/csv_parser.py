import csv


def get_metadata_list_csv(file_path):
    """Extract columns from a CSV file.
    Parameters
    ----------
    filename : str
        Name of the CSV file containing the columns to extract. Each 
        row contains 2 or 3 elements
    
    Returns
    -------
    list of triplets
        Extracted metadata in a list of triplets format. 
    """
    avus = []
    with open(file_path, newline='') as csvfile:
        avus_reader = csv.reader(csvfile, delimiter=',')
        for avu_row in avus_reader:
            if len(avu_row) == 3:
                avus.append(avu_row)
            elif len(avu_row) == 2:
                avus.append(avu_row + [''])
            else:
                continue
    return avus
