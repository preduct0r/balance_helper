from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DockerArtifactsTests(unittest.TestCase):
    def test_dockerfile_runs_web_command_with_persistent_paths(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:", dockerfile)
        self.assertIn("requirements.txt", dockerfile)
        self.assertIn("BALANCE_STORE_PATH=/app/data/local_store.json", dockerfile)
        self.assertIn("BALANCE_LOG_FILE=/app/logs/app.jsonl", dockerfile)
        self.assertIn("balance_fundraising.cli", dockerfile)
        self.assertIn("--host", dockerfile)
        self.assertIn("0.0.0.0", dockerfile)

    def test_compose_persists_logs_and_data_on_host(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("./logs:/app/logs", compose)
        self.assertIn("./data:/app/data", compose)
        self.assertIn("BALANCE_LOG_FILE=/app/logs/app.jsonl", compose)
        self.assertIn("BALANCE_STORE_PATH=/app/data/local_store.json", compose)
        self.assertIn("8080:8080", compose)
        self.assertIn("YANDEX_API_KEY=${YANDEX_API_KEY:-}", compose)
        self.assertIn("YANDEX_FOLDER_ID=${YANDEX_FOLDER_ID:-}", compose)

    def test_gitignore_keeps_env_out_of_commits(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", gitignore)

    def test_dockerignore_keeps_runtime_state_out_of_image(self) -> None:
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".git", dockerignore)
        self.assertIn(".env", dockerignore)
        self.assertIn("logs/", dockerignore)
        self.assertIn("data/", dockerignore)

    def test_harness_tracks_docker_runtime_feature(self) -> None:
        features = json.loads((ROOT / "docs/feature-list.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in features}
        self.assertIn("docker-persistent-runtime", by_id)
        self.assertTrue(by_id["docker-persistent-runtime"]["passes"])


if __name__ == "__main__":
    unittest.main()
