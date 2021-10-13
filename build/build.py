import json
import os
import subprocess
from dataclasses import dataclass, asdict


@dataclass
class Step:
    name: str
    logs: list
    failure: bool


@dataclass
class Build:
    steps: list
    failure: bool


build = Build(steps=[], failure=False)


def get_command_timeout():
    try:
        if "COMMAND_TIMEOUT" not in os.environ:
            return 300
        return int(os.environ["COMMAND_TIMEOUT"])
    except ValueError:
        return 300


def let_build_fail(step_name=None, error=None):
    if step_name is not None:
        build.steps.append(Step(name=step_name, logs=[error], failure=True))
    build.failure = True
    print(json.dumps(asdict(build)))
    exit(0)


def execute_step(name, step):
    if type(name) is not str:
        let_build_fail(step_name=name, error=f"{name} is a valid step name, must be string")

    if type(step) is not dict:
        let_build_fail(step_name=name, error=f"step {name} is not a dictionary")

    if "commands" not in step:
        let_build_fail(step_name=name, error=f"no 'commands' field found in {step}")

    if type(step["commands"]) is not list:
        let_build_fail(step_name=name, error=f"'commands' field in {step} is not a list")

    s = Step(name=name, logs=[], failure=False)

    for command in step["commands"]:
        process = None
        timed_out = False
        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=get_command_timeout(),
                universal_newlines=True,
                env=os.environ,
                shell=True
            )
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout
            stderr = e.stderr
            timed_out = True

        s.logs.append(command)

        if stdout is not None:
            s.logs.extend(stdout.split("\n"))

        s.failure = process is None or process.returncode != 0

        if s.failure:
            if stderr is not None:
                s.logs.extend(stderr.split("\n"))
            if timed_out:
                s.logs.append(f"command took longer than {str(get_command_timeout())} seconds, timed out.")
            build.steps.append(s)
            build.failure = True
            return

    build.steps.append(s)

    if "children" in step:
        if type(step["children"]) is not dict:
            let_build_fail(step_name=name, error=f"'children is not a dictionary in {step}")

        for child, child_step in step["children"].items():
            execute_step(child, child_step)


try:
    with open("/build.json") as f:
        build_json = json.load(f)
        if type(build_json) is not dict:
            let_build_fail(step_name="build-pre-initialize", error="build.json is not a dictionary")

        for name, step in build_json.items():
            execute_step(name, step)

        print(json.dumps(asdict(build)))

        exit(0)
except Exception as e:
    let_build_fail(step_name="build-internal", error=f"{e}")
