import os
import re
import csv
import requests
from collections import Counter

api = "https://borealisdata.ca/api/"

# Get number of datasets per year (month)
params = {"parentAlias": "ualberta"}
metrics_api = api + "info/metrics/"
r_datasets_monthly = requests.get(metrics_api+"datasets/monthly/", params=params)
monthly = r_datasets_monthly.content
path = os.path.join("reports", "Monthly.csv")
with open(path, "wb") as c:
    c.write(monthly)

# Get datasets by subject
r_subject = requests.get(metrics_api+"datasets/bySubject/", params=params)
subj = r_subject.content
with open(os.path.join("reports", "Subject.csv"), "wb") as c:
    c.write(subj)

# Metrics using Native API (citation metadata, file metadata, etc)
# First get list of datasets to check. Since our dataverse has so many nested dataverses and the Native API endpoint
# for listing contents of a dataverse is not recursive, I am using the search API to start.
search = api + "search"
s_params = {"q": "*",
            "subtree": "ualberta",
            "type": "dataset",
            "per_page": "1000"}
r = requests.get(search, params=s_params)
results = r.json()

# Total count should be equal to total number of datasets (you can verify this from the user interface)
print("Total datasets: " + str(results['data']['total_count']))

# This is a list of the JSON search metadata for each dataset. It doesn't include everything we need, so use the
# DOIs from this to get the full metadata using the Native API.
search_metadata = results['data']['items']

# Get counts by dataverse
dvcount = dict(Counter(d['identifier_of_dataverse'] for d in search_metadata))

# Number with related publication (we can check this with just the search metadata).
n_rel_pub = 0
for dataset in search_metadata:
    if 'publications' in dataset.keys():
        n_rel_pub += 1

# Get list of all metadata blocks
metadata_all = []
for dataset in search_metadata:
    doi = dataset['global_id']
    e_params = {'exporter': 'dataverse_json',
                'persistentId': doi}
    export = api + "datasets/export"
    export_single_md = requests.get(export, params=e_params)
    md_single = export_single_md.json()
    metadata_all.append(md_single)

# Counters for citation metadata metrics (related materials, ORCID use, author affiliation)
n_rel_mat = 0
n_orcid = 0
auth_affil = []
ext_affil = 0

for md in metadata_all:
    # This is a list of fields in the citation metadata
    citation = md['datasetVersion']['metadataBlocks']['citation']['fields']
    ext_total = 0
    n_orcid_total = 0
    for field in citation:
        # Search for author information
        if field['typeName'] == 'author':
            auth = field['value']
            for val in iter(auth):
                if 'authorIdentifierScheme' in val.keys() and val['authorIdentifierScheme']['value'] == 'ORCID':
                    n_orcid_total += 1
                if 'authorAffiliation' in val.keys():
                    auth_affil.append(val['authorAffiliation']['value'])
                    if 'University of Alberta' not in val['authorAffiliation']['value']:
                        ext_total += 1
        if field['typeName'] == 'relatedMaterial' or field['typeName'] == 'relatedDatasets':
            n_rel_mat += 1
    if ext_total > 0:
        ext_affil += 1
    if n_orcid_total > 0:
        n_orcid += 1

# Counters/lists for file metrics and licenses
licenses = []
n_files = []
ds_w_file_desc = 0
ds_w_restricted = 0
total_restricted = 0
ds_readme = 0
file_type = []
documentation_tag = 0

for dataset in metadata_all:
    if 'license' in dataset['datasetVersion'].keys():
        license_name = dataset['datasetVersion']['license']['name']
    elif 'termsOfUse' in dataset['datasetVersion'].keys():
        if 'CC0 Waiver' in dataset['datasetVersion']['termsOfUse']:
            license_name = 'CC0 Waiver'
        else:
            license_name = 'Custom'
    licenses.append(license_name)
    # Get files list
    files = dataset['datasetVersion']['files']
    n_files.append(len(files))
    # Check file metadata
    file_desc = 0
    files_restricted = 0
    files_readme = 0
    files_documentation = 0
    for file in files:
        if 'description' in file.keys():
            file_desc += 1
        if file['restricted']:
            files_restricted += 1
        if re.search('readme|read_me|read\sme', file['label'], re.IGNORECASE):
            files_readme += 1
        if 'friendlyType' in file['dataFile'].keys():
            if file['dataFile']['friendlyType'] == 'Unknown':
                file_type.append(file['dataFile']['contentType'])
            else:
                file_type.append(file['dataFile']['friendlyType'])
        if 'categories' in file.keys():
            for tag in file['categories']:
                if tag == 'Documentation':
                    files_documentation += 1
    if file_desc > 0:
        ds_w_file_desc += 1
    if files_restricted > 0:
        ds_w_restricted += 1
    if files_readme > 0:
        ds_readme += 1
    if files_documentation > 0:
        documentation_tag += 1
    total_restricted = total_restricted + files_restricted

# Storage size - total and by dataverse
storage_size = 0
dataset_sizes = []

for dataset in metadata_all:
    files = dataset['datasetVersion']['files']
    doi = dataset['persistentUrl']
    for result in search_metadata:
        if result['url'] == doi:
            dv_name = result['identifier_of_dataverse']
            break
    try:
        dv_name
    except NameError:
        dv_name = ''
    ds_size = 0
    for file in files:
        ds_size += file['dataFile']['filesize']
        storage_size += file['dataFile']['filesize']
    dataset_sizes.append({'parent_dv': dv_name, 'dataset_size': ds_size})
with open(os.path.join('reports', 'storage_size.csv'), 'w') as c:
    writer = csv.DictWriter(c, fieldnames=['parent_dv', 'dataset_size'])
    writer.writeheader()
    for line in dataset_sizes:
        writer.writerow(line)

# Unpublished datasets
token = input("Enter API key: ")
params = {"q": "*",
          "subtree": "ualberta",
          "fq": "publicationStatus:Unpublished",
          "type": "dataset",
          "per_page": "1000"}
u = requests.get(search, params=params, headers={"X-Dataverse-key": token})
unpubs = u.json()['data']['items']

with open(os.path.join('reports', 'Unpublished.csv'), 'w') as c:
    writer = csv.DictWriter(c, fieldnames=['dataverse', 'doi', 'date_created', 'file_count'])
    writer.writeheader()
    for line in unpubs:
        newline = {'dataverse': line['identifier_of_dataverse'],
                   'doi': line['url'],
                   'date_created': line['createdAt'],
                   'file_count': line['fileCount']}
        try:
            writer.writerow(newline)
        except UnicodeEncodeError:
            utfline = {}
            for k, v in newline.items():
                if isinstance(v, str):
                    utfline[k] = v.encode('utf-8')
            writer.writerow(utfline)
        else:
            continue
