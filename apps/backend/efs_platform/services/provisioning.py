from django.conf import settings

from efs_platform.models import DomainType, OrganizationDomain


def platform_cname_target() -> str:
    return getattr(settings, "PLATFORM_CNAME_TARGET", "edge.elitefintech.systems")


def dns_records_for_domain(domain: OrganizationDomain, base_domain: str) -> list[dict]:
    sub = domain.hostname.split(".")[0] if "." in domain.hostname else domain.hostname
    records = [
        {
            "type": "CNAME",
            "host": sub,
            "value": platform_cname_target(),
            "ttl": 300,
            "purpose": f"{domain.domain_type} traffic to Elite Fintech edge",
        },
        {
            "type": "TXT",
            "host": "_elite-verify",
            "value": f"elite-verify={domain.verification_token}",
            "ttl": 300,
            "purpose": "Domain ownership verification",
        },
    ]
    return records


def build_setup_manifest(org, transfer, request) -> dict:
    base = transfer.target_domain or "yourdomain.co.za"
    api_host = f"{transfer.api_subdomain}.{base}"
    app_host = f"{transfer.app_subdomain}.{base}"

    api_domain = OrganizationDomain.objects.filter(organization=org, hostname=api_host).first()
    app_domain = OrganizationDomain.objects.filter(organization=org, hostname=app_host).first()

    default_api = request.build_absolute_uri("/").rstrip("/")

    return {
        "platform_tier": "ENTERPRISE",
        "transfer_token": transfer.transfer_token,
        "organization": {"id": str(org.id), "name": org.name, "slug": org.slug},
        "target_domain": base,
        "urls": {
            "api_production": f"https://{api_host}",
            "app_production": f"https://{app_host}",
            "api_current": default_api,
            "webhooks_base": f"https://{api_host}/webhooks/",
            "websocket": f"wss://{api_host}/ws/billing/",
        },
        "dns_records": {
            "api": dns_records_for_domain(api_domain, base) if api_domain else [],
            "app": dns_records_for_domain(app_domain, base) if app_domain else [],
        },
        "environment": {
            "CLIENT_URL": f"https://{app_host}",
            "ALLOWED_HOSTS": f"{api_host},{app_host}",
            "VITE_API_URL": f"https://{api_host}",
            "VITE_WS_URL": f"wss://{api_host}/ws/billing/",
        },
        "setup_steps": [
            {"id": "domain_claim", "label": "Claim custom domain", "done": bool(transfer.target_domain)},
            {"id": "dns_api", "label": f"CNAME {api_host}", "done": "dns_api" in transfer.completed_steps},
            {"id": "dns_app", "label": f"CNAME {app_host}", "done": "dns_app" in transfer.completed_steps},
            {"id": "dns_verify", "label": "Verify TXT record", "done": "dns_verify" in transfer.completed_steps},
            {"id": "webhooks_payfast", "label": "PayFast ITN URL", "done": "webhooks_payfast" in transfer.completed_steps},
            {"id": "webhooks_stripe", "label": "Stripe webhook", "done": "webhooks_stripe" in transfer.completed_steps},
            {"id": "ssl_tls", "label": "TLS provisioned", "done": "ssl_tls" in transfer.completed_steps},
        ],
        "automation": {
            "compatible_agents": ["cursor", "github_actions", "terraform", "custom"],
            "apply_endpoint": request.build_absolute_uri("/api/v1/platform/setup/apply/"),
            "domains_endpoint": request.build_absolute_uri("/api/v1/platform/domains/"),
            "verify_endpoint": request.build_absolute_uri("/api/v1/platform/domains/verify/"),
            "openapi": request.build_absolute_uri("/api/v1/platform/openapi/"),
        },
        "webhook_urls": {
            "payfast": f"https://{api_host}/webhooks/payfast/",
            "stripe": f"https://{api_host}/webhooks/stripe/",
        },
    }
