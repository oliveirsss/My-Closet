import { ClothingItem, UserProfile } from '../types';

// Aponta para o teu servidor Python local
const API_BASE = 'http://127.0.0.1:8000';

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
  const headers = {
    'Content-Type': 'application/json',
    // Usa o token do user se existir, senão usa a chave pública
    'Authorization': `Bearer ${accessToken || publicAnonKey}`,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// ... (Mantém as restantes funções: signup, getItems, addItem, etc. iguais) ...
export async function signup(email: string, password: string, name: string) {
  return fetchAPI('/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  });
}

export async function getItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI('/items');
}

export async function addItem(item: Omit<ClothingItem, 'id'>): Promise<{ item: ClothingItem }> {
  return fetchAPI('/items', {
    method: 'POST',
    body: JSON.stringify(item),
  });
}

export async function updateItem(id: string, updates: Partial<ClothingItem>): Promise<{ item: ClothingItem }> {
  return fetchAPI(`/items/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteItem(id: string): Promise<{ success: boolean }> {
  return fetchAPI(`/items/${id}`, {
    method: 'DELETE',
  });
}

export async function uploadImage(image: string, fileName: string): Promise<{ url: string; path: string }> {
  return fetchAPI('/upload-image', {
    method: 'POST',
    body: JSON.stringify({ image, fileName }),
  });
}

type ProfilePayload = {
  name: string;
  avatar_url?: string | null;
  bio?: string | null;
  location?: string | null;
};

export async function getProfile(): Promise<{ profile: UserProfile }> {
  return fetchAPI('/profile');
}

export async function updateProfile(payload: ProfilePayload): Promise<{ profile: UserProfile }> {
  return fetchAPI('/profile', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}