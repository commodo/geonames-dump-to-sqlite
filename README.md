Description
===========
A tool to parse the dumped text files from [geonames.org](http://download.geonames.org/export/dump/ "geonames.org") and insert it into a SQLite3 database file.

This tool only cares about Continents, Countries and Administration Levels 1 to 4 (regions, cities and other sub-divisions). Other objectives are not of interest. The main purpose is to create a DB that can be used for a user-location signup form.

To run it you can run it with: **python create_locations_db.py** and it will run with defaults.
Two parameters are given :
* **--out** or **-o** - the output file name for the SQLite3 DB; default is locations.sqlite3
* **--tmp-dir** or **-t** - the temp dir where to work; default is '.' (current directory)

The output format of the DB is the one described on the [geonames.org](http://download.geonames.org/export/dump/ "geonames.org") site **PLUS** one more field called **parent_id**.

So it's

    parent_id         : the ID of the containing continent/country/region/administration level; this field is taken from the **hierarchy.txt** dump 
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


