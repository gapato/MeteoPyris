#!/usr/bin/python
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

import csv
import datetime
import sqlite3
import urllib2
import os
import sys

class Manager:

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

        data_list = data_list[:mark][::-1]

        cur.executemany('INSERT INTO meteo VALUES (?, ?, ?, ?, ?, ?);', data_list)
        self.con.commit()

        return len(data_list)

    def dump_table(self):
        cur = self.con.cursor()

        cur.execute('SELECT * FROM meteo;')

        for l in cur:
            print l

    def render_template(self, filename):

        try:
            import pystache
        except:
            sys.stderr.write('MeteoPyris needs the pystache package to render templates')
            return False

        cur = self.con.cursor()
        cur.execute('SELECT time, temp_out, pressure FROM meteo ORDER BY datetime(time) DESC LIMIT 5000;')

        temp_datastring = ''
        press_datastring = ''
        i = -1
        for l in cur:

            if i == -1 and l[0].minute % 30 != 0:
                continue

            i+=1

            d = l[0]
            t = l[1]
            p = l[2]
            if i % 4 == 0:
                temp_datastring = "[Date.UTC(%d,  %d, %d, %d, %d, %d), %f   ],\n" % (d.year, d.month-1, d.day, d.hour, d.minute, 0, t) + temp_datastring
            if i % 6 == 0:
                press_datastring = "[Date.UTC(%d,  %d, %d, %d, %d, %d), %f   ],\n" % (d.year, d.month-1, d.day, d.hour, d.minute, 0, p) + press_datastring

        if len(temp_datastring) > 0:
            temp_datastring = temp_datastring[:-2]
            press_datastring = press_datastring[:-2]
        self.con.commit()

        r = ''
        renderer = pystache.Renderer(file_encoding='utf-8', string_encoding='utf-8')
        with open(filename, 'r') as template:
            for line in template:
                r += renderer.render(line, {'TEMP_DATA' : temp_datastring, 'PRESS_DATA' : press_datastring })

        return r
