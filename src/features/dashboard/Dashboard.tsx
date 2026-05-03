import { useState, useEffect } from "react";
// Tipos
import { ClothingItem, Screen } from "../../types";
// Componentes UI
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
// Componente de Edição de Perfil
import { EditProfileDialog } from "../auth/EditProfileDialog";
// Componente de Viagem
import { TravelPlannerDialog } from "./TravelPlannerDialog";
// Componente Mannequin para Visualização
import { OutfitMannequin } from "../../components/OutfitMannequin";
// Chat Dialog 
import { AIChatDialog } from "./AIChatDialog";

// Ícones
import {
  Cloud,
  CloudRain,
  Sun,
  Droplets,
  Wind,
  Layers,
  Search,
  LogOut,
  TrendingUp,
  MapPin,
  Edit2,
  Plane,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Package,
  RefreshCw,
  Crown,
  Sparkles,
  MessageCircle,
  CalendarDays,
  PartyPopper,
} from "lucide-react";
// API
import { supabase } from "../../lib/supabase";
import * as api from "../../services/api";

// --- CONFIGURAÇÃO DA API ---
const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || "";
const API_URL = "https://api.openweathermap.org/data/2.5/weather";

interface DashboardProps {
  items: ClothingItem[];
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onViewItem: (item: ClothingItem) => void;
  aiOutfitItems: ClothingItem[] | null;
  setAiOutfitItems: (items: ClothingItem[] | null) => void;
}

// tipo local para o perfil no dashboard
type UserProfileState = {
  name: string;
  avatar_url: string;
  bio: string;
  location: string;
  id: string;
};

export function Dashboard({
  items,
  onNavigate,
  onLogout,
  onViewItem,
  aiOutfitItems,
  setAiOutfitItems,
}: DashboardProps) {
  // 1. ESTADOS (Profile, Travel, Weather)
  const [userProfile, setUserProfile] = useState<UserProfileState>({
    name: "Utilizador",
    avatar_url: "",
    bio: "",
    location: "",
    id: "",
  });

  const [isTopCreator, setIsTopCreator] = useState(false);

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isTravelOpen, setIsTravelOpen] = useState(false);

  const [weather, setWeather] = useState({
    temp: 0,
    humidity: 0,
    condition: "loading",
    rain: false,
    windSpeed: 0,
    city: "A localizar...",
    loading: true,
  });

  const [isAIChatOpen, setIsAIChatOpen] = useState(false);

  // Wear confirmation feedback
  const [wearConfirmed, setWearConfirmed] = useState(false);
  const [wearLoading, setWearLoading] = useState(false);

  // Wear history (loaded on demand)
  const [wearHistory, setWearHistory] = useState<Array<{ date: string; items: any[] }> | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // 2. Carregar Perfil (Direto do Supabase para ser mais robusto)
  // 2. Carregar Perfil (Via API para consistência com o backend)
  useEffect(() => {
    const loadProfile = async () => {
      try {
        // Tenta carregar do backend (onde os updates são gravados)
        const { profile } = await api.getProfile();

        if (profile) {
          setUserProfile({
            name: profile.name || "Utilizador",
            avatar_url: profile.avatar_url || "",
            bio: profile.bio || "",
            location: profile.location || "",
            id: profile.user_id,
          });
        }
      } catch (error) {
        console.error("Erro ao carregar perfil da API:", error);

        // Fallback: Tenta carregar do Supabase se a API falhar
        const { data: { user } } = await supabase.auth.getUser();
        if (user?.user_metadata) {
          setUserProfile({
            name: user.user_metadata.name || "Utilizador",
            avatar_url: user.user_metadata.avatar_url || "",
            bio: user.user_metadata.bio || "",
            location: user.user_metadata.location || "",
            id: user.id || "",
          });
        }
      }
    };
    loadProfile();
  }, []);

  // handler para aplicar updates vindos do modal imediatamente
  const handleProfileUpdated = (updated: Partial<UserProfileState>) => {
    setUserProfile((prev) => ({
      ...prev,
      ...updated,
    }));
  };

  // 3. Carregar Tempo e Top Creator
  useEffect(() => {
    const checkTopCreator = async () => {
      try {
        if (!userProfile.id) return;
        const { items: publicItems } = await api.getPublicItems();
        const ownerCounts: Record<string, number> = {};
        publicItems.forEach(item => { if (item.ownerId) ownerCounts[item.ownerId] = (ownerCounts[item.ownerId] || 0) + 1; });
        const sortedOwners = Object.entries(ownerCounts).sort(([, a], [, b]) => b - a);
        if (sortedOwners.length > 0) {
          const [topCreatorId] = sortedOwners[0];
          setIsTopCreator(topCreatorId === userProfile.id);
        }
      } catch (err) { console.error(err); }
    };
    checkTopCreator();
  }, [userProfile.id]);

  // 4. Carregar Tempo (Sempre que Location mudar)
  useEffect(() => {
    // Se o utilizador tiver uma localização explícita no perfil, usamos essa
    if (userProfile.location && userProfile.location.trim() !== "") {
      fetchWeatherByCity(userProfile.location);
      return;
    }

    // Senão tentamos o GPS
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          fetchWeatherByCoords(latitude, longitude);
        },
        (error) => {
          console.error("Erro de localização:", error);
          fetchWeatherByCoords(38.7169, -9.1399); // Fallback Lisboa
        },
      );
    } else {
      fetchWeatherByCoords(38.7169, -9.1399);
    }
  }, [userProfile.location]);

  const processWeatherResponse = async (res: Response, fallbackCity?: string) => {
    if (!res.ok) throw new Error("Weather API failed");
    const data = await res.json();

    const code = data.weather[0].id;
    let condition = "cloudy";
    let isRaining = false;

    if (code === 800) condition = "sunny";
    else if (code >= 200 && code <= 531) {
      condition = "rainy";
      isRaining = true;
    }

    setWeather({
      temp: Math.round(data.main.temp),
      humidity: data.main.humidity,
      condition,
      rain: isRaining,
      windSpeed: data.wind?.speed || 0, // Wind speed in m/s
      city: data.name || fallbackCity || "Desconhecido",
      loading: false,
    });
  };

  const fetchWeatherByCoords = async (lat: number, lon: number) => {
    if (!API_KEY) {
      setWeather((prev) => ({ ...prev, temp: 18, windSpeed: 0, city: "Modo Demo", loading: false }));
      return;
    }
    try {
      const res = await fetch(`${API_URL}?lat=${lat}&lon=${lon}&units=metric&appid=${API_KEY}&lang=pt`);
      await processWeatherResponse(res);
    } catch (error) {
      setWeather((prev) => ({ ...prev, loading: false, city: "Erro API" }));
    }
  };

  const fetchWeatherByCity = async (city: string) => {
    if (!API_KEY) {
      setWeather((prev) => ({ ...prev, temp: 18, windSpeed: 0, city: city, loading: false }));
      return;
    }
    try {
      const res = await fetch(`${API_URL}?q=${encodeURIComponent(city)}&units=metric&appid=${API_KEY}&lang=pt`);
      await processWeatherResponse(res, city);
    } catch (error) {
      console.error("Erro ao procurar tempo por cidade, fallback para GPS:", error);
      // Fallback para as coordenadas
      fetchWeatherByCoords(38.7169, -9.1399);
    }
  };

  const handleRegenerateAiOutfit = () => {
    setWearConfirmed(false);
    setIsAIChatOpen(true);
  };

  // Helper to convert flat AI items to LayerRecommendation format
  const buildLayerFromAiItems = (aiItems: ClothingItem[]): { baseLayer: any; insulationLayer: any; outerLayer: any } => {
    const isBottom = (item: ClothingItem) => {
      const s = (item.name + ' ' + (item.type || '')).toLowerCase();
      return s.includes('calça') || s.includes('calca') || s.includes('short') || s.includes('jeans') || s.includes('trousers') || s.includes('pant') || s.includes('skirt') || s.includes('saia');
    };
    const isShoe = (item: ClothingItem) => {
      const s = (item.name + ' ' + (item.type || '')).toLowerCase();
      return s.includes('sapato') || s.includes('sapatilha') || s.includes('ténis') || s.includes('tenis') || s.includes('sneaker') || s.includes('bota') || s.includes('calçado') || s.includes('shoe') || s.includes('jordan') || s.includes('dunk') || s.includes('af1');
    };

    const baseItems: any[] = [];
    const insulationItems: any[] = [];
    const outerItems: any[] = [];

    aiItems.forEach(item => {
      const layer = item.layer || 1;
      
      if (layer === 3) {
        // Camada 3: Proteção Externa (Casacos, sapatilhas, acessórios)
        const category = isShoe(item) ? 'shoes' : 'jacket';
        outerItems.push({ item, reasoning: '', category });
      } else if (layer === 2 || isBottom(item)) {
        // Camada 2: Intermédia (Camisolas quentes, calças de inverno, etc)
        // OBS: Calças/Calções são sempre Camada 2 para apresentar na coluna certa.
        insulationItems.push({ item, reasoning: '' });
      } else {
        // Camada 1: Base (T-shirts, tops, calções leves, etc)
        baseItems.push({ item, reasoning: '' });
      }
    });

    return {
      baseLayer: { items: baseItems, reasoning: '', isMissing: baseItems.length === 0 },
      insulationLayer: { items: insulationItems, reasoning: '', isMissing: insulationItems.length === 0 },
      outerLayer: { items: outerItems, reasoning: '', isMissing: outerItems.length === 0 },
    };
  };

  const currentOutfit = aiOutfitItems
    ? buildLayerFromAiItems(aiOutfitItems)
    : {
        baseLayer: { items: [], reasoning: '', isMissing: true },
        insulationLayer: { items: [], reasoning: '', isMissing: true },
        outerLayer: { items: [], reasoning: '', isMissing: true },
      };

  // All item ids in the current outfit (for wear confirmation)
  const currentOutfitItemIds = aiOutfitItems
    ? aiOutfitItems.map(i => i.id).filter(Boolean)
    : [];

  useEffect(() => {
    console.log("[Dashboard] daily_suggestion_item_ids", currentOutfitItemIds);
  }, [currentOutfitItemIds.join(",")]);

  const handleWearConfirm = async () => {
    if (wearLoading || wearConfirmed || currentOutfitItemIds.length === 0) return;
    setWearLoading(true);
    try {
      await api.recordOutfitUsage(currentOutfitItemIds);
      setWearConfirmed(true);
      // Refresh history if visible
      if (wearHistory !== null) loadHistory();
    } catch (e) {
      console.error('Erro ao registar uso:', e);
    } finally {
      setWearLoading(false);
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await api.getWearHistory(30);
      setWearHistory(res.history || []);
    } catch (e) {
      console.error('Erro ao carregar histórico:', e);
      setWearHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleAcceptAiOutfit = (outfitItems: ClothingItem[]) => {
    console.log("[Dashboard] accepted_suggestion_item_ids", outfitItems.map(item => item.id));
    setAiOutfitItems(outfitItems);
    setWearConfirmed(false);
  };

  const cleanItems = items.filter((item) => item.status === "clean").length;
  const dirtyItems = items.filter((item) => item.status === "dirty").length;
  const missingLayers = [1, 2, 3].filter(
    (layer) =>
      !items.some((item) => item.layer === layer && item.status === "clean"),
  );

  const WeatherIcon =
    weather.condition === "sunny" ? Sun : weather.rain ? CloudRain : Cloud;
  const todayDate = new Date().toLocaleDateString("pt-PT", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12">
              {userProfile.avatar_url ? (
                <div
                  className="w-12 h-12 rounded-full overflow-hidden border border-emerald-700 bg-stone-100 shadow-sm"
                >
                  <img
                    src={api.getAssetUrl(userProfile.avatar_url)}
                    alt="Avatar"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // Se falhar e a URL não for vazia, esconde
                      console.error("Erro a carregar avatar:", userProfile.avatar_url);
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-emerald-700 flex items-center justify-center text-white text-xl font-bold shadow-sm">
                  {userProfile.name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>

            <div>
              <h1 className="text-xl text-emerald-900 font-semibold flex items-center gap-2">
                Bem-vindo de volta!
                {isTopCreator && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold border border-amber-200 uppercase tracking-wide">
                    <Sparkles className="w-3 h-3" />
                    Top Creator
                  </span>
                )}
              </h1>
              <div
                className="flex items-center gap-2 group cursor-pointer"
                onClick={() => setIsProfileOpen(true)}
                title="Clique para editar perfil"
              >
                <p className="text-sm text-stone-600 group-hover:text-emerald-700 transition-colors font-medium">
                  {userProfile.name}
                </p>
                <Edit2 className="h-3 w-3 text-stone-400 opacity-0 group-hover:opacity-100 transition-all" />
              </div>

              {userProfile.location && (
                <div className="flex items-center gap-1 mt-0.5 text-xs text-stone-400">
                  <MapPin className="h-3 w-3" />
                  <span>{userProfile.location}</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onNavigate("inventory")}>
              <Layers className="mr-2 h-4 w-4" /> Inventário
            </Button>
            <Button variant="outline" onClick={() => onNavigate("search")}>
              <Search className="mr-2 h-4 w-4" /> Pesquisar
            </Button>

            <Button variant="outline" onClick={() => setIsTravelOpen(true)}>
              <Plane className="mr-2 h-4 w-4" /> Viagem
            </Button>
            
            <Button 
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
              onClick={() => setIsAIChatOpen(true)}
            >
              <MessageCircle className="mr-2 h-4 w-4" /> AI Style Chat
            </Button>

            <Button variant="ghost" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Widget Tempo */}
        <Card
          className="text-white p-6 border-0 shadow-lg"
          style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #2563eb 100%)' }}
        >
          <div className="flex items-start justify-between">
            <div>
              {weather.loading ? (
                <div className="animate-pulse">A carregar tempo...</div>
              ) : (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <WeatherIcon className="h-10 w-10" />
                    <span className="text-6xl font-bold tracking-tighter">
                      {weather.temp}°C
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mb-1 text-sky-50">
                    <MapPin className="h-4 w-4" />
                    <p className="text-lg font-medium">{weather.city}</p>
                  </div>
                  <p className="text-sky-100 capitalize text-sm">{todayDate}</p>
                </>
              )}
            </div>

            <div className="text-right space-y-3">
              <div className="flex items-center gap-2 justify-end">
                <Droplets className="h-5 w-5" />
                <span className="font-medium">
                  {weather.humidity}% Humidade
                </span>
              </div>
              {weather.rain && (
                <div className="flex items-center gap-2 justify-end bg-white/20 px-3 py-1.5 rounded-full backdrop-blur-sm">
                  <CloudRain className="h-4 w-4" />
                  <span className="text-sm font-medium">Chuva Prevista</span>
                </div>
              )}
              {(weather.temp < 10 ||
                (weather.windSpeed && weather.windSpeed >= 10)) && (
                  <div className="flex items-center gap-2 justify-end">
                    <Wind className="h-5 w-5" />
                    <span>
                      {weather.windSpeed && weather.windSpeed >= 10
                        ? `Vento Forte (${Math.round(weather.windSpeed)} m/s)`
                        : "Vento Frio"}
                    </span>
                  </div>
                )}
            </div>
          </div>
        </Card>

        {/* Sugestão do Dia */}
        <section>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h2 className="text-2xl font-semibold text-emerald-900 flex items-center gap-2">
              <span className="bg-emerald-100 p-1.5 rounded-md">
                <TrendingUp className="h-5 w-5 text-emerald-700" />
              </span>
              Sugestão do Dia
            </h2>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerateAiOutfit}
                className="text-stone-600 border-stone-200 hover:bg-stone-50"
              >
                <MessageCircle className="mr-2 h-4 w-4" />
                Mudar (AI)
              </Button>
            </div>
          </div>

          {!aiOutfitItems ? (
            <div className="flex flex-col items-center justify-center p-12 bg-white rounded-xl border border-stone-200 shadow-sm min-h-[400px]">
              <Sparkles className="h-10 w-10 text-emerald-500 mb-4" />
              <p className="text-lg font-medium text-stone-700 text-center">
                Peça uma sugestão no AI Style Assistant para gerar um outfit.
              </p>
              <Button
                className="mt-5 bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => setIsAIChatOpen(true)}
              >
                <MessageCircle className="mr-2 h-4 w-4" />
                Abrir AI Style Assistant
              </Button>
            </div>
          ) : (
            <OutfitMannequin
              baseLayer={currentOutfit.baseLayer}
              insulationLayer={currentOutfit.insulationLayer}
              outerLayer={currentOutfit.outerLayer}
              onViewItem={onViewItem}
            />
          )}

          {/* Botão de confirmação de uso */}
          <div className="mt-4 flex flex-col sm:flex-row items-center gap-3">
            <button
              onClick={handleWearConfirm}
              disabled={wearLoading || wearConfirmed || currentOutfitItemIds.length === 0}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-sm ${
                currentOutfitItemIds.length === 0
                  ? 'bg-stone-100 text-stone-400 border border-stone-200 cursor-not-allowed'
                  : wearConfirmed
                  ? 'bg-emerald-100 text-emerald-700 border border-emerald-200 cursor-default'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20 active:scale-95'
              }`}
            >
              {wearConfirmed ? (
                <><PartyPopper className="w-4 h-4" /> Outfit registado para hoje!</>
              ) : wearLoading ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> A registar...</>
              ) : (
                <><CheckCircle className="w-4 h-4" /> Usei este outfit hoje!</>
              )}
            </button>

            <button
              onClick={() => wearHistory === null ? loadHistory() : setWearHistory(null)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-stone-600 border border-stone-200 hover:bg-stone-50 transition-all"
            >
              <CalendarDays className="w-4 h-4" />
              {wearHistory !== null ? 'Fechar histórico' : 'Ver histórico'}
            </button>
          </div>

          {/* Mini histórico */}
          {wearHistory !== null && (
            <div className="mt-4 rounded-xl border border-stone-200 bg-white overflow-hidden">
              <div className="px-4 py-3 bg-stone-50 border-b border-stone-200 flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-stone-500" />
                <span className="text-sm font-semibold text-stone-700">O que usei nos últimos 30 dias</span>
              </div>
              {historyLoading ? (
                <div className="p-6 text-center text-stone-400 text-sm">A carregar...</div>
              ) : wearHistory.length === 0 ? (
                <div className="p-6 text-center text-stone-400 text-sm">Ainda não há registos. Clica em "Usei este outfit hoje!" para começar.</div>
              ) : (
                <div className="divide-y divide-stone-100 max-h-72 overflow-y-auto">
                  {wearHistory.map(entry => (
                    <div key={entry.date} className="px-4 py-3 flex items-start gap-4">
                      <span className="text-xs font-semibold text-stone-500 min-w-[4.5rem] pt-0.5">
                        {new Date(entry.date + 'T12:00:00').toLocaleDateString('pt-PT', { weekday: 'short', day: 'numeric', month: 'short' })}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {entry.items.map((item, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1 text-xs bg-emerald-50 text-emerald-800 border border-emerald-100 px-2 py-1 rounded-full">
                            {item.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Resumo Inventário */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-stone-700">
            Resumo do Inventário
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <StatCard label="Total Peças" value={items.length} type="total" />

            <StatCard label="Limpas" value={cleanItems} type="clean" />

            <StatCard label="Para Lavar" value={dirtyItems} type="dirty" />

            <StatCard
              label="Em Falta"
              value={missingLayers.length}
              type="missing"
              subtext={`Camadas: ${missingLayers.join(", ")}`}
            />
          </div>
        </section>
      </main>

      {/* --- DIALOGS --- */}
      <EditProfileDialog
        open={isProfileOpen}
        onOpenChange={setIsProfileOpen}
        userData={userProfile}
        onUpdate={handleProfileUpdated}
      />

      <TravelPlannerDialog
        open={isTravelOpen}
        onOpenChange={setIsTravelOpen}
        items={items}
      />

      <AIChatDialog
        open={isAIChatOpen}
        onOpenChange={setIsAIChatOpen}
        weather={weather}
        items={items}
        onViewItem={onViewItem}
        onAcceptOutfit={handleAcceptAiOutfit}
      />
    </div>
  );
}

// --- FUNÇÕES AUXILIARES ---

function StatCard({ label, value, type, subtext }: any) {
  const config = {
    total: {
      icon: Package,
      bg: "bg-stone-50",
      text: "text-stone-500",
    },
    clean: {
      icon: CheckCircle,
      bg: "bg-emerald-50",
      text: "text-emerald-500",
    },
    dirty: {
      icon: AlertTriangle,
      bg: "bg-amber-50",
      text: "text-amber-500",
    },
    missing: {
      icon: XCircle,
      bg: "bg-red-50",
      text: "text-red-500",
    },
  };

  const Icon = config[type].icon;

  return (
    <div
      className={`
        p-5
        rounded-2xl
        shadow-sm
        border border-stone-200
        ${config[type].bg}
        flex
        flex-col
        items-center
        justify-between
        min-h-[140px]
      `}
    >
      {/* header */}
      <div className="flex items-center justify-between w-full mb-2">
        <span className="text-sm font-medium text-stone-700">{label}</span>

        <Icon className={`w-5 h-5 ${config[type].text}`} />
      </div>

      {/* número CENTRADO vertical e horizontal */}
      <div className="flex flex-1 items-center justify-center w-full">
        <p className="text-5xl font-extrabold text-stone-900 leading-none">
          {value}
        </p>
      </div>

      {subtext && (
        <p className="text-xs text-stone-500 text-center mt-1">{subtext}</p>
      )}
    </div>
  );
}
