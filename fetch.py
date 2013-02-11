#!/usr/bin/python

# Copyright (c) 2013, Gaspard Jankowiak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     - Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#     - Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#     - Neither the name of the <ORGANIZATION> nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re, csv, datetime, sqlite3, urllib2, os, sys

DATABASE_NAME     = os.environ['HOME'] + '/.meteo.db'
DUMP_URL          = 'http://static.meteo-paris.com/station/downld02.txt'
DUMP_TIME_FMT     = '%d/%m/%y %H:%M'
DUMP_FIELDS_NAMES = [
                        'date', 'time', 'temp_out', 'hi_temp', 'low_temp',
                        'out_hum', 'dew_pt', 'wind_speed', 'wind_dir',
                        'wind_run', 'hi_speed', 'hi_dir', 'wind_chill',
                        'heat_idx', 'thw_idx', 'pressure', 'rain', 'rain_rate',
                        'heat_dd', 'cool_dd', 'in_temp', 'in_hum',
                        'wind_samp', 'wind_tx', 'iss_recept', 'arc_int',
                        'garbage'
                    ]

def init_sql_connection(database=DATABASE_NAME):
    return sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES);

def reinit_table(con):
    # check if table exists
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meteo';")
    s = cur.fetchmany()
    if len(s) > 0:
        cur.execute('DROP TABLE meteo;')
    cur.execute('CREATE TABLE meteo (time timestamp UNIQUE, temp_out Double, out_hum Double, wind_speed Double, pressure Doube, rain Double);');
    con.commit()


def get_last_entry_date(con):
    cur = con.cursor()
    cur.execute('SELECT time FROM meteo ORDER BY datetime(time) DESC LIMIT 1;')
    result = cur.fetchone()
    con.commit()
    if result:
        return result[0]
    else:
        return None

def parse_dump_line(l):
    date = datetime.datetime.strptime('%s %s' % (l['date'], l['time']), DUMP_TIME_FMT)
    return (date,
            float(l['temp_out']),
            float(l['out_hum']),
            float(l['wind_speed']),
            float(l['pressure']),
            float(l['rain']))

def fetch_parse_dump():
    data_list = []
    d = urllib2.urlopen(DUMP_URL)

    d.readline(); d.readline(); d.readline() # skip header

    parseddata = csv.DictReader(d, DUMP_FIELDS_NAMES, delimiter=' ', skipinitialspace=True)
    for line in parseddata:
        data_list.append(parse_dump_line(line))

    return data_list[::-1]

def update_database(con):

    last_date = get_last_entry_date(con)

    data_list = fetch_parse_dump()

    if len(data_list) == 0:
        print 'ERROR: empty data list!'
        sys.exit(1)

    if last_date:
        for i in range(len(data_list)):
            mark = i
            if data_list[i][0] <= last_date:
                break
    else:
        mark = len(data_list)

    cur = con.cursor()

    data_list = data_list[:mark][::-1]

    cur.executemany('INSERT INTO meteo VALUES (?, ?, ?, ?, ?, ?);', data_list)
    con.commit()

    return len(data_list)

def dump_table(con):
    cur = con.cursor()

    cur.execute('SELECT * FROM meteo;')

    for l in cur:
        print l
