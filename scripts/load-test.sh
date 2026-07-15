#!/usr/bin/env bash
# =============================================================================
# load-test.sh — Repeatable load test for the observability lab
#
# Requirements: curl, ab (apache2-utils) or hey
# Usage:
#   ./scripts/load-test.sh normal    # baseline traffic
#   ./scripts/load-test.sh stress    # high concurrency
#   ./scripts/load-test.sh failure   # hammer /fail endpoint
#   ./scripts/load-test.sh all       # run all three in sequence
# =============================================================================
set -euo pipefail

GATEWAY="http://localhost:8080/service-a"
SCENARIO="${1:-normal}"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

banner() { echo -e "\n${YELLOW}=== $1 ===${NC}\n"; }
ok()     { echo -e "${GREEN}✔ $1${NC}"; }
info()   { echo -e "  $1"; }

check_deps() {
    if ! command -v ab &>/dev/null; then
        echo -e "${RED}ERROR: 'ab' not found. Install with: sudo apt install apache2-utils${NC}"
        exit 1
    fi
}

run_normal() {
    banner "SCENARIO: Normal Traffic (500 requests, 10 concurrent)"
    info "Target: GET $GATEWAY/greet-service-b"
    ab -n 500 -c 10 -q "$GATEWAY/greet-service-b" 2>&1 | \
        grep -E "Requests per second|Time per request|Failed requests|Percentage"
    ok "Normal traffic complete. Check Grafana for baseline metrics."
}

run_stress() {
    banner "SCENARIO: Stress Traffic (2000 requests, 50 concurrent)"
    info "Target: GET $GATEWAY/greet-service-b"
    ab -n 2000 -c 50 -q "$GATEWAY/greet-service-b" 2>&1 | \
        grep -E "Requests per second|Time per request|Failed requests|Percentage"
    ok "Stress traffic complete. Check Grafana — latency should spike."
}

run_failure() {
    banner "SCENARIO: Failure Traffic (300 requests, 10 concurrent, hitting /fail)"
    info "Target: GET $GATEWAY/fail"
    info "Expected: 100% 500 errors — HighErrorRate alert should fire within 2 minutes"
    ab -n 300 -c 10 -q "$GATEWAY/fail" 2>&1 | \
        grep -E "Requests per second|Time per request|Failed requests|Non-2xx" || true
    ok "Failure traffic complete. Check Prometheus alerts and Grafana error rate panel."
    echo ""
    info "To verify the alert:"
    info "  curl http://localhost:9090/api/v1/rules | python3 -m json.tool | grep -A5 HighErrorRate"
}

check_deps

case "$SCENARIO" in
    normal)  run_normal ;;
    stress)  run_stress ;;
    failure) run_failure ;;
    all)
        run_normal
        sleep 5
        run_stress
        sleep 5
        run_failure
        banner "All scenarios complete"
        ok "Open Grafana at http://localhost:3000 to review results"
        ok "Open Prometheus at http://localhost:9090/alerts to check alert state"
        ;;
    *)
        echo "Usage: $0 {normal|stress|failure|all}"
        exit 1
        ;;
esac
