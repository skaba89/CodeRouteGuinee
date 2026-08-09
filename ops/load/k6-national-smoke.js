import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const ALLOW_PRODUCTION = (__ENV.ALLOW_PRODUCTION_LOAD_TEST || 'false').toLowerCase() === 'true';

if (/coderouteguinee-backend\.onrender\.com/i.test(BASE_URL) && !ALLOW_PRODUCTION) {
  throw new Error('Refus de lancer un load test sur la production sans ALLOW_PRODUCTION_LOAD_TEST=true');
}

export const options = {
  scenarios: {
    public_smoke: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: Number(__ENV.K6_VUS_1 || 10) },
        { duration: '60s', target: Number(__ENV.K6_VUS_2 || 50) },
        { duration: '60s', target: Number(__ENV.K6_VUS_3 || 100) },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '15s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const live = http.get(`${BASE_URL}/health/live`, {
    tags: { endpoint: 'health-live' },
    timeout: '5s',
  });
  check(live, {
    'liveness 200': (r) => r.status === 200,
  });

  const readiness = http.get(`${BASE_URL}/health/readiness`, {
    tags: { endpoint: 'health-readiness' },
    timeout: '5s',
  });
  check(readiness, {
    'readiness 200': (r) => r.status === 200,
  });

  sleep(1);
}
