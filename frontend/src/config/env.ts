// The development server can use its same-origin Vite proxy. Production must
// explicitly name the deployed F8 API origin.
const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();

export const apiBaseUrl: string | null = configuredBase
  ? configuredBase.replace(/\/+$/, '')
  : import.meta.env.DEV ? '' : null;

export const demoEnabled = import.meta.env.VITE_DEMO_MODE === 'true';
export const mockEnabled = demoEnabled || (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_DATA === 'true');
export const gradioSpaceId = import.meta.env.VITE_GRADIO_SPACE_ID?.trim() || 'mrintrovert19/sonar-shield-api';
