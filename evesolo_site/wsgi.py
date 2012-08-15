import os
import sys

os.environ['DJANGO_SETTINGS_MODULE']='evesolo_site.settings'
path = 'c:\web\www\evesolo_com'
if path not in sys.path:
    sys.path.append(path)
path = 'c:\web\www\evesolo_com\evesolo_site'
if path not in sys.path:
    sys.path.append(path)

for p in sys.path:
	print >> sys.stderr, 'path element: %s ' % repr(p)

print >> sys.stderr, 'prefix element: %s ' % repr(sys.prefix)

import django.core.handlers.wsgi
application=django.core.handlers.wsgi.WSGIHandler()