import requests
import os

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

# Get datasets that have related citation
# First get list of dataset ids to check
search = api + "search"
s_params = {"q": "*",
            "subtree": "ualberta",
            "type": "dataset",
            "per_page": "1000"}
r = requests.get(search, params=s_params)
results = r.json()

# Total count should be equal to total number of datasets
print("Total datasets: " + str(results['data']['total_count']))

# This is a list of the JSON metadata for each dataset. Unfortunately it uses a different format than the other APIs so
# we need to do some fanangling to get the actual dataset_id value for each.
search_metadata = results['data']['items']

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

# Counters for citation metadata metrics
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

# Get list of files: https://borealisdata.ca/api/datasets/[dataset_id]/versions/:latest-published/files
# Get file metadata: https://borealisdata.ca/api/files/760529/metadata
# :persistentId/ /api/datasets/:persistentId/?persistentId=$PERSISTENT_IDENTIFIER
# Just citation md: export = api + "/datasets/:persistentId/versions/:latest-published/metadata/citation"
