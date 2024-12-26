# charts/static_infra.py
from constructs import Construct
from cdk8s import Chart
from imports.k8s import (
    KubeDeployment,
    KubeService,
    KubePersistentVolumeClaim,
    PersistentVolumeClaimSpec,
    DeploymentSpec,
    PodTemplateSpec,
    PodSpec,
    Container,
    ContainerPort,
    Volume,
    VolumeMount,
    EnvVar,
    EnvVarSource,
    SecretKeySelector,
    ResourceRequirements,
    Quantity,
    PersistentVolumeClaimVolumeSource,
    SecretVolumeSource,
    SecurityContext,
    PodSecurityContext,
    IntOrString,
)


class StaticInfraChart(Chart):
    """
    Chart for static infrastructure components including Elasticsearch
    """

    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        self._create_elasticsearch_infrastructure()

    def _create_persistent_volume_claim(self):
        """Create PVC for Elasticsearch data"""
        return KubePersistentVolumeClaim(
            self,
            "elasticsearch-pvc",
            metadata={
                "name": "elasticsearch-pvc",
                "annotations": {
                    "helm.sh/resource-policy": "keep"  # Prevents accidental deletion
                },
            },
            spec=PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources={"requests": {"storage": Quantity.from_string("10Gi")}},
                storage_class_name="ebs-sc",
            ),
        )

    def _get_elasticsearch_env_vars(self):
        """Define Elasticsearch environment variables"""
        return [
            # Basic configuration
            EnvVar(name="discovery.type", value="single-node"),
            EnvVar(name="xpack.security.enabled", value="true"),
            EnvVar(name="bootstrap.memory_lock", value="true"),
            EnvVar(name="ES_JAVA_OPTS", value="-Xms512m -Xmx512m"),
            # SSL/TLS configuration
            EnvVar(name="xpack.security.http.ssl.enabled", value="true"),
            EnvVar(
                name="xpack.security.http.ssl.key",
                value="/usr/share/elasticsearch/config/certs/tls.key",
            ),
            EnvVar(
                name="xpack.security.http.ssl.certificate",
                value="/usr/share/elasticsearch/config/certs/tls.crt",
            ),
            EnvVar(
                name="xpack.security.http.ssl.certificate_authorities",
                value="/usr/share/elasticsearch/config/certs/ca.crt",
            ),
            # Transport layer security
            EnvVar(name="xpack.security.transport.ssl.enabled", value="true"),
            EnvVar(
                name="xpack.security.transport.ssl.verification_mode",
                value="certificate",
            ),
            EnvVar(
                name="xpack.security.transport.ssl.key",
                value="/usr/share/elasticsearch/config/certs/tls.key",
            ),
            EnvVar(
                name="xpack.security.transport.ssl.certificate",
                value="/usr/share/elasticsearch/config/certs/tls.crt",
            ),
            EnvVar(
                name="xpack.security.transport.ssl.certificate_authorities",
                value="/usr/share/elasticsearch/config/certs/ca.crt",
            ),
            # Credentials from secrets
            EnvVar(
                name="ELASTIC_PASSWORD",
                value_from=EnvVarSource(
                    secret_key_ref=SecretKeySelector(
                        name="elasticsearch-secrets",
                        key="ELASTICSEARCH_PASSWORD",
                    )
                ),
            ),
            EnvVar(
                name="ELASTIC_USERNAME",
                value_from=EnvVarSource(
                    secret_key_ref=SecretKeySelector(
                        name="elasticsearch-secrets",
                        key="ELASTICSEARCH_USER",
                    )
                ),
            ),
        ]

    def _get_elasticsearch_volumes(self):
        """Define volumes for Elasticsearch"""
        return [
            Volume(
                name="elasticsearch-data",
                persistent_volume_claim=PersistentVolumeClaimVolumeSource(
                    claim_name="elasticsearch-pvc"
                ),
            ),
            Volume(
                name="elasticsearch-certs",
                secret=SecretVolumeSource(
                    secret_name="elasticsearch-certs",
                    default_mode=0o400,
                ),
            ),
        ]

    def _get_elasticsearch_volume_mounts(self):
        """Define volume mounts for Elasticsearch"""
        return [
            VolumeMount(
                name="elasticsearch-data",
                mount_path="/usr/share/elasticsearch/data",
            ),
            VolumeMount(
                name="elasticsearch-certs",
                mount_path="/usr/share/elasticsearch/config/certs",
                read_only=True,
            ),
        ]

    def _create_init_container(self):
        """Create init container for permissions setup"""
        return Container(
            name="fix-permissions",
            image="busybox",
            command=[
                "sh",
                "-c",
                "chown -R 1000:1000 /usr/share/elasticsearch/data",
            ],
            security_context=SecurityContext(
                run_as_user=0,
                run_as_group=0,
            ),
            volume_mounts=[
                VolumeMount(
                    name="elasticsearch-data",
                    mount_path="/usr/share/elasticsearch/data",
                ),
            ],
        )

    def _create_elasticsearch_container(self):
        """Create main Elasticsearch container"""
        return Container(
            name="elasticsearch",
            image="docker.elastic.co/elasticsearch/elasticsearch:8.11.0",
            ports=[ContainerPort(container_port=9200, name="http")],
            env=self._get_elasticsearch_env_vars(),
            resources=ResourceRequirements(
                requests={
                    "cpu": Quantity.from_string("250m"),
                    "memory": Quantity.from_string("1Gi"),
                },
                limits={
                    "cpu": Quantity.from_string("1000m"),
                    "memory": Quantity.from_string("2Gi"),
                },
            ),
            volume_mounts=self._get_elasticsearch_volume_mounts(),
        )

    def _create_elasticsearch_deployment(self):
        """Create Elasticsearch deployment"""
        return KubeDeployment(
            self,
            "elasticsearch",
            metadata={"name": "elasticsearch-deployment"},
            spec=DeploymentSpec(
                replicas=1,
                selector={"match_labels": {"app": "elasticsearch"}},
                template=PodTemplateSpec(
                    metadata={"labels": {"app": "elasticsearch"}},
                    spec=PodSpec(
                        security_context=PodSecurityContext(
                            fs_group=1000,
                            run_as_user=1000,
                            run_as_group=1000,
                        ),
                        init_containers=[self._create_init_container()],
                        containers=[self._create_elasticsearch_container()],
                        volumes=self._get_elasticsearch_volumes(),
                    ),
                ),
            ),
        )

    def _create_elasticsearch_service(self):
        """Create Elasticsearch service"""
        return KubeService(
            self,
            "elasticsearch-service",
            metadata={
                "name": "cdk8s-elasticsearch-service-elasticsearch-service-c83bfbef"
            },
            spec={
                "selector": {"app": "elasticsearch"},
                "ports": [{"port": 9200, "targetPort": IntOrString.from_number(9200)}],
                "type": "ClusterIP",
            },
        )

    def _create_elasticsearch_infrastructure(self):
        """Create all Elasticsearch-related infrastructure"""
        self._create_persistent_volume_claim()
        self._create_elasticsearch_deployment()
        self._create_elasticsearch_service()
