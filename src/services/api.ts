import { ClothingItem, UserProfile } from "../types";

// Base URL do backend (vem do .env, com fallback para localhost)
const API_BASE =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Chave pública para quando o user não está logado (fallback)
const publicAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  // Construir header Authorization de forma segura
  let authHeader: string | undefined = undefined;

  if (accessToken) {
    authHeader = `Bearer ${accessToken}`;
  } else if (publicAnonKey) {
    authHeader = `Bearer ${publicAnonKey}`;
  }

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(authHeader ? { Authorization: authHeader } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Tentar ler JSON, mas sem rebentar se o backend mandar texto simples
  let data: any = null;
  try {
    data = await response.json();
  } catch {
    // se não for JSON, deixamos data = null
  }

  if (!response.ok) {
    const message =
        (data && (data.error || data.detail || data.message)) ||
        `HTTP ${response.status}`;
    throw new Error(message);
  }

  return data;
}

/* AUTH / SIGNUP */

export async function signup(email: string, password: string, name: string) {
  return fetchAPI("/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

/* ITEMS (PRIVADO) */

export async function getItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI("/items");
}

export async function addItem(
    item: Omit<ClothingItem, "id">
): Promise<{ item: ClothingItem }> {
  return fetchAPI("/items", {
    method: "POST",
    body: JSON.stringify(item),
  });
}

export async function updateItem(
    id: string,
    updates: Partial<ClothingItem>
): Promise<{ item: ClothingItem }> {
  return fetchAPI(`/items/${id}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function deleteItem(
    id: string
): Promise<{ success: boolean }> {
  return fetchAPI(`/items/${id}`, {
    method: "DELETE",
  });
}

/* UPLOAD IMAGEM */

export async function uploadImage(
    image: string,
    fileName: string
): Promise<{ url: string; path: string }> {
  // Ajusta o endpoint se no backend estiver com prefixo (ex.: /storage/upload-image)
  return fetchAPI("/upload-image", {
    method: "POST",
    body: JSON.stringify({ image, fileName }),
  });
}

/* PERFIL */

type ProfilePayload = {
  name: string;
  avatar_url?: string | null;
  bio?: string | null;
  location?: string | null;
};

export async function getProfile(): Promise<{ profile: UserProfile }> {
  return fetchAPI("/profile");
}

export async function updateProfile(
    payload: ProfilePayload
): Promise<{ profile: UserProfile }> {
  return fetchAPI("/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/* ITENS PÚBLICOS (VISITANTE) */

export async function getPublicItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI("/public-items");
}