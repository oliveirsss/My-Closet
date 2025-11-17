import { projectId, publicAnonKey } from './supabase/info.tsx';
import { ClothingItem } from '../App';

const API_BASE = `https://${projectId}.supabase.co/functions/v1/make-server-1d4585bc`;

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
