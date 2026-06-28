"""
Chat-modul for 1010monky.

Egen Flask-blueprint som hanterar besokschatt: konversationer, meddelanden,
publikt API och admin-vy. Byggs backend-first (modeller + admin innan widget).
Ingen AI och ingen extern chatt-tjanst - allt sparas i projektets egen databas.

Inkoppling: 'chat' laggs till i apps-tupeln i apps/__init__.py, varpa
registreringsloopen importerar apps.chat.routes och registrerar detta blueprint.
"""
from flask import Blueprint

blueprint = Blueprint(
    'chat_blueprint',
    __name__,
    template_folder='../templates',
    url_prefix=''
)
