"""
Serverar Gentelella-adminpanelen som statiskt bygge pa /admin - utan losenord.

Den gamla chatt-/analytics-adminen togs bort 2026-06-29. Det har ar bara en
ren statisk servering av admin/dist (Gentelella v4, byggt med BASE_PATH=/admin/),
helt med sin egen stil. Inget ar integrerat mot sidans data.

Bygg om panelen sa har (fran projektroten):
  cd admin
  NODE_ENV=production BASE_PATH=/admin/ npx vite build

Startsidan /admin -> /admin/production/index.html (Gentelellas dashboard).
Alla tillgangar (/admin/js, /admin/assets, /admin/images ...) ligger i dist-roten.
Push-routesen (/admin/push, /admin/install, /admin/sw.js ...) ar mer specifika
och tar fortfarande sina egna anrop; resten faller hit till de statiska filerna.
"""
import os

from flask import Blueprint, send_from_directory, redirect, abort

blueprint = Blueprint('adminpanel_blueprint', __name__, url_prefix='')

# .../1010monky/admin/dist  (tre niverar upp fran apps/adminpanel/routes.py)
_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'admin', 'dist',
)


@blueprint.route('/admin')
@blueprint.route('/admin/')
def admin_index():
    return redirect('/admin/production/index.html')


@blueprint.route('/admin/<path:filename>')
def admin_static(filename):
    full = os.path.normpath(os.path.join(_DIST, filename))
    # Skydd mot path traversal + 404 for saknade filer.
    if not full.startswith(os.path.normpath(_DIST)) or not os.path.isfile(full):
        abort(404)
    return send_from_directory(_DIST, filename)
