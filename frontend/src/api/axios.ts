import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000',
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  console.log(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.message);
    if (error.code === 'ERR_NETWORK') {
      console.error(
        '[API] Backend tidak dapat diakses. Pastikan backend running di:',
        api.defaults.baseURL,
      );
    }
    return Promise.reject(error);
  },
);

export default api;
