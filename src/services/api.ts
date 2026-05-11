import { ClothingItem, UserProfile } from "../types";

// Base URL do backend
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const publicAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function getAssetUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
}

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  let authHeader: string | undefined = undefined;

  if (accessToken) {
    authHeader = `Bearer ${accessToken}`;
  }
  // Removed publicAnonKey fallback to ensure Visitors send NO header
  // and trigger the correct backend handling for unauthenticated requests.

  const headers: HeadersInit = {
    ...(authHeader ? { Authorization: authHeader } : {}),
    ...(options.headers || {}),
  };

  if (!(options.body instanceof FormData)) {
    (headers as any)["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    // ignorar erro de parse se não for json
  }

  if (!response.ok) {
    const message = (data && (data.error || data.detail || data.message)) || `HTTP ${response.status}`;
    throw new Error(message);
  }

  return data;
}

/* --- FUNÇÕES --- */

export async function signup(email: string, password: string, name: string) {
  return fetchAPI("/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function getItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI("/items");
}

export async function addItem(item: Omit<ClothingItem, "id">): Promise<{ item: ClothingItem }> {
  console.log("[api.ts] Frontend payload before POST /items", {
    ...item,
    image: item.image ? `${item.image.slice(0, 80)}...(${item.image.length} chars)` : item.image,
  });
  return fetchAPI("/items", {
    method: "POST",
    body: JSON.stringify(item),
  });
}

export async function updateItem(id: string, updates: Partial<ClothingItem>): Promise<{ item: ClothingItem }> {
  console.log("[api.ts] Frontend payload before PUT /items", {
    id,
    ...updates,
    image: updates.image ? `${updates.image.slice(0, 80)}...(${updates.image.length} chars)` : updates.image,
  });
  return fetchAPI(`/items/${id}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function deleteItem(id: string): Promise<{ success: boolean }> {
  return fetchAPI(`/items/${id}`, {
    method: "DELETE",
  });
}

/* UPLOAD IMAGEM */
export async function uploadImage(file: File, fileName: string): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);

  return fetchAPI("/upload-image", {
    method: "POST",
    body: formData,
  });
}

export async function getProfile(): Promise<{ profile: UserProfile }> {
  return fetchAPI("/profile");
}

export async function updateProfile(payload: any): Promise<{ profile: UserProfile }> {
  return fetchAPI("/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getPublicItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI("/public-items");
}

/* --- SOCIAL --- */

export async function likeItem(itemId: string) {
  return fetchAPI(`/social/like/${itemId}`, { method: "POST" });
}

export async function unlikeItem(itemId: string) {
  return fetchAPI(`/social/like/${itemId}`, { method: "DELETE" });
}

export async function getLikedItems(): Promise<{ items: ClothingItem[] }> {
  return fetchAPI("/social/likes");
}

export async function getItemLikes(itemId: string): Promise<{ count: number; isLiked: boolean }> {
  return fetchAPI(`/social/likes/${itemId}`);
}

export async function getComments(itemId: string): Promise<{ comments: any[] }> {
  return fetchAPI(`/social/comments/${itemId}`);
}

export async function addComment(itemId: string, text: string) {
  return fetchAPI(`/social/comment/${itemId}`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function addToWishlist(itemId: string) {
  return fetchAPI(`/social/wishlist/${itemId}`, { method: "POST" });
}

export async function removeFromWishlist(itemId: string) {
  return fetchAPI(`/social/wishlist/${itemId}`, { method: "DELETE" });
}

export async function getWishlist(): Promise<{ items: any[] }> {
  return fetchAPI("/social/wishlist");
}

/* --- AI OUTFIT --- */
export async function getAIDailyOutfit(
  weather_data: any,
  preferences?: any,
  exclude_items?: any[],
  user_request?: string,
  current_outfit_items?: string[]
) {
  console.log("[api.ts] POST /ai-outfit/today payload", {
    weather_data,
    preferences: preferences || {},
    exclude_items: exclude_items || [],
    user_request: user_request || undefined,
    user_prompt: user_request || undefined,
    current_outfit_items: current_outfit_items || [],
  });
  return fetchAPI("/ai-outfit/today", {
    method: "POST",
    body: JSON.stringify({
      weather_data,
      preferences: preferences || {},
      exclude_items: exclude_items || [],
      current_outfit_items: current_outfit_items || [],
      user_request: user_request || undefined,
      user_prompt: user_request || undefined,
    }),
  });
}

export async function getAITravelOutfits(payload: {
  destination: string,
  days?: number,
  start_date?: string,
  end_date?: string,
  luggage_limit?: number,
  preferences?: any,
  exclude_items?: string[],
  weather_by_day?: any[]
}) {
  return fetchAPI("/ai-outfit/travel-plan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/* --- USAGE HISTORY --- */
export type WearHistoryEntry = {
  date: string;
  outfit_id?: string | null;
  usage_history_id?: string | null;
  source?: string | null;
  item_ids?: string[];
  items: ClothingItem[];
};

export async function saveOutfitUsage(
  itemIds: string[],
  source: string = "ai_suggestion",
): Promise<{
  success: boolean;
  duplicate?: boolean;
  outfit: { id?: string | null; source?: string | null; used_at?: string; items: ClothingItem[]; item_ids: string[] };
  usage_history_id?: string | null;
}> {
  return fetchAPI("/outfits/use-today", {
    method: "POST",
    body: JSON.stringify({
      outfit_items: itemIds,
      source,
      used_at: new Date().toISOString(),
    }),
  });
}

export const recordOutfitUsage = saveOutfitUsage;

export async function getWearHistory(days: number = 30): Promise<{ success: boolean; history: WearHistoryEntry[] }> {
  return fetchAPI(`/usage/history?days=${days}`);
}
