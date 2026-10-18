export type ServiceStatus = 'ok' | 'ready' | 'degraded' | 'unhealthy' | 'error';

export interface HealthStatusResponse {
  status: 'ok' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface ApiClientConfig {
  baseUrl: string;
  timeoutMs?: number;
}
