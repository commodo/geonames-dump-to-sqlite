#!/usr/bin/env python

"""
Utility to dump the data from geonames.org to an SQLite3 database.
"""

import os
import sys
import sqlite3
import codecs
import argparse
import shutil
import urllib2
import zipfile

# Some constants; well, that's how they're defined on the site
BASE_URL = "http://download.geonames.org/export/dump/"
COUNTRIES_ZIP_FILE = "allCountries.zip"
COUNTRIES_TXT_FILE = "allCountries.txt"
HIERARCHY_ZIP_FILE = "hierarchy.zip"
HIERARCHY_TXT_FILE = "hierarchy.txt"

# Handle argument parsing here
parser = argparse.ArgumentParser()
parser.add_argument( "-t", "--temp-dir", default=".", help="Temporary work directory")
parser.add_argument( "-o", "--out",      default="locations.sqlite3", help="Output file name for the SQLite3 DB")
args = parser.parse_args()

# And get the arguments of interest and put them in our constants.
TMP_DIR = args.temp_dir
OUT_SQLITE_FILE = args.out

REMOTE_COUNTRIES_ZIP_URL = BASE_URL + COUNTRIES_ZIP_FILE
REMOTE_HIERARCHY_ZIP_URL = BASE_URL + HIERARCHY_ZIP_FILE
LOCAL_HIERARCHY_ZIP_FILE = os.path.join(TMP_DIR, HIERARCHY_ZIP_FILE)
LOCAL_COUNTRIES_ZIP_FILE = os.path.join(TMP_DIR, COUNTRIES_ZIP_FILE)
LOCAL_HIERARCHY_TXT_FILE = os.path.join(TMP_DIR, HIERARCHY_TXT_FILE)
LOCAL_COUNTRIES_TXT_FILE = os.path.join(TMP_DIR, COUNTRIES_TXT_FILE)

TABLE_MAPPINGS = { "PCLI" : "countries",
                    "CONT" : "continents",
                    "ADM1" : "adminlevel1s",
                    "ADM2" : "adminlevel2s",
                    "ADM3" : "adminlevel3s",
                    "ADM4" : "adminlevel4s",
            }
'''
    Below are fields described @ http://download.geonames.org/export/dump/
    We've adapted this into our own SQLite3 DB ; right now we just added the parent_id field
    instead of using a hierarchy table.

    geonameid         : integer id of record in geonames database
    name              : name of geographical point (utf8) varchar(200)
    asciiname         : name of geographical point in plain ascii characters, varchar(200)
    alternatenames    : alternatenames, comma separated varchar(5000)
    latitude          : latitude in decimal degrees (wgs84)
    longitude         : longitude in decimal degrees (wgs84)
    feature class     : see http://www.geonames.org/export/codes.html, char(1)
    feature code      : see http://www.geonames.org/export/codes.html, varchar(10)
    country code      : ISO-3166 2-letter country code, 2 characters
    cc2               : alternate country codes, comma separated, ISO-3166 2-letter country code, 60 characters
    admin1 code       : fipscode (subject to change to iso code), see exceptions below, see file admin1Codes.txt for display names of this code; varchar(20)
    admin2 code       : code for the second administrative division, a county in the US, see file admin2Codes.txt; varchar(80) 
    admin3 code       : code for third level administrative division, varchar(20)
    admin4 code       : code for fourth level administrative division, varchar(20)
    population        : bigint (8 byte int) 
    elevation         : in meters, integer
    dem               : digital elevation model, srtm3 or gtopo30, average elevation of 3''x3'' (ca 90mx90m) or 30''x30'' (ca 900mx900m) area in meters, integer. srtm processed by cgiar/ciat.
timezone          : the timezone id (see file timeZone.txt) varchar(40)
    modification date : date of last modification in yyyy-MM-dd format
'''
TABLE_FIELDS = [{'parentid'       : 'integer'},
                {'geonameid'      : 'integer'},
                {'name'           : 'text'},
                {'asciiname'      : 'text'},
                {'alternatenames' : 'text'},
                {'latitude'       : 'real'},
                {'longitude'      : 'real'},
                {'feature_class'  : 'text'},
                {'feature_code'   : 'text'},
                {'country_code'   : 'text'},
                {'cc2'            : 'text'},
                {'admin1_code'    : 'text'},
                {'admin2_code'    : 'text'},
                {'admin3_code'    : 'text'},
                {'admin4_code'    : 'text'},
                {'population'     : 'integer'},
                {'elevation'      : 'integer'},
                {'dem'            : 'integer'},
                {'timezone'       : 'text'},
                {'modification'   : 'date'}]


# Simple code to download file (alternative to wget )
def download_file(url, dst_file):
    req = urllib2.urlopen(url)
    with open(dst_file, 'wb') as fp:
        shutil.copyfileobj(req, fp)

def create_tables(cur):
    '''
    Create empty tables which will be populated later.
    '''
    for table_name in TABLE_MAPPINGS.values():
        cur.execute('DROP TABLE IF EXISTS %s' % table_name)
        table_fields = [ "%s %s" % table_field.items()[0] for table_field in TABLE_FIELDS ]
        cur.execute('CREATE TABLE %s (%s)' % (table_name, ','.join(table_fields)))


def get_db_links():
    '''
    Extracts the links from the hierarchy text file.
    '''
    # Forward links and reverse links
    fwd_links = {}
    rev_links = {}

    with codecs.open(LOCAL_HIERARCHY_TXT_FILE, 'r', encoding = "utf-8") as f:
        line = f.readline()
        while line != '':
            line_elems = line.split('\t')
            if len(line_elems) != 3:
                print "Line was not split correctly"
                break
            
            parent_id, child_id = None, None
            if line_elems[2].strip().lower() == 'adm':
                parent_id, child_id = line_elems[0], line_elems[1]
            elif line_elems[2].strip().lower() == 'parent':
                parent_id, child_id = line_elems[1], line_elems[0]
            if (parent_id is not None) and (child_id is not None):
                fwd_links[parent_id] = child_id
                rev_links[child_id]  = parent_id

            line = f.readline()

    return fwd_links, rev_links


def dump_to_db(cur):

    fwd_links, rev_links = get_db_links()

    with codecs.open(LOCAL_COUNTRIES_TXT_FILE, 'r', encoding = "utf-8") as f:
        line = f.readline()
        while line != '':
            line_elems = line.split('\t')
            if len(line_elems) != 19:
                print "Line was not split correctly"
                break
            table_name = TABLE_MAPPINGS.get(line_elems[7].upper())
            parent_id  = rev_links.get(line_elems[0])
            if (table_name is not None) and (parent_id is not None):
                # clean line elems first
                line_elems = [ (u'"%s"' % line_elem.strip().replace('"', '""') ) for line_elem in line_elems ]
                table_fields = [ "%s" % table_field.keys()[0] for table_field in TABLE_FIELDS ]
                cur.execute('INSERT INTO %s (%s) VALUES (%s)' % (table_name, ','.join(table_fields), (parent_id + ',' +','.join(line_elems))) )
            line = f.readline()

# The rest of the main code is here
for _zip_ in [COUNTRIES_ZIP_FILE, HIERARCHY_ZIP_FILE]:
    if not os.path.isfile(_zip_):
        print "Downloading " + _zip_
        download_file(BASE_URL + _zip_, os.path.join(TMP_DIR, _zip_))

    print "Extracting all files from " + _zip_
    z = zipfile.ZipFile(_zip_)
    z.extractall(TMP_DIR)

con = None
# And below we do the dump to SQLite
try:

    con = sqlite3.connect(OUT_SQLITE_FILE)
    cur = con.cursor()
    print "Creating tables in file '%s'" % OUT_SQLITE_FILE
    create_tables(cur)
    print "Started parsing and dumping"
    dump_to_db(cur)
    if (os.path.isfile(LOCAL_COUNTRIES_TXT_FILE)):
        os.remove(LOCAL_COUNTRIES_TXT_FILE)
    if (os.path.isfile(LOCAL_HIERARCHY_TXT_FILE)):
        os.remove(LOCAL_HIERARCHY_TXT_FILE)
    con.commit()
    print "Done."

except sqlite3.Error, e:
    con = None
    print "Error %s:" % e.args[0]
    sys.exit(1)
    
if (con):
    con.close()
