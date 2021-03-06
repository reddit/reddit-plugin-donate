from __future__ import print_function, division

import csv
import json

from reddit_donate import models, utils


MIN_PREFIX_LEN = 3


def _generate_prefixes(display_name):
    sanitized = utils.sanitize_query(display_name)

    words = sanitized.split()
    for i in xrange(len(words)):
        spaceless = "".join(words[i:])
        for prefix_len in xrange(MIN_PREFIX_LEN, len(spaceless)+1):
            yield spaceless[:prefix_len]


def _coerce_values(mapping, function, keys):
    for key in keys:
        value = mapping.get(key)
        if value:
            mapping[key] = function(value)


def load_charity_data(csv_filename):
    reader = csv.DictReader(open(csv_filename))

    org_batch = models.DonationOrganization._cf.batch()
    prefix_batch = models.DonationOrganizationsByPrefix._cf.batch()

    for i, row in enumerate(reader):
        if i % 10000 == 0:
            print("{: 5.2%} progress".format(i / 1497802))

        # coerce various values from the csv
        row = {k: unicode(v, "utf-8") for k, v in row.iteritems()}
        _coerce_values(row, int, ["EIN"])
        _coerce_values(row, float,
            ["OverallScore", "OverallRtg", "ATScore", "ATRtg"])

        serialized = json.dumps(row)
        org_batch.insert(row["EIN"], {"data": serialized})

        # we only do autocomplete for rated orgs as the master list has a huge
        # huge huge number of duplicate names etc.
        if row["OrgID"]:
            score = row["OverallScore"] or 0
            display_name = row["DisplayName"]

            for prefix in _generate_prefixes(display_name):
                prefix_batch.insert(prefix, {(score, display_name): serialized})
