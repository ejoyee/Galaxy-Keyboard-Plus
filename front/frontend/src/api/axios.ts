import axios from 'axios';
import { BASE_URL } from '@env';
import { useAuthStore } from '../stores/authStore';
import { refreshWithServer } from '../services/authService';

export const api = axios.create({
  // baseURL: 'https://k12e201.p.ssafy.io',
  baseURL: BASE_URL,
  timeout: 8000,
});

// ★ 토큰 주입
api.interceptors.request.use((config) => {
  console.log("BASE_URL: ", BASE_URL);
  const { accessToken } = useAuthStore.getState();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ★ 401 → RT로 재발급(중복 호출 lock)
let refreshPromise: Promise<void> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (
      error.response?.status === 401 &&
      !original._retry &&
      useAuthStore.getState().refreshToken
    ) {
      original._retry = true;

      if (!refreshPromise) {
        refreshPromise = refreshWithServer().finally(
          () => (refreshPromise = null),
        );
      }
      await refreshPromise;
      return api(original);
    }
    return Promise.reject(error);
  },
);
