import unittest
from pathlib import Path


class NodeDeployDockerfileTests(unittest.TestCase):
    def test_node_dockerfile_supports_lockfile_and_fallback_install(self):
        dockerfile = Path("templates/nodeJS.Dockerfile").read_text()

        self.assertIn("package-lock.json", dockerfile)
        self.assertIn("npm ci", dockerfile)
        self.assertIn("npm install", dockerfile)


if __name__ == "__main__":
    unittest.main()
