// Prueba de carga: sube por etapas hasta TARGET_RPS y sostiene la carga.
//
//   Local (contra el contenedor):
//     k6 run -e TARGET_RPS=200 -e RAMP=10s -e HOLD=20s load-tests/load.js
//
//   Real (10.000 RPS): se ejecuta dentro del clúster, repartida en varios pods,
//   con load-tests/run-in-cluster.sh.
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TARGET_RPS = parseInt(__ENV.TARGET_RPS || '10000', 10);
const RAMP = __ENV.RAMP || '2m';
const HOLD = __ENV.HOLD || '5m';

export const options = {
  // No se guarda el cuerpo de las respuestas: el generador rinde más.
  discardResponseBodies: true,
  scenarios: {
    load: {
      // "arrival rate": k6 mantiene las peticiones por segundo pedidas aunque
      // la API responda más lento (modelo abierto, como el tráfico real).
      executor: 'ramping-arrival-rate',
      startRate: Math.ceil(TARGET_RPS / 10),
      timeUnit: '1s',
      preAllocatedVUs: Math.ceil(TARGET_RPS / 10),
      maxVUs: Math.ceil(TARGET_RPS / 2),
      stages: [
        { target: Math.ceil(TARGET_RPS * 0.25), duration: RAMP },
        { target: Math.ceil(TARGET_RPS * 0.5), duration: RAMP },
        { target: TARGET_RPS, duration: RAMP },
        { target: TARGET_RPS, duration: HOLD },
        { target: 0, duration: '30s' },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300', 'p(99)<800'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  // Mezcla de tráfico: 80 % detalle de un producto, 20 % listado.
  const detail = Math.random() < 0.8;
  const url = detail
    ? `${BASE_URL}/products/${Math.floor(Math.random() * 12) + 1}`
    : `${BASE_URL}/products`;

  // La etiqueta "name" agrupa las métricas por tipo de petición y no por URL.
  const response = http.get(url, { tags: { name: detail ? 'detalle' : 'listado' } });
  check(response, { 'responde 200': (r) => r.status === 200 });
}
