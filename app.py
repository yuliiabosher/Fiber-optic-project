import os
import json
from flask import (
    Flask,
    render_template,
    url_for,
    request,
    flash,
    redirect,
    jsonify,
    make_response,
    Response,
    abort,
    after_this_request,
    render_template_string,
)
from markupsafe import Markup
from datetime import datetime, timezone
import folium
from branca.element import MacroElement
from files.backend import Backend

environment = os.getenv("FLASK_ENV", "development")
application = Flask(__name__, template_folder="templates", static_folder="static")

bkd = Backend()

visuals = dict(
    # dual_RUC_map = bkd.make_RUC_dualmap(),
    # fibre_distribution_uk_slider = bkd.make_map_of_fibre_distribution_uk(),
    eu_fttp_slider=bkd.make_eu_fftp_availability_map(),
    eu_fttp_predictions_slider=bkd.make_eu_fftp_availability_predictions_map(),
    # graphs = bkd.graphs
)


###############
# API Helpers
###############
def build_success(data):
    if not "ts" in data.keys():
        data["ts"] = datetime.now(timezone.utc).isoformat()
    return Response(json.dumps(data), mimetype="application/json", status=200)


def build_error(message, status_code):
    error = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "message": message,
    }
    return Response(json.dumps(error), mimetype="application/json", status=status_code)


###############
#     HEALTH CHECK      #
###############
@application.route("/hc")
def health_check():
    return Response("{}", status=200)


################
# 	   DASHBOARD	   #
################
@application.route("/")
def index():
    return render_template("index.html", **visuals)


@application.route("/test")
def test():
    return render_template("index.html", **visuals)


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8000, debug=True)
