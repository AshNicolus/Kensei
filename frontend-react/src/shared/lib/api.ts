import axios, { AxiosError, AxiosRequestConfig } from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 600_000,
});

const TOKEN_KEY = "kensei.token";
const EMAIL_KEY = "kensei.email";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  },
  getEmail: () => localStorage.getItem(EMAIL_KEY),
  setEmail: (email: string) => localStorage.setItem(EMAIL_KEY, email),
};

api.interceptors.request.use((config) => {
  const tok = tokenStore.get();
  if (tok) {
    config.headers = config.headers || {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${tok}`;
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401 && onUnauthorized) {
      onUnauthorized();
    }
    return Promise.reject(err);
  }
);

export function apiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: string | object } | undefined;
    if (data?.detail) {
      return typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail);
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

export type RequestOpts = AxiosRequestConfig;
