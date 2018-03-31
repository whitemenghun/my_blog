from flask import Blueprint

main = Blueprint('main', __name__, template_folder='/app/templates')

from . import views, errors


