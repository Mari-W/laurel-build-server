import requests
from flask import Blueprint, session, render_template

from server.env import Env
from server.models import Build
from server.routing.decorators import authorized_route

builds_bp = Blueprint("builds", __name__)


def is_tutor(course: str, username: str):
    return requests.get(f"{Env.get('COURSES_API_URL')}/course/{course}/is_tutor/{username}",
                        headers={"Authorization": Env.get("COURSES_API_KEY")}).status_code == 200


@builds_bp.route('/<course>/')
@authorized_route
def builds_course(course):
    user = session.get("user")
    admin = user["role"] == "admin"
    tutor = False
    if not admin:
        if not is_tutor(course, user["sub"]):
            return "unauthorized", 403
        tutor = True

    return render_template("builds.html", admin=admin, tutor=tutor, course=course, student=None,
                           builds=Build.query.many(course=course))


@builds_bp.route('/')
@authorized_route
def builds():
    user = session.get("user")
    if user["role"] != "admin":
        return "unauthorized", 403
    return render_template("builds.html", admin=True, tutor=False, course=None, student=None,
                           builds=Build.query.all())


@builds_bp.route('/<course>/<student>')
@authorized_route
def builds_student(course, student):
    user = session.get("user")
    admin = user["role"] == "admin"
    tutor = False
    if not admin and user["sub"] != student:
        if not is_tutor(course, user["sub"]):
            return "unauthorized", 403
        tutor = True
    return render_template("builds.html", admin=admin, tutor=tutor, course=course, student=student,
                           builds=Build.query.many(course=course, student=student))


@builds_bp.route('/<course>/<student>/<id>')
@authorized_route
def build(course, student, id):
    user = session.get("user")
    admin = user["role"] == "admin"
    tutor = False
    if not admin and user["sub"] != student:
        if not is_tutor(course, user["sub"]):
            return "unauthorized", 403
        tutor = True

    try:
        id = int(id)
    except ValueError:
        return "invalid build id", 404

    build = Build.query.one(id=id)
    if build.course != course:
        return f"id does not belong to {course}", 404
    if build.student != student:
        return f"id does not belong to {student}"

    return render_template("build.html", admin=admin, tutor=tutor, course=build.course, student=build.student,
                           build=build)
