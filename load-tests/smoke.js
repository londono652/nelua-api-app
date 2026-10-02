// Prueba de humo: carga ligera después de cada despliegue en staging.
// 20 iteraciones por segundo durante 30 s, con 2 peticiones cada una (1.200 en
// total), por debajo del límite por IP del WAF (2.000 en 5 minutos).
//
//   k6 run -e BASE_URL=http://localhost:8000 load-tests/smoke.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-arrival-rate',
      rate: 20,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 10,
      maxVUs: 20,
    },
  },
  // Si no se cumplen, k6 termina con error y el pipeline falla.
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const id = Math.floor(Math.random() * 12) + 1;
  const responses = http.batch([
    ['GET', `${BASE_URL}/products`],
    ['GET', `${BASE_URL}/products/${id}`],
  ]);

  check(responses[0], { 'listado responde 200': (r) => r.status === 200 });
  check(responses[1], { 'detalle responde 200': (r) => r.status === 200 });
}
