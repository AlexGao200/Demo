# charts/backend.py
from constructs import Construct
from cdk8s import Chart
from imports.k8s import (
    KubeDeployment,
    KubeService,
    DeploymentSpec,
    PodTemplateSpec,
    PodSpec,
    Container,
    ContainerPort,
    IntOrString,
)
import os


class BackendChart(Chart):
    """
    Chart for backend deployment and service.
    Handles the Flask backend application deployment and its associated service.
    """

    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        self.validate_env_vars()
        self._create_backend_resources()

    def validate_env_vars(self):
        """Validate required environment variables"""
        self.ecr_registry = os.environ.get("ECR_REGISTRY_BACKEND")
        self.image_tag = os.environ.get("IMAGE_TAG")
        self.use_latest = os.environ.get("USE_LATEST", "false").lower() == "true"

        if not self.ecr_registry or not self.image_tag:
            raise ValueError(
                f"Missing required environment variables. Got: "
                f"ECR_REGISTRY_BACKEND='{self.ecr_registry}', "
                f"IMAGE_TAG='{self.image_tag}'"
            )

        # Log configuration for debugging
        print(f"Backend Chart - ECR_REGISTRY_BACKEND: {self.ecr_registry}")
        print(f"Backend Chart - IMAGE_TAG: {self.image_tag}")
        print(f"Backend Chart - USE_LATEST: {self.use_latest}")

    def _get_env_sources(self):
        """Get environment sources for backend container"""
        return [
            {"configMapRef": {"name": "app-config"}},
            {"secretRef": {"name": "app-secrets"}},
            {"secretRef": {"name": "api-keys-secret"}},
            {"secretRef": {"name": "email-secrets"}},
            {"secretRef": {"name": "elasticsearch-secrets"}},
        ]

    def _create_deployment(self):
        """Create backend deployment"""
        actual_tag = "latest" if self.use_latest else self.image_tag

        return KubeDeployment(
            self,
            "backend-deployment",
            metadata={"name": "backend-deployment"},
            spec=DeploymentSpec(
                replicas=2,
                selector={"match_labels": {"app": "backend"}},
                template=PodTemplateSpec(
                    metadata={"labels": {"app": "backend"}},
                    spec=PodSpec(
                        service_account_name="backend-service-account",
                        containers=[
                            Container(
                                name="backend",
                                image=f"{self.ecr_registry}:{actual_tag}",
                                image_pull_policy="Always"
                                if self.use_latest
                                else "IfNotPresent",
                                ports=[ContainerPort(container_port=5000)],
                                env_from=self._get_env_sources(),
                            )
                        ]
                    ),
                ),
            ),
        )

    def _create_service(self):
        """Create backend service"""
        return KubeService(
            self,
            "backend-service",
            metadata={"name": "backend-service"},
            spec={
                "selector": {"app": "backend"},
                "ports": [{"port": 5000, "targetPort": IntOrString.from_number(5000)}],
                "type": "ClusterIP",
            },
        )

    def _create_backend_resources(self):
        """Create all backend-related resources"""
        self._create_deployment()
        self._create_service()


# utils/constants.py (optional, for shared constants)
class DeploymentConfig:
    """Shared configuration constants"""

    FRONTEND_PORT = 80
    BACKEND_PORT = 5000
    DEFAULT_REPLICAS = 1
    DEPLOYMENT_LABELS = {"app": "frontend"}  # or "backend"
