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

        self.data.reverse()
        cursor.connection.commit()

    def length(self):
        return len(self.data)

    def render_template(self, filename, window_width=1):

        assert self.length() > 0, 'Measure set is empty, cannot render'

        try:
            import pystache
        except:
            raise ImportError('MeteoPyris needs the pystache package to render templates')


        d = None
        d_start = d_end = None

        avg = {}
        datastrings = {}

        keys = self.data[0].keys()
        keys.remove('time')

        for k in keys:
            avg[k] = 0
            datastrings[k] = ''

        i = 0
        n = 0
        for row in self.data:

            # remember first and last date (we are filtering backwards, ORDER BY time DESC)
            if n == 0:
                d_end = row['time']
                n = 1

            i += 1

            for k in keys:
                avg[k] = avg[k]*(i-1)/i + row[k]/i

            if window_width == 1 or i == window_width//2:
                d_start = d = row['time']

            if i < window_width:
                continue
            else:
                i = 0
                for k in keys:
                    datastrings[k]  = "%.1f," % (avg[k]) + datastrings[k]
                    avg[k] = 0

        if n > 0:
            for k in keys:
                datastrings[k] = datastrings[k][:-1]
            d_start = "Date.UTC(%d,  %d, %d, %d, %d, %d)" % (d_start.year, d_start.month-1, d_start.day, d_start.hour, d_start.minute, 0)
            d_end   = "Date.UTC(%d,  %d, %d, %d, %d, %d)" % (d_end.year, d_end.month-1, d_end.day, d_end.hour, d_end.minute, 0)

        r = ''
        renderer = pystache.Renderer(file_encoding='utf-8', string_encoding='utf-8')
        with open(filename, 'r') as template:
            for line in template:
                template_context = {
                    'START_DATE' : d_start,
                    'END_DATE'   : d_end,
                    'TIME_STEP'  : '%d' % (1000 * 60 * 5 * window_width)
                    }
                for k in keys:
                    template_context['%s_DATA' % k.upper()] = datastrings[k]
                r += renderer.render(line, template_context)
        return r
