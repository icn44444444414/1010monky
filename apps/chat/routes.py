"""
Publika routes/API for chatten.

Milestone 1: enbart en halso-route sa vi kan verifiera att blueprintet ar
inkopplat. De riktiga API-endpoints (/api/chat/start, /api/chat/message,
/api/chat/messages/<id>) byggs i Milestone 4.

Den har modulen ar ocksa "samlingspunkten": den importerar models (sa att
db.create_all() hittar tabellerna) och admin_routes (sa att admin-routarna
registreras pa samma blueprint). Registreringsloopen i apps/__init__.py
importerar just denna modul och plockar 'blueprint'.
"""
from apps.chat import blueprint
from apps.chat import models  # noqa: F401  (sakerstaller att modeller laddas)
from apps.chat import admin_routes  # noqa: F401  (registrerar admin-routes)
from flask import jsonify


@blueprint.route('/api/chat/ping')
def chat_ping():
    # Tillfallig halsokoll for att bekrafta inkoppling. Tas bort i M4.
    return jsonify(ok=True, area='chat', milestone=1)
