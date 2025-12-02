import { createClient } from '@supabase/supabase-js';

// Ler as chaves do ficheiro .env
const projectId = import.meta.env.VITE_SUPABASE_PROJECT_ID;
const supabaseUrl = `https://${projectId}.supabase.co`;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);