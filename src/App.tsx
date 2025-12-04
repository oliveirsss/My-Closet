import { useState, useEffect } from 'react';
import { LoginScreen } from './features/auth/LoginScreen';
import { Dashboard } from './features/dashboard/Dashboard';
import { Inventory } from './features/inventory/Inventory';
import { ItemDetail } from './features/inventory/ItemDetail';
import { ImageSearch } from './features/search/ImageSearch';
import { supabase } from './lib/supabase';
import * as api from './services/api';
import { UserType, Screen, ClothingItem } from './types';

function App() {
  const [userType, setUserType] = useState<UserType>(null);
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [selectedItem, setSelectedItem] = useState<ClothingItem | null>(null);
  const [items, setItems] = useState<ClothingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  // NOVO: Estado para filtrar por um utilizador específico (Perfil)
  const [ownerFilter, setOwnerFilter] = useState<{id: string, name: string} | null>(null);

  useEffect(() => {
    checkSession();
  }, []);

  useEffect(() => {
    if (userType) {
      loadItems();
    }
  }, [userType, userId]);

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
      if (userType === 'visitor') {
        const { items: loadedItems } = await api.getPublicItems();
        setItems(loadedItems);
      } else if (userType === 'client' && userId) {
        const { items: loadedItems } = await api.getItems();
        setItems(loadedItems);
      }
    } catch (error) {
      console.error('Error loading items:', error);
    }
  }

  const handleLogin = async (type: UserType, email?: string, password?: string) => {
    if (type === 'visitor') {
      setUserType(type);
      setCurrentScreen('inventory');
      return;
    }
    if (email && password) {
      try {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        if (data.session?.access_token) {
          api.setAccessToken(data.session.access_token);
          setUserId(data.user.id);
          setUserType('client');
          setCurrentScreen('dashboard');
        }
      } catch (error: any) {
        alert(error.message || 'Erro ao fazer login');
      }
    }
  };

  const handleLogout = async () => {
    if (userType === 'client') await supabase.auth.signOut();
    api.setAccessToken(null);
    setUserId(null);
    setUserType(null);
    setCurrentScreen('login');
    setSelectedItem(null);
    setItems([]);
    setOwnerFilter(null); // Limpar filtro
  };

  // ... Funções addItem, updateItem, deleteItem mantêm-se iguais ...
  // (Vou omitir para poupar espaço, copia do teu anterior)
  const handleAddItem = async (item: ClothingItem) => {
    const { item: newItem } = await api.addItem(item);
    setItems([...items, newItem]);
  };
  const handleUpdateItem = async (updatedItem: ClothingItem) => {
    const { item } = await api.updateItem(updatedItem.id, updatedItem);
    setItems(items.map(i => i.id === item.id ? item : i));
    if (selectedItem?.id === item.id) setSelectedItem(item);
  };
  const handleDeleteItem = async (id: string) => {
    await api.deleteItem(id);
    setItems(items.filter(item => item.id !== id));
    setSelectedItem(null);
    setCurrentScreen('inventory');
  };

  // NOVO: Função para ver perfil de outro user
  const handleViewOwnerProfile = (ownerId: string, ownerName: string) => {
    setOwnerFilter({ id: ownerId, name: ownerName });
    setSelectedItem(null);
    setCurrentScreen('inventory');
  };

  const handleViewDetail = (item: ClothingItem) => {
    setSelectedItem(item);
    setCurrentScreen('detail');
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center">A carregar...</div>;
  if (currentScreen === 'login') return <LoginScreen onLogin={handleLogin} />;

  if (currentScreen === 'detail' && selectedItem) {
    return (
      <ItemDetail
        item={selectedItem}
        onBack={() => setCurrentScreen('inventory')}
        onUpdate={handleUpdateItem}
        onDelete={handleDeleteItem}
        isVisitor={userType === 'visitor'}
        onViewOwner={handleViewOwnerProfile} // <--- Passar a função nova
      />
    );
  }

  if (currentScreen === 'search') return <ImageSearch items={items} onBack={() => setCurrentScreen('inventory')} onViewItem={handleViewDetail} />;

  if (currentScreen === 'dashboard' && userType === 'client') {
    return <Dashboard items={items} onNavigate={setCurrentScreen} onLogout={handleLogout} onViewItem={handleViewDetail} />;
  }

  return (
    <Inventory
      items={items}
      userType={userType}
      onNavigate={setCurrentScreen}
      onLogout={handleLogout}
      onAddItem={handleAddItem}
      onViewItem={handleViewDetail}
      // NOVAS PROPS PARA FILTRAGEM
      ownerFilter={ownerFilter}
      onClearOwnerFilter={() => setOwnerFilter(null)}
    />
  );
}

export default App;