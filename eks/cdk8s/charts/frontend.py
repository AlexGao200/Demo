# charts/frontend.py
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


class FrontendChart(Chart):
    """
    Chart for frontend deployment and service.
    Handles the React frontend application deployment and its associated service.
    """

    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        self.validate_env_vars()
        self._create_frontend_resources()

    def validate_env_vars(self):
        """Validate required environment variables"""
        self.ecr_registry = os.environ.get("ECR_REGISTRY_FRONTEND")
        self.image_tag = os.environ.get("IMAGE_TAG")
        self.use_latest = os.environ.get("USE_LATEST", "false").lower() == "true"

        if not self.ecr_registry or not self.image_tag:
            raise ValueError(
                f"Missing required environment variables. Got: "
                f"ECR_REGISTRY_FRONTEND='{self.ecr_registry}', "
                f"IMAGE_TAG='{self.image_tag}'"
            )

        # Log configuration for debugging
        print(f"Frontend Chart - ECR_REGISTRY_FRONTEND: {self.ecr_registry}")
        print(f"Frontend Chart - IMAGE_TAG: {self.image_tag}")
        print(f"Frontend Chart - USE_LATEST: {self.use_latest}")

    def _create_deployment(self):
        """Create frontend deployment"""
        actual_tag = "latest" if self.use_latest else self.image_tag

        return KubeDeployment(
            self,
            "frontend-deployment",
            metadata={"name": "frontend-deployment"},
            spec=DeploymentSpec(
                replicas=2,
                selector={"match_labels": {"app": "frontend"}},
                template=PodTemplateSpec(
                    metadata={"labels": {"app": "frontend"}},
                    spec=PodSpec(
                        containers=[
                            Container(
                                name="frontend",
                                image=f"{self.ecr_registry}:{actual_tag}",
                                image_pull_policy="Always"
                                if self.use_latest
                                else "IfNotPresent",
                                ports=[ContainerPort(container_port=80)],
                                env_from=[
                                    {"configMapRef": {"name": "app-config"}},
                                ],
                            )
                        ]
                    ),
                ),
            ),
        )

    def _create_service(self):
        """Create frontend service"""
        return KubeService(
            self,
            "frontend-service",
            metadata={"name": "frontend-service"},
            spec={
                "selector": {"app": "frontend"},
                "ports": [{"port": 80, "targetPort": IntOrString.from_number(80)}],
                "type": "ClusterIP",
            },
        )

    def _create_frontend_resources(self):
        """Create all frontend-related resources"""
        self._create_deployment()
        self._create_service()
