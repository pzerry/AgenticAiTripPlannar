"""Promote an image digest to ECS after a successful one-off migration task."""
import copy
import json
import os
import subprocess
import time
import urllib.request


def aws(*args):
    result = subprocess.run(["aws", *args, "--output", "json"], check=True,
                            capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def describe_services(cluster, names):
    result = aws("ecs", "describe-services", "--cluster", cluster, "--services", *names)
    if result.get("failures") or len(result.get("services", [])) != len(names):
        raise RuntimeError("ECS services are missing or inaccessible")
    return result["services"]


def revision(definition, image):
    # Only fields accepted by RegisterTaskDefinition; strip read-only response metadata.
    fields = {"family", "taskRoleArn", "executionRoleArn", "networkMode", "containerDefinitions",
              "volumes", "placementConstraints", "requiresCompatibilities", "cpu", "memory",
              "pidMode", "ipcMode", "proxyConfiguration", "inferenceAccelerators",
              "ephemeralStorage", "runtimePlatform", "enableFaultInjection"}
    result = {key: copy.deepcopy(value) for key, value in definition.items() if key in fields}
    containers = [item for item in result["containerDefinitions"] if item["name"] == "app"]
    if len(containers) != 1:
        raise RuntimeError("Task definition must contain exactly one app container")
    containers[0]["image"] = image
    return result


def migrate(cluster, service, task_definition):
    result = aws("ecs", "run-task", "--cluster", cluster, "--launch-type", "FARGATE",
                 "--platform-version", "1.4.0", "--task-definition", task_definition,
                 "--network-configuration", json.dumps(service["networkConfiguration"]),
                 "--overrides", json.dumps({"containerOverrides": [{"name": "app",
                     "command": ["python", "-m", "Backend.Memory.migrate"]}]}))
    if result.get("failures") or len(result.get("tasks", [])) != 1:
        raise RuntimeError("Migration task could not start")
    task = result["tasks"][0]["taskArn"]
    stopped = False
    try:
        for _ in range(60):
            detail = aws("ecs", "describe-tasks", "--cluster", cluster, "--tasks", task)
            if detail.get("failures") or not detail.get("tasks"):
                raise RuntimeError("Migration task is inaccessible")
            current = detail["tasks"][0]
            if current["lastStatus"] == "STOPPED":
                stopped = True
                containers = current.get("containers", [])
                app = [c for c in containers if c["name"] == "app"]
                if len(app) != 1 or app[0].get("exitCode") != 0:
                    raise RuntimeError("Migration failed; inspect the API CloudWatch log stream")
                return
            time.sleep(10)
        raise TimeoutError("Migration exceeded 10 minutes")
    finally:
        if not stopped:
            aws("ecs", "stop-task", "--cluster", cluster, "--task", task,
                "--reason", "Migration deployment check failed or timed out")


def verify_service(cluster, name, expected):
    aws("ecs", "wait", "services-stable", "--cluster", cluster, "--services", name)
    service = describe_services(cluster, [name])[0]
    if service["taskDefinition"] != expected or service["runningCount"] < 1:
        raise RuntimeError(f"{name} did not deploy the requested revision (possibly rolled back)")
    deployments = service.get("deployments", [])
    if len(deployments) != 1 or deployments[0].get("rolloutState") != "COMPLETED":
        raise RuntimeError(f"{name} rollout is incomplete")


def health(url):
    if not url.startswith("https://"):
        raise ValueError("Deployment health URLs must use HTTPS")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                if response.status == 200:
                    return
        except (OSError, ValueError):
            pass
        if attempt < 5:
            time.sleep(10)
    raise RuntimeError("Public HTTPS health check failed")


def main():
    cluster = os.environ["ECS_CLUSTER"]
    names = [os.environ[f"ECS_{kind}_SERVICE"] for kind in ("API", "WORKER", "UI")]
    image = os.environ["DEPLOY_IMAGE"]
    if "@sha256:" not in image:
        raise ValueError("Deploy an immutable ECR image digest")
    old = {s["serviceName"]: s for s in describe_services(cluster, names)}
    new = {}
    for name in names:
        definition = aws("ecs", "describe-task-definition",
                         "--task-definition", old[name]["taskDefinition"].rsplit(":", 1)[0])["taskDefinition"]
        registered = aws("ecs", "register-task-definition", "--cli-input-json",
                         json.dumps(revision(definition, image)))
        new[name] = registered["taskDefinition"]["taskDefinitionArn"]
    migrate(cluster, old[names[0]], new[names[0]])
    changed = []
    try:
        for name in names:
            changed.append(name)
            aws("ecs", "update-service", "--cluster", cluster, "--service", name,
                "--task-definition", new[name], "--desired-count", str(max(1, old[name]["desiredCount"])))
            verify_service(cluster, name, new[name])
        health(os.environ["API_HEALTH_URL"])
        health(os.environ["UI_HEALTH_URL"])
    except Exception:
        # Restore every changed service. Schema rollback is deliberately not automatic.
        for name in reversed(changed):
            try:
                aws("ecs", "update-service", "--cluster", cluster, "--service", name,
                    "--task-definition", old[name]["taskDefinition"],
                    "--desired-count", str(old[name]["desiredCount"]))
            except Exception:
                print(f"Automatic restore failed for {name}; restore the previous revision manually.")
        raise
    print(f"Deployed {image}; all three services and HTTPS health checks passed.")


if __name__ == "__main__":
    main()
