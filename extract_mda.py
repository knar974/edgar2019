import os
import re
import unicodedata
from bs4 import BeautifulSoup

#%%
def main():
    '''
    Adapted : NK April 2022
    assumes 10k form is for e.g 1592706_10-K_2019-11-15_0000109177-19-000050.txt, i.e.:
    cik_form_date-of-filing_Accession-Number.txt uses it to create header for extracted item 7 md&a
    form 10k parsed, special characters removed, before md&a extracted contents compared and found matching  with that
    produced by R's edgar library:
    library(edgar)
    useragent = "knar74@gmail.com"
    output <- getMgmtDisc(cik.no = c(1592706), filing.year = 2019, useragent)
    '''
    basepath = "./data/form10k"
    parse_dir = "./data/form10k.parsed/"
    mda_dir = "./data/mda/"
    fn_key = ['CIK: ' , 'form: ' , 'filing-date: ' , 'accession-number: ']
    for fn in os.listdir(basepath):
        if fn.endswith(".txt"):
            print('processing ', fn)
            #fn = '1592706_10-K_2019-11-15_0000109177-19-000050'
            fn_parts = fn.split('_')

            file_hdr = list(zip(fn_key , fn_parts))


            form_dirp = basepath + '/' + fn

            parse_dirp = parse_dir + fn

            mda_dirp = mda_dir + fn
            parse_xml(form_dirp, parse_dirp)
            parse_mda(parse_dirp, mda_dirp, file_hdr)


def write_content2(content, hdr, output_path):
    """ Writes content to file
    Args:
        content (str)
        hdr (str)
        output_path (str): path to output file
    """
    with open(output_path, "w", encoding="utf-8") as fout:
        for line in hdr:
            fout.write(str(line)+'\n')
        fout.write('\n') #add extra line for blank Company Name
        fout.write('\n')
        fout.write('\n')
        fout.write(content)

def write_content(content, output_path):
    """ Writes content to file
    Args:
        content (str)
        output_path (str): path to output file
    """
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(content)

def parse_xml(input_file, output_file, overwrite=True):
    """ Parses text from html with BeautifulSoup
    Args:
        input_file (str)
        output_file (str)
    """
    if not overwrite and os.path.exists(output_file):
        print("{} already exists.  Skipping parse html...".format(output_file))
        return

    print("Parsing xml {}".format(input_file))
    with open(input_file, 'r', encoding='utf-8') as fin:
        content = fin.read()
    # Parse html with BeautifulSoup
    soup = BeautifulSoup(content, "lxml")
    # soup.prettify
    text = soup.get_text("\n")
    # breakpoint()
    # d = process_header(content)
    # import pdb; pdb. set_trace()

    write_content(text, output_file)
    # Log message
    print("Write to {}".format(output_file))


def remove_special_characters(text, remove_digits=False):
    pattern = r'[^a-zA-z0-9\&\.\s]' if not remove_digits else r'[^a-zA-z\&\.\s]'
    text = re.sub(pattern, ' ', text)
    text=text.replace('[',' ')
    text=text.replace(']',' ')
    text=text.replace('_',' ')

    return text

def normalize_text(text):
    """Normalize Text
    """
    text = unicodedata.normalize("NFKD", text)  # Normalize
    text = '\n'.join(text.splitlines())  # Unicode break lines

    # Convert to upper
    text = text.upper()  # Convert to upper

    # Take care of breaklines & whitespaces combinations due to beautifulsoup parsing
    text = re.sub(r'[ ]+\n', '\n', text)
    text = re.sub(r'\n[ ]+', '\n', text)
    text = re.sub(r'\n+', '\n', text)

    # To find MDA section, reformat item headers
    text = text.replace('\n.\n', '.\n')  # Move Period to beginning

    text = text.replace('\nI\nTEM', '\nITEM')
    text = text.replace('\nITEM\n', '\nITEM ')
    text = text.replace('\nITEM  ', '\nITEM ')

    text = text.replace(':\n', '.\n')

    # Math symbols for clearer looks
    text = text.replace('$\n', '$')
    text = text.replace('\n%', '%')

    # Reformat
    text = text.replace('\n', '\n\n')  # Reformat by additional breakline

    #chunk from ParseXML.
    text = remove_special_characters(text)

    return text

def parse_mda(form_path, mda_path, file_hdr,overwrite=True):
    """ Reads form and parses mda
    Args:
        form_path (str)
        mda_path (str)
    """
    if not overwrite and os.path.exists(mda_path):
        print("{} already exists.  Skipping parse mda...".format(mda_path))
        return
    # Read
    print("Parse MDA {}".format(form_path))
    with open(form_path, "r", encoding='utf-8') as fin:
        text = fin.read()

    # Normalize text here
    text = normalize_text(text)

    # Parse MDA
    mda, end = find_mda_from_text(text)
    # Parse second time if first parse results in index
    if mda and len(mda.encode('utf-8')) < 1000:
        mda, _ = find_mda_from_text(text, start=end)

    if mda:
        print("Write MDA to {}".format(mda_path))
        write_content2(mda.lower(), file_hdr, mda_path)
    else:
        print("Parse MDA failed {}".format(form_path))


def find_mda_from_text(text, start=0):
    """Find MDA section from normalized text
    Args:
        text (str)s
    """
    debug = False

    mda = ""
    end = 0

    # Define start & end signal for parsing
    item7_begins = [
        '\nITEM 7.', '\nITEM 7 –', '\nITEM 7:', '\nITEM 7 ', '\nITEM 7\n'
    ]
    item7_ends = ['\nITEM 7A']
    if start != 0:
        item7_ends.append('\nITEM 7')  # Case: ITEM 7A does not exist
    item8_begins = ['\nITEM 8']
    """
    Parsing code section
    """
    text = text[start:]

    # Get begin
    for item7 in item7_begins:
        begin = text.find(item7)
        if debug:
            print(item7, begin)
        if begin != -1:
            break

    if begin != -1:  # Begin found
        for item7A in item7_ends:
            end = text.find(item7A, begin + 1)
            if debug:
                print(item7A, end)
            if end != -1:
                break

        if end == -1:  # ITEM 7A does not exist
            for item8 in item8_begins:
                end = text.find(item8, begin + 1)
                if debug:
                    print(item8, end)
                if end != -1:
                    break

        # Get MDA
        if end > begin:
            mda = text[begin:end].strip()
            mda = mda.replace('\n\n',' ')
            # import pdb; pdb. set_trace()
        else:
            end = 0

    return mda, end
'''
import argparse
import csv
import concurrent.futures
import itertools

import time

from collections import namedtuple
from functools import wraps
from glob import glob

import requests
'''
if __name__ == "__main__":
    main()