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
} from "lucide-react";
// API
import { supabase } from "../../lib/supabase";
// Outfit Recommendation Service
import {
  recommendOutfit,
  WeatherData,
} from "../../services/outfitRecommendation";

// --- CONFIGURAÇÃO DA API ---
const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || "";
const API_URL = "https://api.openweathermap.org/data/2.5/weather";

interface DashboardProps {
  items: ClothingItem[];
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onViewItem: (item: ClothingItem) => void;
}

// tipo local para o perfil no dashboard
type UserProfileState = {
  name: string;
  avatar_url: string;
  bio: string;
  location: string;
};

export function Dashboard({
  items,
  onNavigate,
  onLogout,
  onViewItem,
}: DashboardProps) {
  // 1. ESTADOS (Profile, Travel, Weather)
  const [userProfile, setUserProfile] = useState<UserProfileState>({
    name: "Utilizador",
    avatar_url: "",
    bio: "",
    location: "",
  });

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

  // 2. Carregar Perfil (Direto do Supabase para ser mais robusto)
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (user?.user_metadata) {
          setUserProfile({
            name: user.user_metadata.name || "Utilizador",
            avatar_url: user.user_metadata.avatar_url || "",
            bio: user.user_metadata.bio || "",
            location: user.user_metadata.location || "",
          });
        }
      } catch (error) {
        console.error("Erro ao carregar perfil:", error);
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

  // 3. Carregar Tempo
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          fetchWeather(latitude, longitude);
        },
        (error) => {
          console.error("Erro de localização:", error);
          fetchWeather(38.7169, -9.1399); // Fallback Lisboa
        },
      );
    } else {
      fetchWeather(38.7169, -9.1399);
    }
  }, []);

  const fetchWeather = async (lat: number, lon: number) => {
    if (!API_KEY) {
      setWeather((prev) => ({
        ...prev,
        temp: 18,
        windSpeed: 0,
        city: "Modo Demo",
        loading: false,
      }));
      return;
    }

    try {
      const res = await fetch(
        `${API_URL}?lat=${lat}&lon=${lon}&units=metric&appid=${API_KEY}&lang=pt`,
      );
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
        city: data.name,
        loading: false,
      });
    } catch (error) {
      setWeather((prev) => ({ ...prev, loading: false, city: "Erro API" }));
    }
  };

  // 4. Generate Outfit Recommendation using the recommendation service
  const weatherData: WeatherData = {
    temperature: weather.temp,
    rain: weather.rain,
    windSpeed: weather.windSpeed,
    humidity: weather.humidity,
  };

  const outfitRecommendation = recommendOutfit(items, weatherData);
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
                  className={`w-12 h-12 rounded-full overflow-hidden border border-emerald-700 ${isDark ? "bg-stone-700" : "bg-stone-100"} shadow-sm`}
                >
                  <img
                    src={userProfile.avatar_url}
                    alt="Avatar"
                    className="w-full h-full object-cover"
                  />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-emerald-700 flex items-center justify-center text-white text-xl font-bold shadow-sm">
                  {userProfile.name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>

            <div>
              <h1 className="text-xl text-emerald-900 font-semibold">
                Bem-vindo de volta!
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

            <Button variant="ghost" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Widget Tempo */}
        <Card className="bg-gradient-to-br from-sky-400 to-blue-500 text-white p-6 border-0 shadow-lg">
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
          <h2 className="text-2xl font-semibold mb-4 text-emerald-900 flex items-center gap-2">
            <span className="bg-emerald-100 p-1.5 rounded-md">
              <TrendingUp className="h-5 w-5 text-emerald-700" />
            </span>
            Sugestão do Dia
          </h2>

          <OutfitMannequin
            baseLayer={outfitRecommendation.baseLayer}
            insulationLayer={outfitRecommendation.insulationLayer}
            outerLayer={outfitRecommendation.outerLayer}
            onViewItem={onViewItem}
          />
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
