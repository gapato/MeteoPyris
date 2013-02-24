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

import json
from json import encoder
encoder.FLOAT_REPR = lambda o: format(o, '.2f')

class Measures:

    def __init__(self, cursor, sql_fields):

        self.data = []

        for l in cursor:

            row = {}

            k = 0
            for i in sql_fields:
                row[i] = l[k]
                k += 1

            self.data.append(row)

        cursor.connection.commit()

    def length(self):
        return len(self.data)

    def _prefilter_data(self, window_width=1):

        d = None
        date_start = date_end = None

        avg = {}
        post_filter_dict = {}

        keys = self.data[0].keys()
        keys.remove('time')

        for k in keys:
            avg[k] = 0
            post_filter_dict['%s_DATA' % k.upper()] = []

        i = 0
        n = 0
        for row in self.data:

            if n == 0:
                date_start = row['time']
                n = 1

            i += 1

            for k in keys:
                avg[k] = avg[k]*(i-1)/i + row[k]/i

            if window_width == 1 or i == window_width//2:
                date_end = d = row['time']

            if i < window_width:
                continue
            else:
                i = 0
                for k in keys:
                    post_filter_dict['%s_DATA' % k.upper()].append(round(avg[k],2))
                    avg[k] = 0

        post_filter_dict['START_DATE'] = date_start
        post_filter_dict['END_DATE'] = date_end

        return post_filter_dict

    def serialize_json(self, filename=None, window_width=1):

        assert self.length() > 0, 'Measure set is empty, cannot render'

        filtered_data = self._prefilter_data(window_width)

        obj_to_serial = filtered_data.copy()

        obj_to_serial['START_DATE'] = obj_to_serial['START_DATE'].isoformat()
        obj_to_serial['END_DATE']   = obj_to_serial['END_DATE'].isoformat()

        obj_to_serial['TIME_STEP'] = 1000 * 60 * 5 * window_width

        if filename:
            with open(filename, 'w') as fd:
                json.dump(obj_to_serial, fd)
        else:
            return json.dumps(obj_to_serial)

    def render_template(self, filename, window_width=1):

        assert self.length() > 0, 'Measure set is empty, cannot render'

        try:
            import pystache
        except:
            raise ImportError('MeteoPyris needs the pystache package to render templates')

        filtered_data = self._prefilter_data(window_width)
        ds = filtered_data['START_DATE']
        de = filtered_data['END_DATE']
        template_context = {
            'START_DATE' : 'Date.UTC(%d, %d, %d, %d ,%d, 0)' % (ds.year, ds.month-1, ds.day, ds.hour, ds.minute),
            'END_DATE'   : 'Date.UTC(%d, %d, %d, %d ,%d, 0)' % (de.year, de.month-1, de.day, de.hour, de.minute),
            'TIME_STEP'  : '%d' % (1000 * 60 * 5 * window_width)
            }
        for k in filtered_data.keys():
            if k == 'START_DATE' or k == 'END_DATE':
                continue
            template_context[k] = ','.join(map(str, filtered_data[k]))

        r = ''
        renderer = pystache.Renderer(file_encoding='utf-8', string_encoding='utf-8')
        with open(filename, 'r') as template:
            for line in template:
                r += renderer.render(line, template_context)
        return r
