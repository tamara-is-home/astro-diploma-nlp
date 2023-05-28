import os
import re
import argparse
import subprocess
import pandas as pd
from typing import List

gcns_tar_gz_url = "https://gcn.gsfc.nasa.gov/gcn3/all_gcn_circulars.tar.gz"

title_re = r"TITLE:.*"
subject_re = r"SUBJECT:.*"
number_re = r"NUMBER:.*"
date_re = r"DATE:.*"
from_re = r"FROM:.*"
other_gcn_re = r"[\[\s(](?:GCN|gcn).?:?\s?[Circ.]+?\s?([\d\s,]+)|[\[\s(](?:GCN|gcn).?:?\s?#?([\d\s,#]+)"
atel_re = r"[\[\s(](?:ATel|atel)+.?:?\s?#?([\d\s,#]+)"
line_where_authors_end_re = r".*report[s]?:\s?\"?|.*report that:\s?\"?|report on behalf of [a, the]+.*?:\s?\"?"


def get_gcn_names() -> List[str]:
    gcn_files = [f for f in os.listdir("gcn3") if f.endswith('gcn3')]
    gcn_files.sort()
    return gcn_files


def load_gcns() -> List[str]:
    gcns_str = []
    for file in get_gcn_names():
        with open(f"gcn3/{file}", 'rb') as f:
            try:
                gcn = f.read().decode('utf-8')
                gcns_str.append(gcn)
            except:
                gcn = f.read().decode('windows-1252')
                gcns_str.append(gcn)
    print(f"Loaded {len(gcns_str)} GCNs as plain text")
    return gcns_str


def parse_gcns(gcns_str: List[str]):
    bodies = []
    titles = []
    numbers = []
    subjects = []
    dates = []
    froms = []
    other_gcns = []
    other_atels = []

    for gcn in gcns_str:
        clean_gcn = gcn

        title = re.findall(title_re, gcn)
        if title:
            title = title[0]
            clean_gcn = clean_gcn.replace(title, '')
            titles.append(title.replace("TITLE:", '').strip())
        else:
            titles.append(None)

        subject = re.findall(subject_re, gcn)
        if subject:
            subject = subject[0]
            clean_gcn = clean_gcn.replace(subject, '')
            subjects.append(subject.replace("SUBJECT:", '').strip())
        else:
            subjects.append(None)

        number = re.findall(number_re, gcn)
        if number:
            number = number[0]
            clean_gcn = clean_gcn.replace(number, '')
            number = re.search(r"\d+", number)[0]
            numbers.append(number)
        else:
            numbers.append(None)

        date = re.findall(date_re, gcn)
        if date:
            date = date[0]
            clean_gcn = clean_gcn.replace(date, '')
            dates.append(date.replace("DATE:", '').strip())
        else:
            dates.append(None)

        from_ = re.findall(from_re, gcn)
        if from_:
            from_ = from_[0]
            clean_gcn = clean_gcn.replace(from_, '')
            froms.append(from_.replace("FROM:", '').strip())
        else:
            froms.append(None)

        gcn_references = re.findall(other_gcn_re, clean_gcn)
        this_gcn_refs = []
        for ref_group in gcn_references:
            for ref in ref_group:
                processed_refs = [x.replace('#', '').strip() for x in ref.split(',') if x.replace('#', '').strip()]
                try:
                    this_gcn_refs.extend(list(set([int(x) for x in processed_refs])))
                except:
                    pass
        other_gcns.append(list(set([int(x) for x in this_gcn_refs])))

        atel_references = re.findall(atel_re, clean_gcn)
        processed_refs = []
        for ref in atel_references:
            try:
                processed_refs = [x.replace('#', '').strip() for x in ref.split(',') if x.replace('#', '').strip()]
                processed_refs = list(set([int(x) for x in processed_refs]))
            except:
                pass
        other_atels.append(processed_refs)

        line_where_authors_end = re.search(line_where_authors_end_re, clean_gcn)
        if line_where_authors_end:
            clean_gcn_parts = clean_gcn.split(line_where_authors_end[0])
            if len(clean_gcn_parts) == 2:
                clean_gcn = clean_gcn_parts[1]

        bodies.append(clean_gcn.replace(">", "").replace('\n', ' ').replace('\r', '').strip("\"").strip())
    return bodies, subjects, numbers, dates, froms, other_gcns, other_atels


def search_from_email_gcn(from_field):
    gcn_from_re = r"<(.*)>"
    exact_match = re.findall(gcn_from_re, from_field)
    if exact_match:
        return exact_match[0]
    from_parts = from_field.split(' ')
    for part in from_parts:
        if '@' in part:
            return part
    return ''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse all GCN telegrams')
    parser.add_argument('--csv_filename', '-n', type=str, default="gcn.csv")
    args = parser.parse_args()
    filename = args.csv_filename
    gcn_df = pd.DataFrame([], columns=['body', 'subject', 'date', 'from', 'number', 'gcn_refs', 'atel_refs'])
    # load tar.gz with all available GCNs, unzip it
    subprocess.run(f'wget {gcns_tar_gz_url}', shell=True)
    subprocess.run('tar -xzvf all_gcn_circulars.tar.gz', shell=True)
    all_str_gcns = load_gcns()
    bodies, subjects, numbers, dates, froms, other_gcns, other_atels = parse_gcns(all_str_gcns)
    # create DF
    gcn_df['body'] = bodies
    gcn_df['subject'] = subjects
    # gcn_df['title'] = titles  # GCN titles are useless
    gcn_df['number'] = numbers
    gcn_df['date'] = dates
    gcn_df['from'] = froms
    gcn_df['gcn_refs'] = other_gcns
    gcn_df['atel_refs'] = other_atels
    gcn_df['type'] = ['gcn'] * len(gcn_df)
    # set gcn number as index
    gcn_df = gcn_df.dropna(subset=['number']).drop_duplicates(subset=['number'], keep='first').set_index("number")
    # parse `from` col to leave only the author(s)' email
    gcn_df = gcn_df.dropna(subset=['from'])
    gcn_df['from'] = gcn_df['from'].apply(search_from_email_gcn)
    # parse the date
    gcn_df['date'] = gcn_df['date'].apply(lambda x: pd.to_datetime(x, errors='coerce', yearfirst=True))
    # save
    print(f"Loaded and parsed {len(gcn_df)} GCNs, saving it to {filename}")
    gcn_df.to_csv(filename, index=True, errors='ignore')
    # cleaning
    subprocess.run(f'rm -f all_gcn_circulars.tar.gz', shell=True)
    subprocess.run(f'rm -rf gcn3', shell=True)
