MeteoPyris
==========

Small python package to download, store and plot data from http://meteo-paris.com

For now, only a simple Manager class is provided, that can be used as follow:

```
import MeteoPyris

m = MeteoPyris.Manager()
m.reinit_table()
m.update_database()

html = m.render_template('fr_template.html').encode('utf-8')

with open('render.html', 'w') as h:
    h.write(html)
```

This will initalized a sqlite database in ~/.meteo.db,
populate it by retrieving online info at http://meteo-paris.com
and finally render the sample template.
Obviously, the initialisation is to be done only once.

The sample template 'fr_template.html' is into the example
folder and requires the pystache template engine.

A live page is available at http://oknaj.eu/temp/

Hopefuly, updates, doc and installer are coming soon.

This software is distributed under the Modified BSD License
