# coding: utf-8

# This software is distributed under the Modified BSD License

# Copyright (c) 2013, Gaspard Jankowiak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#   * Neither the name of the MeteoPyris project nor the
#   names of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL I BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division
import csv
import datetime
import sqlite3
import urllib2
import os
import sys

import MeteoPyris.measures

class Manager:

    try:
        DATABASE_NAME     = os.environ['HOME'] + '/.meteo.db'
    except:
        DATABASE_NAME     = None
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

    def __init__(self, database=DATABASE_NAME):
        self.con = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES);

    def reinit_table(self):
        # check if table exists
        cur = self.con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meteo';")
        s = cur.fetchmany()
        if len(s) > 0:
            cur.execute('DROP TABLE meteo;')
        cur.execute('CREATE TABLE meteo (time timestamp UNIQUE, temp_out Double, out_hum Double, wind_speed Double, pressure Doube, rain Double);');
        self.con.commit()

    def __get_last_entry_date(self):
        cur = self.con.cursor()
        cur.execute('SELECT time FROM meteo ORDER BY datetime(time) DESC LIMIT 1;')
        result = cur.fetchone()
        self.con.commit()
        if result:
            return result[0]
        else:
            return None

    def __parse_dump_line(self, l):
        date = datetime.datetime.strptime('%s %s' % (l['date'], l['time']), self.DUMP_TIME_FMT)
        return (date,
                float(l['temp_out']),
                float(l['out_hum']),
                float(l['wind_speed']),
                float(l['pressure']),
                float(l['rain']))

    def __fetch_parse_dump(self):
        data_list = []
        d = urllib2.urlopen(self.DUMP_URL)

        d.readline(); d.readline(); d.readline() # skip header

        parseddata = csv.DictReader(d, self.DUMP_FIELDS_NAMES, delimiter=' ', skipinitialspace=True)
        for line in parseddata:
            data_list.append(self.__parse_dump_line(line))

        return data_list[::-1]

    def update_database(self):

        last_date = self.__get_last_entry_date()

        data_list = self.__fetch_parse_dump()

        if len(data_list) == 0:
            sys.stderr.write('Error while retrieving data from server')
            return False

        if last_date:
            for i in range(len(data_list)):
                mark = i
                if data_list[i][0] <= last_date:
                    break
        else:
            mark = len(data_list)

        cur = self.con.cursor()

        data_list = data_list[:mark]

        cur.executemany('INSERT INTO meteo VALUES (?, ?, ?, ?, ?, ?);', data_list)
        self.con.commit()

        return len(data_list)

    def _dump_table(self):
        cur = self.con.cursor()

        cur.execute('SELECT * FROM meteo;')

        for l in cur:
            print l

    def fetch_measures(self, from_date=None, to_date=None, hours_back=None, fields=['temp_out']):
        """Fetch specified fields + date from base, between specified dates

        Keyword arguments:
        from_date   -- a datetime.datetime object. If None, defaults to 24 hours before now. Overrides hours_back
        to_date     -- a datetime.datetime object. If None, defaults to now
        hours_back  -- integer, limit data to the last hours_back hours
        fields      -- array of strings, elements of ... . Date will be always included

        """
        for f in fields:
            assert self.DUMP_FIELDS_NAMES.index(f), 'unkown field {0}'.format(f)

        sql_fields = ['time']
        sql_fields.extend(fields)

        if not to_date:
            to_date = datetime.datetime.now()
        else:
            assert to_date.__class__ == datetime.datetime, 'to_date must be datetime.datetime'

        if not from_date:
            if hours_back:
                assert hours_back.__class__ == int, 'hours must be an int'
                delta = datetime.timedelta(hours=abs(hours_back))
            else:
                delta = datetime.timedelta(day=1)
            from_date = datetime.datetime.now()
            from_date -= delta
        else:
            assert from_date.__class__ == datetime.datetime, 'from_date must be datetime.datetime'

        cur = self.con.cursor()
        cur.execute('SELECT %s FROM meteo WHERE datetime(time) >= ? AND datetime(time) <= ? ORDER BY datetime(time) ASC;' % (', '.join(sql_fields)), [from_date, to_date])

        return MeteoPyris.Measures(cur, sql_fields)
