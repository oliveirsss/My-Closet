import { useState, useEffect } from "react";
import { LoginScreen } from "./features/auth/LoginScreen";
import { LoadingScreen } from "./components/LoadingScreen";
import { Dashboard } from "./features/dashboard/Dashboard";
import { Inventory } from "./features/inventory/Inventory";
import { ItemDetail } from "./features/inventory/ItemDetail";
import { ImageSearch } from "./features/search/ImageSearch";
import { supabase } from "./lib/supabase";
import * as api from "./services/api";
import { UserType, Screen, ClothingItem } from "./types";

function App() {
  const [userType, setUserType] = useState<UserType>(null);
  const [currentScreen, setCurrentScreen] = useState<Screen>("login");
  const [selectedItem, setSelectedItem] = useState<ClothingItem | null>(null);
  const [items, setItems] = useState<ClothingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  // viewMode: 'personal' (My Closet) or 'community' (Our Closet)
  const [viewMode, setViewMode] = useState<"personal" | "community">("personal");
  const [showLikedOnly, setShowLikedOnly] = useState(false); // New state for Liked Items filter

  const [ownerFilter, setOwnerFilter] = useState<{
    id: string;
    name: string;
    avatar?: string;
  } | null>(null);

  // 1. Session Check & Auth Listener
  useEffect(() => {
    // Check initial session
    checkSession();

    // Listen for auth changes (token refresh, sign out, etc.)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.access_token) {
        api.setAccessToken(session.access_token);
        setUserId(session.user.id);
        // Only set type/screen if not already set (to avoid resetting state on refresh)
        if (!userType) {
          setUserType("client");
          setCurrentScreen("dashboard");
        }
      } else {
        // Handle logout if needed
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // 2. Load Items on state change
  useEffect(() => {
    if (userType) {
      loadItems();
    }
  }, [userType, userId, viewMode, showLikedOnly]); // Added showLikedOnly dependency

  async function checkSession() {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        api.setAccessToken(session.access_token);
        setUserId(session.user.id);
        setUserType("client");
        setCurrentScreen("dashboard");
      } else {
        // No session, stop loading immediately
        setLoading(false);
      }
    } catch (error) {
      console.error("Error checking session:", error);
      setLoading(false);
    }
    // Removed finally block that accessed 'session' incorrectly
  }

  async function loadItems() {
    setLoading(true); // Show loading screen whenever fetching items (switching views etc)
    try {
      if (userType === "visitor") {
        const { items: loadedItems } = await api.getPublicItems();
        setItems(loadedItems);
      } else if (userType === "client" && userId) {
        if (viewMode === "community") {
          if (showLikedOnly) {
            const { items: loadedItems } = await api.getLikedItems();
            setItems(loadedItems);
          } else {
            const { items: loadedItems } = await api.getPublicItems();
            setItems(loadedItems);
          }
        } else {
          // Personal Closet
          const { items: loadedItems } = await api.getItems();
          if (showLikedOnly) {
            setItems(loadedItems.filter(i => i.favorite));
          } else {
            setItems(loadedItems);
          }
        }
      }
    } catch (error) {
      console.error("Error loading items:", error);
    } finally {
      // Turn off global loading only after items are fetched
      setLoading(false);
    }
  }

  const handleLogin = async (
    type: UserType,
    email?: string,
    password?: string,
  ) => {
    if (type === "visitor") {
      setUserType(type);
      setViewMode("community"); // FORCE COMMUNITY VIEW FOR VISITORS
      setCurrentScreen("inventory");
      return;
    }
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
          setUserType("client");
          setCurrentScreen("dashboard");
        }
      } catch (error: any) {
        alert(error.message || "Erro ao fazer login");
      }
    }
  };

  const handleLogout = async () => {
    if (userType === "client") await supabase.auth.signOut();
    api.setAccessToken(null);
    setUserId(null);
    setUserType(null);
    setCurrentScreen("login");
    setSelectedItem(null);
    setItems([]);
    setOwnerFilter(null);
    setViewMode("personal");
    setShowLikedOnly(false);
  };

  const handleAddItem = async (item: ClothingItem) => {
    const { item: newItem } = await api.addItem(item);
    setItems([...items, newItem]);
  };

  const handleUpdateItem = async (updatedItem: ClothingItem) => {
    // Determine the action based on view mode (Community vs Personal)
    if (viewMode === "community") {
      // Logic for LIKES (Social)
      const isLiked = !!updatedItem.isLikedByMe;
      // NOTE: updatedItem comes with 'favorite' toggled from component, but we ignore that for social.
      // We toggle isLikedByMe based on its current value (before valid click logic, but here we assume toggle)
      // Wait, the FavoriteButton sends the item with 'favorite' property flipped if we don't change it.
      // But simplified: we just toggle the boolean.

      // Correct approach: Look at the item in state, not the incoming argument which might be misleading
      const currentItem = items.find(i => i.id === updatedItem.id);
      if (!currentItem) return;

      const wasLiked = !!currentItem.isLikedByMe;
      const newIsLiked = !wasLiked;

      // Optimistic UI Update
      setItems(items.map((i) => (i.id === updatedItem.id ? { ...i, isLikedByMe: newIsLiked } : i)));

      try {
        if (newIsLiked) {
          await api.likeItem(updatedItem.id);
        } else {
          await api.unlikeItem(updatedItem.id);
        }
      } catch (error) {
        // Revert on error
        console.error("Error toggling like:", error);
        setItems(items.map((i) => (i.id === updatedItem.id ? currentItem : i)));
      }

    } else {
      // Logic for FAVORITES (Personal Owner)
      const { item } = await api.updateItem(updatedItem.id, updatedItem);
      setItems(items.map((i) => (i.id === item.id ? item : i)));
      if (selectedItem?.id === item.id) setSelectedItem(item);
    }
  };

  const handleDeleteItem = async (id: string) => {
    await api.deleteItem(id);
    setItems(items.filter((item) => item.id !== id));
    setSelectedItem(null);
    setCurrentScreen("inventory");
  };

  const handleViewOwnerProfile = (ownerId: string, ownerName: string, ownerAvatar?: string) => {
    setOwnerFilter({ id: ownerId, name: ownerName, avatar: ownerAvatar });
    setSelectedItem(null);
    setCurrentScreen("inventory");
  };

  const handleViewDetail = (item: ClothingItem) => {
    setSelectedItem(item);
    setCurrentScreen("detail");
  };

  if (loading) return <LoadingScreen />;

  if (currentScreen === "login") return <LoginScreen onLogin={handleLogin} />;

  if (currentScreen === "detail" && selectedItem) {
    return (
      <ItemDetail
        item={selectedItem}
        onBack={() => setCurrentScreen("inventory")}
        onUpdate={handleUpdateItem}
        onDelete={handleDeleteItem}
        isVisitor={userType === "visitor"}
        onViewOwner={handleViewOwnerProfile}
        currentUserId={userId}
      />
    );
  }

  if (currentScreen === "search")
    return (
      <ImageSearch
        items={items}
        onBack={() => setCurrentScreen("inventory")}
        onViewItem={handleViewDetail}
      />
    );

  if (currentScreen === "dashboard" && userType === "client") {
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
      ownerFilter={ownerFilter}
      onClearOwnerFilter={() => setOwnerFilter(null)}
      onToggleFavorite={handleUpdateItem}
      onViewOwner={handleViewOwnerProfile}
      viewMode={viewMode}
      onToggleViewMode={() => {
        setViewMode(prev => prev === "personal" ? "community" : "personal");
        setShowLikedOnly(false); // Reset filter when switching modes
      }}
      showLikedOnly={showLikedOnly}
      onToggleLikedOnly={() => setShowLikedOnly(!showLikedOnly)}
    />
  );
}

export default App;
