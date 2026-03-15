import axios from 'axios';

const TOKEN_KEY = 'pqc_token';

/** Show a transient toast message (no dependency). */
function showToast(message: string) {
  const el = document.createElement('div');
  el.setAttribute('role', 'alert');
  el.style.cssText =
    'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1f2937;color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.2);z-index:9999;max-width:90vw;';
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = '/login';
    } else if (status === 429) {
      showToast('Monthly quota exceeded — upgrade your plan');
    }
    return Promise.reject(error);
  }
);

export { api, TOKEN_KEY };
