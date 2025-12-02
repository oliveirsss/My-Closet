import { useState, useEffect } from 'react';
import { LoginScreen } from './features/auth/LoginScreen';
import { Dashboard } from './features/dashborad/Dashboard';
import { Inventory } from './features/inventory/Inventory';
import { ItemDetail } from './features/inventory/ItemDetail';
import { ImageSearch } from './features/search/ImageSearch';
import { supabase } from './lib/supabase';
import * as api from './services/api';

export type UserType = 'visitor' | 'client' | null;

export interface ClothingItem {
  id: string;
  name: string;
  brand: string;
  size: string;
  type: string;
  layer: 1 | 2 | 3;
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

export type Screen = 'login' | 'dashboard' | 'inventory' | 'detail' | 'search';

function App() {
  const [userType, setUserType] = useState<UserType>(null);
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [selectedItem, setSelectedItem] = useState<ClothingItem | null>(null);
  const [items, setItems] = useState<ClothingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    checkSession();
  }, []);

  // Load items when user is authenticated
  useEffect(() => {
    if (userId && userType === 'client') {
      loadItems();
    }
  }, [userId, userType]);

  async function checkSession() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        api.setAccessToken(session.access_token);
        setUserId(session.user.id);
        setUserType('client');
        setCurrentScreen('dashboard');
      }
    } catch (error) {
      console.error('Error checking session:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadItems() {
    try {
      const { items: loadedItems } = await api.getItems();
      setItems(loadedItems);
    } catch (error) {
      console.error('Error loading items:', error);
    }
  }

  const handleLogin = async (type: UserType, email?: string, password?: string) => {
    if (type === 'visitor') {
      setUserType(type);
      setCurrentScreen('inventory');
      // Load demo data for visitors
      setItems([
        {
          id: '1',
          name: 'Casaco North Face Azul',
          brand: 'The North Face',
          size: 'M',
          type: 'Casaco',
          layer: 3,
          materials: ['Poliéster', 'Gore-Tex'],
          weight: 450,
          tempMin: -5,
          tempMax: 10,
          waterproof: true,
          windproof: true,
          seasons: ['Outono', 'Inverno'],
          image: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400',
          status: 'clean',
          favorite: true
        },
        {
          id: '2',
          name: 'Camisola Lã Merino',
          brand: 'Patagonia',
          size: 'M',
          type: 'Camisola',
          layer: 2,
          materials: ['Lã Merino'],
          weight: 280,
          tempMin: 5,
          tempMax: 15,
          waterproof: false,
          windproof: false,
          seasons: ['Outono', 'Inverno', 'Primavera'],
          image: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400',
          status: 'clean',
          favorite: true
        }
      ]);
      return;
    }

    // Client login
    if (email && password) {
      try {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) throw error;

        if (data.session?.access_token) {
          api.setAccessToken(data.session.access_token);
          setUserId(data.user.id);
          setUserType('client');
          setCurrentScreen('dashboard');
        }
      } catch (error: any) {
        console.error('Login error:', error);
        alert(error.message || 'Erro ao fazer login');
      }
    }
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      api.setAccessToken(null);
      setUserId(null);
      setUserType(null);
      setCurrentScreen('login');
      setSelectedItem(null);
      setItems([]);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const handleAddItem = async (item: ClothingItem) => {
    try {
      const { item: newItem } = await api.addItem(item);
      setItems([...items, newItem]);
    } catch (error) {
      console.error('Error adding item:', error);
      alert('Erro ao adicionar peça');
    }
  };

  const handleUpdateItem = async (updatedItem: ClothingItem) => {
    try {
      const { item } = await api.updateItem(updatedItem.id, updatedItem);
      setItems(items.map(i => i.id === item.id ? item : i));
      setSelectedItem(item);
    } catch (error) {
      console.error('Error updating item:', error);
      alert('Erro ao atualizar peça');
    }
  };

  const handleDeleteItem = async (id: string) => {
    try {
      await api.deleteItem(id);
      setItems(items.filter(item => item.id !== id));
      setSelectedItem(null);
      setCurrentScreen('inventory');
    } catch (error) {
      console.error('Error deleting item:', error);
      alert('Erro ao apagar peça');
    }
  };

  const handleViewDetail = (item: ClothingItem) => {
    setSelectedItem(item);
    setCurrentScreen('detail');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-emerald-700 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-stone-600">A carregar...</p>
        </div>
      </div>
    );
  }

  if (currentScreen === 'login') {
    return <LoginScreen onLogin={handleLogin} />;
  }

  if (currentScreen === 'detail' && selectedItem) {
    return (
      <ItemDetail
        item={selectedItem}
        onBack={() => setCurrentScreen('inventory')}
        onUpdate={handleUpdateItem}
        onDelete={handleDeleteItem}
      />
    );
  }

  if (currentScreen === 'search') {
    return (
      <ImageSearch
        items={items}
        onBack={() => setCurrentScreen('inventory')}
        onViewItem={handleViewDetail}
      />
    );
  }

  if (currentScreen === 'dashboard' && userType === 'client') {
    return (
      <Dashboard
        items={items}
        onNavigate={setCurrentScreen}
        onLogout={handleLogout}
        onViewItem={handleViewDetail}
      />
    );
  }

  return (
    <Inventory
      items={items}
      userType={userType}
      onNavigate={setCurrentScreen}
      onLogout={handleLogout}
      onAddItem={handleAddItem}
      onViewItem={handleViewDetail}
    />
  );
}

export default App;