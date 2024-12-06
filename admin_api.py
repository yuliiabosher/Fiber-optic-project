import subprocess
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
from flask_basicauth import BasicAuth
from datetime import datetime, timezone
from threading import Thread
from time import sleep

environment = os.getenv("FLASK_ENV", "development")
application = Flask(__name__, template_folder="templates", static_folder="static")
application.config["BASIC_AUTH_USERNAME"] = "admin"
application.config["BASIC_AUTH_PASSWORD"] = "LyNx2017@chaozhou"
basic_auth = BasicAuth(application)

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

def execute(commands:list) -> bool:
    sleep(20)
    for command in commands:
        os.system(command)
    return True
    
###############
#     HEALTH CHECK      #
###############
@application.route("/admin/hc")
@basic_auth.required
def health_check():
    try:
        memory = subprocess.check_output("free -h".split()).decode("utf-8").rstrip().split()
        metrics = dict(
            battery_status = subprocess.check_output("cat /sys/class/power_supply/BAT0/status".split()).decode("utf-8").rstrip(),
            memory= {k:v for k,v in zip(memory[:6],memory[7:13])},
            uptime=subprocess.check_output("uptime".split()).decode("utf-8").rstrip(),
        )
    except Exception as e:
         return build_error("Could not return metrics %s"%e)
    return build_success(metrics)

@application.route("/admin/control_panel/<string:command>")
@basic_auth.required
def control_panel(command):
    commands = []
    if command.lower() == "restart":
        #restart service
        commands.append("fuser -kn tcp 8000")
        commands.append("bash ~/.profile")
    elif command.lower() == "reboot":
        #reboot computer
        commands.append("reboot")
    elif command.lower() == "terminate":
        #kill flask process
        commands.append("fuser -kn tcp 8000")
    Thread(target=execute, args=[commands]).start()
    return build_success({"msg":"Commands Registered", "commands":commands})
    
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5001, debug=True)
