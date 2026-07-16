#!/usr/bin/env python3
"""Generate Phase 5 Kubernetes manifests from Docker resource contracts (G-007)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import render_resources as rr  # noqa: E402

OUT_BASE = REPO / "infra" / "k8s" / "base"
OUT_KARPENTER = REPO / "infra" / "k8s" / "karpenter"
OUT_MONITORING = REPO / "infra" / "k8s" / "monitoring"
OUT_OVERLAYS = REPO / "infra" / "k8s" / "overlays"
GENERATED_META = REPO / "infra" / "k8s" / "generated" / "resource-digests.json"

NAMESPACES = [
    "agentic-app",
    "data-pipeline",
    "gateway",
    "analytics",
    "observability",
]

# Workload → scheduling / image mapping from Sections 2 and 6.
WORKLOADS: dict[str, dict[str, Any]] = {
    "gateway": {
        "namespace": "gateway",
        "name": "ai-gateway",
        "replicas": 2,
        "image": "vanguard/gateway:phase2",
        "port": 8000,
        "command": None,
        "service": True,
    },
    "inference": {
        "namespace": "agentic-app",
        "name": "inference-api",
        "replicas": 1,
        "image": "vanguard/inference:phase2",
        "port": 8000,
        "command": None,
        "service": True,
    },
    "pipeline": {
        "namespace": "data-pipeline",
        "name": "curation-pipeline",
        "replicas": 1,
        "image": "vanguard/pipeline:phase2",
        "port": None,
        "command": ["python", "-m", "app.data_pipelines"],
        "service": False,
    },
}

NODEPOOLS = {
    "inference-gpu": {
        "families": ["g5", "p4d"],
        "capacity_types": ["on-demand"],
        "ami_family": "AL2",
    },
    "pipeline-cpu": {
        "families": ["r6i"],
        "capacity_types": ["spot", "on-demand"],
        "ami_family": "AL2",
    },
    "gateway-general": {
        "families": ["m6i"],
        "capacity_types": ["on-demand"],
        "ami_family": "AL2",
    },
    "sandbox-runtime": {
        "families": ["c6i"],
        "capacity_types": ["on-demand"],
        "ami_family": "AL2",
    },
}


def _dump(doc: Any) -> str:
    return yaml.safe_dump(doc, sort_keys=False).rstrip() + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path.relative_to(REPO)}")


def render_namespaces() -> None:
    docs = [
        {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": ns, "labels": {"app.kubernetes.io/part-of": "vanguard"}},
        }
        for ns in NAMESPACES
    ]
    write(OUT_BASE / "namespaces.yaml", "".join(_dump(d) + "---\n" for d in docs).rstrip("-\n") + "\n")


def render_network_policies() -> None:
    docs = []
    for ns in NAMESPACES:
        docs.append(
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {
                    "name": "default-deny-all",
                    "namespace": ns,
                    "labels": {"app.kubernetes.io/part-of": "vanguard"},
                },
                "spec": {
                    "podSelector": {},
                    "policyTypes": ["Ingress", "Egress"],
                },
            }
        )
        # Allow DNS egress so pods can resolve in-cluster services.
        docs.append(
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {
                    "name": "allow-dns-egress",
                    "namespace": ns,
                },
                "spec": {
                    "podSelector": {},
                    "policyTypes": ["Egress"],
                    "egress": [
                        {
                            "to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}}}],
                            "ports": [
                                {"protocol": "UDP", "port": 53},
                                {"protocol": "TCP", "port": 53},
                            ],
                        }
                    ],
                },
            }
        )
    # Gateway may receive traffic from agentic-app; analytics may reach gateway Trino later.
    docs.append(
        {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "allow-agentic-to-gateway", "namespace": "gateway"},
            "spec": {
                "podSelector": {"matchLabels": {"app": "ai-gateway"}},
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {"kubernetes.io/metadata.name": "agentic-app"}
                                }
                            }
                        ],
                        "ports": [{"protocol": "TCP", "port": 8000}],
                    }
                ],
            },
        }
    )
    write(
        OUT_BASE / "networkpolicies.yaml",
        "\n---\n".join(_dump(d).rstrip() for d in docs) + "\n",
    )


def deployment_for(workload: str, contract: dict[str, Any], resources: dict[str, Any]) -> dict[str, Any]:
    meta = WORKLOADS[workload]
    nodepool = contract["nodepool"]
    container: dict[str, Any] = {
        "name": meta["name"],
        "image": meta["image"],
        "imagePullPolicy": "IfNotPresent",
        "securityContext": {
            "runAsNonRoot": True,
            "runAsUser": 8888,
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": False,
        },
        "resources": resources["resources"],
        "env": [
            {"name": "VANGUARD_WORKLOAD", "value": workload},
        ],
    }
    if meta["port"]:
        container["ports"] = [{"containerPort": meta["port"], "name": "http"}]
        container["readinessProbe"] = {
            "httpGet": {"path": "/readyz", "port": "http"},
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
        }
    if meta["command"]:
        container["command"] = meta["command"]

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": meta["name"],
            "namespace": meta["namespace"],
            "labels": {
                "app": meta["name"],
                "workload": workload,
                "app.kubernetes.io/part-of": "vanguard",
            },
            "annotations": {
                "vanguard.ai/resource-contract": f"infra/docker/resources/{workload}.yaml",
            },
        },
        "spec": {
            "replicas": meta["replicas"],
            "selector": {"matchLabels": {"app": meta["name"]}},
            "template": {
                "metadata": {
                    "labels": {
                        "app": meta["name"],
                        "workload": workload,
                        "workload-tier": nodepool,
                    }
                },
                "spec": {
                    "nodeSelector": {"karpenter.sh/nodepool": nodepool},
                    "tolerations": [
                        {
                            "key": "workload-tier",
                            "operator": "Equal",
                            "value": nodepool,
                            "effect": "NoSchedule",
                        }
                    ],
                    "containers": [container],
                },
            },
        },
    }


def service_for(workload: str) -> dict[str, Any] | None:
    meta = WORKLOADS[workload]
    if not meta["service"]:
        return None
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": meta["name"],
            "namespace": meta["namespace"],
            "labels": {"app": meta["name"]},
        },
        "spec": {
            "selector": {"app": meta["name"]},
            "ports": [{"name": "http", "port": meta["port"], "targetPort": "http"}],
        },
    }


def render_workloads(schema: dict[str, Any]) -> dict[str, Any]:
    digests: dict[str, Any] = {}
    for workload in ("gateway", "inference", "pipeline"):
        contract_path = REPO / "infra" / "docker" / "resources" / f"{workload}.yaml"
        result = rr.render_pair(contract_path, schema)
        resources = yaml.safe_load(result["k8s_resources_yaml"])
        contract = rr.load_contract(contract_path)
        dep = deployment_for(workload, contract, resources)
        docs = [dep]
        svc = service_for(workload)
        if svc:
            docs.append(svc)
        write(
            OUT_BASE / f"{WORKLOADS[workload]['name']}.yaml",
            "\n---\n".join(_dump(d).rstrip() for d in docs) + "\n",
        )
        digests[workload] = {
            "k8s_digest": result["k8s_digest"],
            "karpenter_digest": result["karpenter_digest"],
            "pair_digest": result["pair_digest"],
            "nodepool": contract["nodepool"],
            "manifest": f"infra/k8s/base/{WORKLOADS[workload]['name']}.yaml",
        }
    return digests


def render_karpenter() -> None:
    docs = []
    for name, cfg in NODEPOOLS.items():
        docs.append(
            {
                "apiVersion": "karpenter.k8s.aws/v1",
                "kind": "EC2NodeClass",
                "metadata": {"name": name},
                "spec": {
                    "amiFamily": cfg["ami_family"],
                    "role": "vanguard-karpenter-node",
                    "subnetSelectorTerms": [{"tags": {"karpenter.sh/discovery": "vanguard"}}],
                    "securityGroupSelectorTerms": [{"tags": {"karpenter.sh/discovery": "vanguard"}}],
                    "tags": {
                        "Name": f"vanguard-{name}",
                        "workload-tier": name,
                    },
                },
            }
        )
        docs.append(
            {
                "apiVersion": "karpenter.sh/v1",
                "kind": "NodePool",
                "metadata": {"name": name},
                "spec": {
                    "template": {
                        "metadata": {"labels": {"workload-tier": name}},
                        "spec": {
                            "requirements": [
                                {
                                    "key": "karpenter.sh/capacity-type",
                                    "operator": "In",
                                    "values": cfg["capacity_types"],
                                },
                                {
                                    "key": "karpenter.k8s.aws/instance-family",
                                    "operator": "In",
                                    "values": cfg["families"],
                                },
                                {
                                    "key": "kubernetes.io/arch",
                                    "operator": "In",
                                    "values": ["amd64"],
                                },
                            ],
                            "taints": [
                                {
                                    "key": "workload-tier",
                                    "value": name,
                                    "effect": "NoSchedule",
                                }
                            ],
                            "nodeClassRef": {
                                "group": "karpenter.k8s.aws",
                                "kind": "EC2NodeClass",
                                "name": name,
                            },
                        },
                    },
                    "disruption": {
                        "consolidationPolicy": "WhenEmptyOrUnderutilized",
                        "consolidateAfter": "30m",
                    },
                },
            }
        )
    write(
        OUT_KARPENTER / "nodepools.yaml",
        "\n---\n".join(_dump(d).rstrip() for d in docs) + "\n",
    )


def render_kustomize() -> None:
    base_resources = [
        "namespaces.yaml",
        "networkpolicies.yaml",
        "ai-gateway.yaml",
        "inference-api.yaml",
        "curation-pipeline.yaml",
    ]
    write(
        OUT_BASE / "kustomization.yaml",
        _dump(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "kind": "Kustomization",
                "resources": base_resources,
            }
        ),
    )
    overlay_defs = {
        "dev": [
            ("ai-gateway", "gateway", 1),
            ("inference-api", "agentic-app", 1),
        ],
        "prod": [
            ("ai-gateway", "gateway", 2),
            ("inference-api", "agentic-app", 2),
        ],
    }
    for env, replicas in overlay_defs.items():
        overlay = OUT_OVERLAYS / env
        patches = []
        for name, namespace, count in replicas:
            patch_file = f"replica-{name}.yaml"
            write(
                overlay / patch_file,
                _dump(
                    {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "metadata": {"name": name, "namespace": namespace},
                        "spec": {"replicas": count},
                    }
                ),
            )
            patches.append({"path": patch_file})
        write(
            overlay / "kustomization.yaml",
            _dump(
                {
                    "apiVersion": "kustomize.config.k8s.io/v1beta1",
                    "kind": "Kustomization",
                    "resources": ["../../base", "../../karpenter", "../../monitoring"],
                    "patches": patches,
                    "labels": [
                        {
                            "pairs": {"vanguard.ai/env": env},
                            "includeSelectors": False,
                        }
                    ],
                }
            ),
        )


def render_monitoring() -> None:
    # In-cluster Prometheus + Grafana for air-gapped/IL mission BI (Section 5).
    docs = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "prometheus",
                "namespace": "observability",
                "labels": {"app": "prometheus"},
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "prometheus"}},
                "template": {
                    "metadata": {"labels": {"app": "prometheus"}},
                    "spec": {
                        "nodeSelector": {"karpenter.sh/nodepool": "gateway-general"},
                        "tolerations": [
                            {
                                "key": "workload-tier",
                                "operator": "Equal",
                                "value": "gateway-general",
                                "effect": "NoSchedule",
                            }
                        ],
                        "containers": [
                            {
                                "name": "prometheus",
                                "image": "prom/prometheus:v2.54.1",
                                "ports": [{"containerPort": 9090, "name": "http"}],
                                "resources": {
                                    "requests": {"cpu": "250m", "memory": "512Mi"},
                                    "limits": {"cpu": "1000m", "memory": "2Gi"},
                                },
                            }
                        ],
                    },
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "prometheus", "namespace": "observability"},
            "spec": {
                "selector": {"app": "prometheus"},
                "ports": [{"port": 9090, "targetPort": "http", "name": "http"}],
            },
        },
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "grafana",
                "namespace": "observability",
                "labels": {"app": "grafana"},
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "grafana"}},
                "template": {
                    "metadata": {"labels": {"app": "grafana"}},
                    "spec": {
                        "nodeSelector": {"karpenter.sh/nodepool": "gateway-general"},
                        "tolerations": [
                            {
                                "key": "workload-tier",
                                "operator": "Equal",
                                "value": "gateway-general",
                                "effect": "NoSchedule",
                            }
                        ],
                        "containers": [
                            {
                                "name": "grafana",
                                "image": "grafana/grafana:11.2.0",
                                "ports": [{"containerPort": 3000, "name": "http"}],
                                "volumeMounts": [
                                    {
                                        "name": "datasources",
                                        "mountPath": "/etc/grafana/provisioning/datasources",
                                        "readOnly": True,
                                    }
                                ],
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "256Mi"},
                                    "limits": {"cpu": "500m", "memory": "512Mi"},
                                },
                            }
                        ],
                        "volumes": [
                            {
                                "name": "datasources",
                                "configMap": {"name": "grafana-datasources"},
                            }
                        ],
                    },
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "grafana", "namespace": "observability"},
            "spec": {
                "selector": {"app": "grafana"},
                "ports": [{"port": 3000, "targetPort": "http", "name": "http"}],
            },
        },
    ]
    write(
        OUT_MONITORING / "prometheus-grafana.yaml",
        "\n---\n".join(_dump(d).rstrip() for d in docs) + "\n",
    )

    # Section 5 Grafana datasources — Mission BI alongside Prometheus (G-004 oauthPassThru).
    datasources = {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "access": "proxy",
                "url": "http://prometheus.observability.svc.cluster.local:9090",
                "editable": False,
            },
            {
                "name": "MissionBI-Trino",
                "type": "grafana-trino-datasource",
                "access": "proxy",
                "url": "http://trino.query-engine.svc.cluster.local:8080",
                "jsonData": {
                    "catalog": "mission_marts",
                    "oauthPassThru": True,
                },
                "editable": False,
            },
            {
                "name": "MissionBI-MetadataDB",
                "type": "postgres",
                "access": "proxy",
                "url": "rds-metadata-replica.internal:5432",
                "database": "curation_metadata",
                "editable": False,
            },
        ],
    }
    # Also publish under analytics/grafana/provisioning for the dual-path artifact.
    analytics_ds = REPO / "analytics" / "grafana" / "provisioning" / "datasources.yaml"
    write(analytics_ds, _dump(datasources))

    cm = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "grafana-datasources",
            "namespace": "observability",
        },
        "data": {
            "datasources.yaml": _dump(datasources),
        },
    }
    write(OUT_MONITORING / "grafana-datasources-configmap.yaml", _dump(cm))
    write(
        OUT_MONITORING / "kustomization.yaml",
        _dump(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "kind": "Kustomization",
                "resources": [
                    "prometheus-grafana.yaml",
                    "grafana-datasources-configmap.yaml",
                ],
            }
        ),
    )
    write(
        OUT_KARPENTER / "kustomization.yaml",
        _dump(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "kind": "Kustomization",
                "resources": ["nodepools.yaml"],
            }
        ),
    )


def main() -> int:
    schema = rr.load_schema(rr.DEFAULT_SCHEMA)
    render_namespaces()
    render_network_policies()
    digests = render_workloads(schema)
    render_karpenter()
    render_monitoring()
    render_kustomize()
    write(GENERATED_META, json.dumps(digests, indent=2) + "\n")
    print("Phase 5 manifests generated from resource contracts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
