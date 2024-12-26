# main.py
from cdk8s import App
from charts.backend import BackendChart
from charts.frontend import FrontendChart
from charts.ingress import IngressChart
from charts.static_infra import StaticInfraChart
import os

if __name__ == "__main__":
    print("Starting CDK8s synthesis...")
    print("Environment variables:")
    print(f"ECR_REGISTRY_FRONTEND: {os.environ.get('ECR_REGISTRY_FRONTEND')}")
    print(f"ECR_REGISTRY_BACKEND: {os.environ.get('ECR_REGISTRY_BACKEND')}")
    print(f"IMAGE_TAG: {os.environ.get('IMAGE_TAG')}")

    app = App()
    StaticInfraChart(app, "static-infra")
    BackendChart(app, "backend")
    FrontendChart(app, "frontend")
    IngressChart(app, "ingress")
    app.synth()
