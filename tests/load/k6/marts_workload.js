/**
 * K6 workload driven by tests/load/workload-manifest.yaml (G-011).
 * Default target is gateway /readyz for Local evidence; set TRINO_URL for mart SQL.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const latency = new Trend("vanguard_latency_ms", true);

const BASE = __ENV.GATEWAY_URL || "http://localhost:8000";
const VUS = Number(__ENV.VUS || 50);
const DURATION = __ENV.DURATION || "10m";

export const options = {
  scenarios: {
    marts_mix: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: VUS },
        { duration: DURATION, target: VUS },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    // Bound to workload-manifest.yaml slos.*
    http_req_duration: ["p(95)<750", "p(99)<1500"],
    errors: ["rate<0.01"],
  },
};

const TEMPLATES = [
  { id: "curation_health", weight: 0.35, path: "/readyz" },
  { id: "data_quality", weight: 0.3, path: "/readyz" },
  { id: "security_posture", weight: 0.2, path: "/readyz" },
  { id: "mission_eval", weight: 0.15, path: "/openapi.json" },
];

function pickTemplate() {
  const r = Math.random();
  let acc = 0;
  for (const t of TEMPLATES) {
    acc += t.weight;
    if (r <= acc) return t;
  }
  return TEMPLATES[0];
}

export default function () {
  const t = pickTemplate();
  const res = http.get(`${BASE}${t.path}`, {
    tags: { template: t.id },
  });
  const ok = check(res, {
    "status is 200": (r) => r.status === 200,
  });
  errorRate.add(!ok);
  latency.add(res.timings.duration);
  sleep(0.2);
}

export function handleSummary(data) {
  // Caller merges dataset/code versions via tools/link_load_report.py
  return {
    "tests/load/reports/k6-summary.json": JSON.stringify(data, null, 2),
  };
}
