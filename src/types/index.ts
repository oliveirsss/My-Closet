export interface ClothingItem {
  id: string;
  name: string;
  brand: string;
  size: string;
  type: string;
  layer: number;
  materials: string[];
  weight: number;
  tempMin: number;
  tempMax: number;
  waterproof: boolean;
  windproof: boolean;
  seasons: string[];
  image: string;
  status: 'clean' | 'dirty';
  favorite: boolean;
}

export type UserType = 'visitor' | 'client' | null;

export interface UserProfile {
  user_id: string;
  name: string;
  avatar_url?: string | null;
  bio?: string | null;
  location?: string | null;
}