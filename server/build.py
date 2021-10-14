import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import docker
from docker.errors import ImageNotFound
from gitea_api import Configuration, ApiClient, RepositoryApi, CreateStatusOption
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from server.error_handling import send_error
from server.models import Build
from server.env import Env

pool = ThreadPoolExecutor(max_workers=Env.get_int("MAX_WORKERS"))

# easily create new database sessions thread safe
engine = create_engine(Env.get("SQLALCHEMY_DATABASE_URI"))
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def _repo_api():
    gitea_configuration = Configuration()
    gitea_configuration.host = Env.get("GITEA_LOCAL_URL") + "/api/v1"
    gitea_configuration.username = Env.get("GITEA_USER")
    gitea_configuration.password = Env.get("GITEA_PASSWORD")
    gitea_api_client = ApiClient(gitea_configuration)
    return RepositoryApi(gitea_api_client)


def _build(sha: str, course: str, student: str, exercise: str = None):
    container = None
    try:
        docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')

        now = datetime.now()

        api = _repo_api()
        api.repo_create_status(owner=course, repo=student, sha=sha, body=CreateStatusOption(
            context=f"laurel/{exercise}",
            description=f"building..",
            state="pending",
        ))

        # set commit status to pending
        try:
            # network mode host so you can access the internet
            container = docker_client.containers.create(
                image=course.lower(),
                command="python3 build.py",
                detach=False,
                mem_limit="512m",
                network_mode="host",
                environment={
                    "EXERCISE": exercise if exercise else "",
                    "STUDENT": student,
                    "COURSE": course,
                    "GITEA_HOST": Env.get("GITEA_HOST"),
                    "GITEA_USER": Env.get("GITEA_USER"),
                    "GITEA_PASSWORD": Env.get("GITEA_PASSWORD"),
                    "GITEA_PROTOCOL": Env.get("GITEA_PROTOCOL"),
                    "COMMAND_TIMEOUT": Env.get("COMMAND_TIMEOUT")
                }
            )
        except ImageNotFound:
            # if image is not found just dont build, as simple as that
            return

        # run the container
        container.start()
        exit_status = container.wait()['StatusCode']

        if exit_status != 0:
            stderr = list(container.logs(stdout=True, stderr=True, stream=True, follow=True))
            raise Exception(
                f"building error ({course}, {student}, {exercise}): {''.join([line.decode('utf-8') for line in stderr])}\n")

        stdout = list(container.logs(stdout=True, stderr=False, stream=True, follow=True))
        container.remove()

        out = json.loads(''.join([line.decode('utf-8') for line in stdout]))

        # save to database, uses new session bc multithreading ukr
        session = Session()
        build = Build(
            start=now,
            end=datetime.now(),
            course=course,
            student=student,
            exercise=exercise,
            logs=json.dumps(out["steps"]),
            failure=out["failure"]
        )
        session.add(build)
        session.commit()
        build_id = build.id
        session.close()

        # set commit status in gitea accordingly
        api.repo_create_status(owner=course, repo=student, sha=sha, body=CreateStatusOption(
            context=f"laurel/{exercise}",
            description=f"build {'failed' if out['failure'] else 'succeeded'}",
            state="failure" if out["failure"] else "success",
            target_url=f"{Env.get('PUBLIC_URL')}/builds/{course}/{student}/{build_id}"
        ))
    except Exception as e:
        if container is not None:
            container.remove()
        # is inside another thread but printing actually works, yay
        print(e)
        send_error(e)
        _repo_api().repo_create_status(owner=course, repo=student, sha=sha, body=CreateStatusOption(
            context=f"laurel/{exercise}",
            description=f"build failed due to internal error",
            state="failure",
        ))


def build(course: str, student: str, exercise: str):
    docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    try:
        docker_client.images.get(course)
    except ImageNotFound:
        return

    api = _repo_api()
    sha = api.repo_get_all_commits(owner=course, repo=student, limit=1)[0].sha
    api.repo_create_status(owner=course, repo=student, sha=sha, body=CreateStatusOption(
        context=f"laurel/{exercise}",
        description=f"build queued",
        state="pending",
    ))

    pool.submit(_build, sha, course, student, exercise)
