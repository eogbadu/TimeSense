"use client";

import { useCallback } from "react";
import { useAuth } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** All network calls go through this — never call fetch() against the backend elsewhere. */
export async function apiFetch<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Convenience hook for admin pages: resolves the current Firebase ID token automatically. */
export function useAdminApi() {
  const { getIdToken } = useAuth();

  return useCallback(
    async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
      const token = await getIdToken();
      return apiFetch<T>(path, token, options);
    },
    [getIdToken]
  );
}
