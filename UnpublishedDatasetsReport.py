#!/usr/bin/env python3
import logging
import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests

logging.basicConfig(filename="UnpublishedSearch.log", level=logging.INFO)

# Use Dataverse's Search API to retrieve a report of datasets with the "unpublished" status.
# Parse the JSON response to filter only for those uploaded over six months ago.
# Write results to csv file.

token = input("Enter API key: ")
search_api = "https://borealisdata.ca/api/search"
params = {"q": "*",
          "subtree": "ualberta",
          "fq": "publicationStatus:Unpublished",
          "type": "dataset",
          "per_page": "1000"}

r = requests.get(search_api, params=params, headers={"X-Dataverse-key": token})

if r.status_code == 200:
    response = r.json()
    drafts = response['data']['items']  # This is a list of dicts where each item is a dataset's metadata
    # Make a list of results that are from the last six months. These won't be included in the report.
    to_remove = []
    for i in range(len(drafts)):
        # Unpublished items don't have resolvable DOI. Create the resolvable URL for ease of report.
        url = "https://borealisdata.ca/dataset.xhtml?persistentId=" + drafts[i]['global_id']
        drafts[i]['resolvable_url'] = url
        # Compare date added w current date
        created_at = drafts[i]['createdAt'].split("T")[0]
        parsed_date = datetime.strptime(created_at, "%Y-%m-%d")
        date_diff = relativedelta(datetime.today(), parsed_date)
        if date_diff.years > 0:
            continue
        elif date_diff.months > 6:
            continue
        elif date_diff.months <= 6:
            to_remove.append(drafts[i])
    # Remove from list if less than 6 months old. No need to follow up on these yet.
    if len(to_remove) > 0:
        for item in to_remove:
            drafts.remove(item)
    # Write to csv
    with open("DraftDatasetReport.csv", 'w', newline="") as c:
        writer = csv.DictWriter(c, fieldnames=['dataverse', 'contact', 'url', 'title', 'date_created'])
        writer.writeheader()
        for line in drafts:
            # Only write columns that we need. Parse contacts column to only return the name.
            newline = {'dataverse': line['identifier_of_dataverse'], 'contact': line['contacts'][0]['name'],
                       'url': line['resolvable_url'],
                       'title': line['name'], 'date_created': line['createdAt']}
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
else:
    logging.error("Request response code: " + str(r.status_code))
