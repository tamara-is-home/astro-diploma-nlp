import re
import requests
import argparse
import warnings
import user_agent
import pandas as pd
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

url = "https://www.astronomerstelegram.org"
agent = user_agent.generate_user_agent()
headers = {'User-Agent': agent}

title_pattern = re.compile(r"ATel #(\d{1,9}): (.*)")
related_pattern = re.compile(r"read=(\d{1,9})")
body_pattern = re.compile(r"Tweet(.*?)(Related \d{1,9}|\[ Telegram Index \])")
broken_body_pattern = re.compile(r"Tweet(.*)")  # look 3015
total_telegrams_pattern = re.compile(r"Selected of (\d{1,9}) Telegrams")


def extract_related_ids(soup):
    related = []
    related_tag = soup.find('a', text=" Related ")
    if related_tag:
        for parent in related_tag.parent:
            related.extend(related_pattern.findall(str(parent)))
    return related


def extract_subjects(soup):
    subjects = list()
    p_tags = soup.find_all("p")
    for tag in p_tags:
        try:
            if "subjects" in tag.attrs['class']:
                subjects = tag.text.replace("Subjects: ", "")
        except: pass
    return subjects


def extract_body(soup):
    test_text = soup.text.replace('\n', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ')
    try:
        body = body_pattern.findall(test_text)[0][0].strip()
    except:
        print('broken body')
        body = broken_body_pattern.findall(test_text)[0].strip()
    return body


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse ATel telegrams from the given #')
    parser.add_argument('--parse_from', '-p', type=int, default=1)
    parser.add_argument('--csv_filename', '-n', type=str, default="atel.csv")
    args = parser.parse_args()
    first_atel = args.parse_from
    filename = args.csv_filename

    cols = ['title', 'date', 'authors', 'credential_certification', 'subjects', 'body', 'related_ids']
    df = pd.DataFrame([], columns=cols)

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text)
    total_telegrams = int(total_telegrams_pattern.findall(soup.find('em').text)[0])
    print(f"There are {total_telegrams} telegrams!")

    for i in range(first_atel, total_telegrams + 1):
        print(f"Querying for telegram #{i}")
        try:
            resp = requests.get(url, headers=headers, params=f"read={i}")
            resp.raise_for_status()
            # parse
            soup = BeautifulSoup(resp.text, "html.parser")
            # extract id and title
            index, title = int(title_pattern.match(soup.title.text.strip()).group(1)), title_pattern.match(
                soup.title.text.strip()).group(2)
            # extract related ids
            related_ids = extract_related_ids(soup)
            # extract authors and publication date
            strong_tags = soup.find_all("strong")
            authors, date = strong_tags[0].text, strong_tags[1].text
            # extract cred certification
            credential_certification = soup.find_all("em")[1].text.replace("Credential Certification: ", "")
            # subjects
            subjects = extract_subjects(soup)
            # body
            body = extract_body(soup)

            df.loc[index] = [title, date, authors, credential_certification, subjects, body, related_ids]

        except Exception as e:
            print(f'An error occurred while querying for telegram #{i}', e)
    
    print(f"Adding loaded ATels to {filename} (if exists)")
    try:
        df_old = pd.read_csv(filename, index_col=0)
    except: 
        df_old = pd.DataFrame()
    df = pd.concat((df_old, df)).reset_index().drop_duplicates(subset='index', keep='last').set_index('index')
    df.to_csv(filename, index=True, errors='ignore')
    print(f"Done, loaded {len(df)-len(df_old)} new ATels")
    