# charts/ingress.py
from constructs import Construct
from cdk8s import Chart
from imports.k8s import (
    KubeIngress,
    IngressSpec,
    IngressRule,
    HttpIngressRuleValue,
    HttpIngressPath,
    IngressBackend,
    ServiceBackendPort,
)
import os


class IngressChart(Chart):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Get domain from environment variables with fallback
        frontend_domain = os.environ.get("FRONTEND_DOMAIN", "acaceta.com")

        # Create ingress with common configuration
        self._create_main_ingress(frontend_domain)

    def _get_common_annotations(self):
        """Define common annotations for ingress configuration"""
        return {
            # Basic ingress config
            "nginx.ingress.kubernetes.io/use-regex": "true",
            "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
            # Timeouts
            "nginx.ingress.kubernetes.io/proxy-connect-timeout": "600",
            "nginx.ingress.kubernetes.io/proxy-send-timeout": "600",
            "nginx.ingress.kubernetes.io/proxy-read-timeout": "600",
            "nginx.ingress.kubernetes.io/proxy-body-size": "50m",
            # CORS configuration
            "nginx.ingress.kubernetes.io/enable-cors": "true",
            "nginx.ingress.kubernetes.io/cors-allow-methods": "PUT, GET, POST, OPTIONS, DELETE",
            "nginx.ingress.kubernetes.io/cors-allow-credentials": "true",
            "nginx.ingress.kubernetes.io/cors-allow-headers": (
                "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,"
                "If-Modified-Since,Cache-Control,Content-Type,Authorization,"
                "Origin,Accept,Access-Control-Request-Method,"
                "Access-Control-Request-Headers"
            ),
            # SSL configuration
            "cert-manager.io/cluster-issuer": "letsencrypt-prod",
            "nginx.ingress.kubernetes.io/ssl-redirect": "true",
            "nginx.ingress.kubernetes.io/force-ssl-redirect": "true",
            "nginx.ingress.kubernetes.io/from-to-www-redirect": "true",
            # Advanced CORS and security configuration
            "nginx.ingress.kubernetes.io/configuration-snippet": r"""
                if ($http_origin ~ '^https://(www\.)?acaceta\.com$') {
                    set $allow_origin $http_origin;
                }

                if ($request_method = 'OPTIONS') {
                    add_header 'Access-Control-Allow-Origin' $allow_origin always;
                    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
                    add_header 'Access-Control-Allow-Headers' 'DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization,Origin,Accept,Access-Control-Request-Method,Access-Control-Request-Headers' always;
                    add_header 'Access-Control-Allow-Credentials' 'true' always;
                    add_header 'Access-Control-Max-Age' 1728000;
                    add_header 'Content-Type' 'text/plain charset=UTF-8';
                    add_header 'Content-Length' 0;
                    return 204;
                }

                add_header 'Access-Control-Allow-Origin' $allow_origin always;
                add_header 'Access-Control-Allow-Credentials' 'true' always;
                add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
                add_header 'Access-Control-Allow-Headers' 'DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization,Origin,Accept,Access-Control-Request-Method,Access-Control-Request-Headers' always;

                # Force .mjs files to be served with application/javascript MIME type
                location ~* \.mjs$ {
                    default_type application/javascript;
                    add_header Content-Type "application/javascript" always;
                }
            """,
        }

    def _create_paths(self, is_www=False):
        """Create the ingress paths for a domain"""
        return [
            # Backend API path
            HttpIngressPath(
                path="/api(/|$)(.*)",
                path_type="ImplementationSpecific",
                backend=IngressBackend(
                    service={
                        "name": "backend-service",
                        "port": ServiceBackendPort(number=5000),
                    }
                ),
            ),
            # Frontend catch-all
            HttpIngressPath(
                path="/(.*)",
                path_type="ImplementationSpecific",
                backend=IngressBackend(
                    service={
                        "name": "frontend-service",
                        "port": ServiceBackendPort(number=80),
                    }
                ),
            ),
        ]

    def _create_main_ingress(self, frontend_domain: str):
        """Create the main ingress resource"""

        # Create rules for both www and non-www domains
        rules = [
            # Non-www domain rules
            IngressRule(
                host=frontend_domain,
                http=HttpIngressRuleValue(paths=self._create_paths(is_www=False)),
            ),
            # www domain rules
            IngressRule(
                host=f"www.{frontend_domain}",
                http=HttpIngressRuleValue(paths=self._create_paths(is_www=True)),
            ),
        ]

        # Create the ingress resource
        KubeIngress(
            self,
            "frontend-ingress",
            metadata={
                "name": "frontend-ingress",
                "annotations": self._get_common_annotations(),
            },
            spec=IngressSpec(
                ingress_class_name="nginx",
                tls=[
                    {
                        "hosts": [frontend_domain, f"www.{frontend_domain}"],
                        "secretName": "acaceta-tls",
                    }
                ],
                rules=rules,
            ),
        )
