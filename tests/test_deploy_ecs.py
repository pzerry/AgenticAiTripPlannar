import unittest
from unittest.mock import patch

from scripts import deploy_ecs as deploy


class DeploymentTests(unittest.TestCase):
    def test_revision_preserves_settings_and_only_updates_app_image(self):
        original = {"family": "api", "taskDefinitionArn": "old", "revision": 1,
                    "containerDefinitions": [{"name": "app", "image": "old", "secrets": [{"name": "DATABASE_URL", "valueFrom": "secret"}]},
                                             {"name": "sidecar", "image": "sidecar"}]}
        result = deploy.revision(original, "new@sha256:123")
        self.assertNotIn("revision", result)
        self.assertNotIn("taskDefinitionArn", result)
        self.assertEqual(result["containerDefinitions"][0]["image"], "new@sha256:123")
        self.assertEqual(result["containerDefinitions"][0]["secrets"], original["containerDefinitions"][0]["secrets"])
        self.assertEqual(result["containerDefinitions"][1]["image"], "sidecar")
        self.assertEqual(original["containerDefinitions"][0]["image"], "old")

    def test_stable_but_rolled_back_service_is_failure(self):
        with patch.object(deploy, "aws"), patch.object(deploy, "describe_services", return_value=[
                {"taskDefinition": "previous", "runningCount": 1} ]):
            with self.assertRaises(RuntimeError):
                deploy.verify_service("cluster", "api", "requested")

    def test_migration_task_nonzero_exit_is_failure(self):
        with patch.object(deploy, "aws", side_effect=[
            {"tasks": [{"taskArn": "migration"}]},
            {"tasks": [{"lastStatus": "STOPPED", "containers": [{"name": "app", "exitCode": 1}]}]},
        ]):
            with self.assertRaisesRegex(RuntimeError, "Migration failed"):
                deploy.migrate("cluster", {"networkConfiguration": {}}, "revision")

    def test_migration_timeout_stops_task(self):
        def fake(*args):
            if args[1] == "run-task":
                return {"tasks": [{"taskArn": "migration"}]}
            return {"tasks": [{"lastStatus": "RUNNING"}]}
        with patch.object(deploy, "aws", side_effect=fake) as api, patch.object(deploy.time, "sleep"):
            with self.assertRaises(TimeoutError):
                deploy.migrate("cluster", {"networkConfiguration": {}}, "revision")
            self.assertEqual(api.call_args.args[1], "stop-task")

    def run_main(self, *, migration_error=None, rollout_error=None):
        env = {"ECS_CLUSTER": "cluster", "DEPLOY_IMAGE": "ecr@sha256:123",
               "ECS_API_SERVICE": "api", "ECS_WORKER_SERVICE": "worker", "ECS_UI_SERVICE": "ui"}
        old = [{"serviceName": name, "taskDefinition": name + ":1", "desiredCount": 1}
               for name in ("api", "worker", "ui")]
        def fake(*args):
            if args[1] == "describe-task-definition":
                return {"taskDefinition": {"containerDefinitions": [{"name": "app"}]}}
            if args[1] == "register-task-definition":
                return {"taskDefinition": {"taskDefinitionArn": "new:2"}}
            return {}
        with patch.dict(deploy.os.environ, env), patch.object(deploy, "describe_services", return_value=old), \
             patch.object(deploy, "aws", side_effect=fake) as api, \
             patch.object(deploy, "migrate", side_effect=migration_error), \
             patch.object(deploy, "verify_service", side_effect=rollout_error):
            with self.assertRaises(RuntimeError):
                deploy.main()
            return [call.args for call in api.call_args_list if call.args[1] == "update-service"]

    def test_failed_migration_never_updates_services(self):
        self.assertEqual(self.run_main(migration_error=RuntimeError("migration")), [])

    def test_failed_rollout_requests_previous_service_revision(self):
        updates = self.run_main(rollout_error=RuntimeError("rollout"))
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[-1][updates[-1].index("--task-definition") + 1], "api:1")
