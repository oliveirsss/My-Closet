import { Hono } from 'npm:hono';
import { cors } from 'npm:hono/cors';
import { logger } from 'npm:hono/logger';
import { createClient } from 'npm:@supabase/supabase-js@2';
import * as kv from './kv_store.tsx';

const app = new Hono();

app.use('*', cors());
app.use('*', logger(console.log));

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

const BUCKET_NAME = 'make-1d4585bc-closet-images';

// Initialize storage bucket on startup
async function initializeBucket() {
  try {
    const { data: buckets } = await supabase.storage.listBuckets();
    const bucketExists = buckets?.some(bucket => bucket.name === BUCKET_NAME);
    
    if (!bucketExists) {
      console.log('Creating storage bucket...');
      const { error } = await supabase.storage.createBucket(BUCKET_NAME, {
        public: false,
        fileSizeLimit: 5242880, // 5MB
      });
      
      if (error) {
        console.error('Error creating bucket:', error);
      } else {
        console.log('Storage bucket created successfully');
      }
    }
  } catch (error) {
    console.error('Error initializing bucket:', error);
  }
}

initializeBucket();

// Helper function to get user from access token
async function getUserFromToken(authHeader: string | null) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  
  const accessToken = authHeader.split(' ')[1];
  const { data: { user }, error } = await supabase.auth.getUser(accessToken);
  
  if (error || !user) {
    console.error('Error getting user from token:', error);
    return null;
  }
  
  return user;
}

// Sign up new user
app.post('/make-server-1d4585bc/signup', async (c) => {
  try {
    const body = await c.req.json();
    const { email, password, name } = body;

    if (!email || !password || !name) {
      return c.json({ error: 'Email, password and name are required' }, 400);
    }

    const { data, error } = await supabase.auth.admin.createUser({
      email,
      password,
      user_metadata: { name },
      // Automatically confirm the user's email since an email server hasn't been configured.
      email_confirm: true
    });

    if (error) {
      console.error('Signup error:', error);
      return c.json({ error: error.message }, 400);
    }

    return c.json({ user: data.user });
  } catch (error) {
    console.error('Signup error:', error);
    return c.json({ error: 'Internal server error during signup' }, 500);
  }
});

// Get all items for a user
app.get('/make-server-1d4585bc/items', async (c) => {
  try {
    const user = await getUserFromToken(c.req.header('Authorization'));
    
    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const key = `user:${user.id}:items`;
    const items = await kv.get(key);
    
    return c.json({ items: items || [] });
  } catch (error) {
    console.error('Error fetching items:', error);
    return c.json({ error: 'Error fetching items' }, 500);
  }
});

// Add new item
app.post('/make-server-1d4585bc/items', async (c) => {
  try {
    const user = await getUserFromToken(c.req.header('Authorization'));
    
    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const body = await c.req.json();
    const key = `user:${user.id}:items`;
    
    const existingItems = await kv.get(key) || [];
    const newItem = {
      ...body,
      id: Date.now().toString(),
      createdAt: new Date().toISOString()
    };
    
    const updatedItems = [...existingItems, newItem];
    await kv.set(key, updatedItems);
    
    return c.json({ item: newItem });
  } catch (error) {
    console.error('Error adding item:', error);
    return c.json({ error: 'Error adding item' }, 500);
  }
});

// Update item
app.put('/make-server-1d4585bc/items/:id', async (c) => {
  try {
    const user = await getUserFromToken(c.req.header('Authorization'));
    
    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const itemId = c.req.param('id');
    const body = await c.req.json();
    const key = `user:${user.id}:items`;
    
    const existingItems = await kv.get(key) || [];
    const itemIndex = existingItems.findIndex((item: any) => item.id === itemId);
    
    if (itemIndex === -1) {
      return c.json({ error: 'Item not found' }, 404);
    }
    
    existingItems[itemIndex] = {
      ...existingItems[itemIndex],
      ...body,
      updatedAt: new Date().toISOString()
    };
    
    await kv.set(key, existingItems);
    
    return c.json({ item: existingItems[itemIndex] });
  } catch (error) {
    console.error('Error updating item:', error);
    return c.json({ error: 'Error updating item' }, 500);
  }
});

// Delete item
app.delete('/make-server-1d4585bc/items/:id', async (c) => {
  try {
    const user = await getUserFromToken(c.req.header('Authorization'));
    
    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const itemId = c.req.param('id');
    const key = `user:${user.id}:items`;
    
    const existingItems = await kv.get(key) || [];
    const updatedItems = existingItems.filter((item: any) => item.id !== itemId);
    
    await kv.set(key, updatedItems);
    
    return c.json({ success: true });
  } catch (error) {
    console.error('Error deleting item:', error);
    return c.json({ error: 'Error deleting item' }, 500);
  }
});

// Upload image
app.post('/make-server-1d4585bc/upload-image', async (c) => {
  try {
    const user = await getUserFromToken(c.req.header('Authorization'));
    
    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401);
    }

    const body = await c.req.json();
    const { image, fileName } = body;

    if (!image || !fileName) {
      return c.json({ error: 'Image and fileName are required' }, 400);
    }

    // Convert base64 to blob
    const base64Data = image.split(',')[1];
    const buffer = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0));
    
    const filePath = `${user.id}/${Date.now()}_${fileName}`;
    
    const { error: uploadError } = await supabase.storage
      .from(BUCKET_NAME)
      .upload(filePath, buffer, {
        contentType: 'image/jpeg',
        upsert: false
      });

    if (uploadError) {
      console.error('Upload error:', uploadError);
      return c.json({ error: 'Error uploading image' }, 500);
    }

    // Get signed URL
    const { data: signedUrlData, error: urlError } = await supabase.storage
      .from(BUCKET_NAME)
      .createSignedUrl(filePath, 31536000); // 1 year

    if (urlError) {
      console.error('Signed URL error:', urlError);
      return c.json({ error: 'Error creating signed URL' }, 500);
    }

    return c.json({ 
      url: signedUrlData.signedUrl,
      path: filePath
    });
  } catch (error) {
    console.error('Image upload error:', error);
    return c.json({ error: 'Error uploading image' }, 500);
  }
});

// Health check
app.get('/make-server-1d4585bc/health', (c) => {
  return c.json({ status: 'ok', timestamp: new Date().toISOString() });
});

Deno.serve(app.fetch);
