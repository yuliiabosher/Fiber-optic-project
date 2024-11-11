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
from datetime import datetime, timezone
import folium
from files.backend import Backend

environment = os.getenv("FLASK_ENV", "development")
application = Flask(__name__, template_folder="templates", static_folder="static")

#bkd = Backend()

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


@application.route("/index")
def index():

    m = folium.Map(
        location=[54.7023545, -3.2765753],
        zoom_start=6,
        tiles="Cartodb Positron",
        height=800,
        width=500,
    )
    for n, choropleth_data in enumerate(bkd.choropleth_data):

        if choropleth_data:
            choropleth = choropleth_data[0]
            choropleth.add_to(m)

    folium.TileLayer(tiles="Cartodb dark_matter", name="dark").add_to(m)
    folium.LayerControl().add_to(m)
    m.get_root().width = "500px"
    m.get_root().height = "800px"
    body_html = m.get_root()._repr_html_()

    m2 = folium.Map(
        location=[54.7023545, -3.2765753], zoom_start=6, height=800, width=500
    )
    choropleth_with_slider = bkd.get_choropleth_for_full_fibre_availability_with_slider(
        bkd.choropleth_data
    )
    choropleth_with_slider.add_to(m2)

    m2.get_root().width = "500px"
    m2.get_root().height = "800px"
    body_html2 = m2.get_root()._repr_html_()

    return render_template(
        "index.html", body_html=body_html, body_html2=body_html2, graphs=bkd.graphs
    )


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=80, debug=True)
