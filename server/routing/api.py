from flask import Blueprint, jsonify

import server.build
from server.models import Build
from server.routing.decorators import admin_route

api_bp = Blueprint("api", __name__)


@api_bp.route("/build/<course>/<student>/<exercise>")
@admin_route
def build(course, student, exercise=None):
    server.build.build(course, student, exercise)
    return "", 200


@api_bp.route("/logs/<course>/<student>/<exercise>")
@admin_route
def logs(course, student, exercise):
    builds = Build.query.many(course=course, student=student, exercise=exercise)
    if not builds:
        return "no logs found", 404
    latest = sorted(builds, key=lambda b: b.end, reverse=True)[0]
    return jsonify(latest.to_dict()), 200
