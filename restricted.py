import os
import csv
import requests

# Script to get a list of datasets with restricted files and writes to a CSV file.
# Includes number of restricted files, dataset DOI and publication date.

api = "https://borealisdata.ca/api/"
search = api + "search"
s_params = {"q": "*",
            "subtree": "ualberta",
            "type": "dataset",
            "per_page": "1000"}
r = requests.get(search, params=s_params)
results = r.json()
search_metadata = results['data']['items']
metadata_all = []

for dataset in search_metadata:
    doi = dataset['global_id']
    e_params = {'exporter': 'dataverse_json',
                'persistentId': doi}
    export = api + "datasets/export"
    export_single_md = requests.get(export, params=e_params)
    md_single = export_single_md.json()
    metadata_all.append(md_single)

restricted_datasets = []
for ds in metadata_all:
    filelist = ds['datasetVersion']['files']
    n_restr = 0
    for file in filelist:
        if not file['restricted']:
            continue
        else:
            n_restr += 1
    if n_restr > 0:
        info = {'doi':ds['persistentUrl'],
                'n_restricted_files':n_restr,
                'date':ds['publicationDate']}
        restricted_datasets.append(info)

#Write to csv
with open(os.path.join("reports","restricted_files.csv"), 'w') as c:
    writer = csv.DictWriter(c, fieldnames=['doi','n_restricted_files','date'])
    writer.writeheader()
    for line in restricted_datasets:
        writer.writerow(line)