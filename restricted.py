import os
import csv
import requests

# Script to get a list of datasets with restricted files and writes to a CSV file.
# Includes number of restricted files, dataset DOI, publication date, license, and .

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

# Get dowload counts (all files)
dlapi = api+"info/metrics/filedownloads"
dls_req = requests.get(dlapi,headers={'Accept':'application/json'},params={"parentAlias":"ualberta"})
dls = dls_req.json()['data']

# Identify datasets with restricted files
restricted_datasets = []
for ds in metadata_all:
    filelist = ds['datasetVersion']['files']
    n_restr = 0
    for file in filelist:
        if not file['restricted']:
            continue
        else:
            n_restr += 1
            #Lookup file id in download count list - get total downloads of restricted files for this dataset
            downloads = 0
            file_id = file['dataFile']['id']
            for item in dls:
                if item['id'] == file_id:
                    downloads += item['count']
                    break
    if n_restr > 0:
        citation = ds['datasetVersion']['metadataBlocks']['citation']['fields']
        # Get title
        for field in citation:
            if field['typeName'] == 'title':
                title = field['value']
            #Get subject
            if field['typeName'] == 'subject':
                subject = field['value']
        # Get license
        if 'license' in ds['datasetVersion'].keys():
            license_name = ds['datasetVersion']['license']['name']
        elif 'termsOfUse' in ds['datasetVersion'].keys():
            if 'CC0 Waiver' in ds['datasetVersion']['termsOfUse']:
                license_name = 'CC0 Waiver'
            else:
                license_name = 'Custom'
        info = {'title':title,
                'doi':ds['persistentUrl'],
                'n_restricted_files':n_restr,
                'date':ds['publicationDate'],
                'license':license_name,
                'downloads':downloads,
                'subject':subject}
        restricted_datasets.append(info)

#Write to csv
with open(os.path.join("reports","restricted_files.csv"), 'w') as c:
    writer = csv.DictWriter(c, fieldnames=list(info.keys()))
    writer.writeheader()
    for line in restricted_datasets:
        writer.writerow(line)