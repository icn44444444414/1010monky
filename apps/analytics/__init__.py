"""
Analytics-modul for 1010monky-admin.

Egen Flask-blueprint for live-besokarstatistik och leads. Byggs i steg:
  Steg 1 (nu): dashboard-skalet (paneler + diagram) med demodata.
  Senare: VisitorSession/VisitorEvent/Lead-modeller, event-API, lead score,
  live-vy och mini-CRM (se roadmap i minnet). Allt bakom cookie-samtycke.
"""
from flask import Blueprint

blueprint = Blueprint(
    'analytics_blueprint',
    __name__,
    template_folder='../templates',
    url_prefix=''
)
