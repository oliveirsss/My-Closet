import { useState, useEffect } from 'react';
// Tipos
import { ClothingItem, Screen } from '../../types';
// Componentes UI
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
// Componente de Edição de Perfil
import { EditProfileDialog } from '../auth/EditProfileDialog';
// Componente de Viagem
import { TravelPlannerDialog } from './TravelPlannerDialog';

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
  Plane
} from 'lucide-react';
// API
import { supabase } from '../../lib/supabase';

// --- CONFIGURAÇÃO DA API ---
const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || '';
const API_URL = 'https://api.openweathermap.org/data/2.5/weather';

interface DashboardProps {
  items: ClothingItem[];
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onViewItem: (item: ClothingItem) => void;
}

export function Dashboard({ items, onNavigate, onLogout, onViewItem }: DashboardProps) {
  // 1. ESTADOS (Profile, Travel, Weather)
  const [userProfile, setUserProfile] = useState({
    name: 'Utilizador',
    avatar_url: '',
    bio: '',
    location: ''
  });

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isTravelOpen, setIsTravelOpen] = useState(false);

  const [weather, setWeather] = useState({
    temp: 0,
    humidity: 0,
    condition: 'loading',
    rain: false,
    city: 'A localizar...',
    loading: true
  });

  // 2. Carregar Perfil (Direto do Supabase para ser mais robusto)
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (user?.user_metadata) {
          setUserProfile({
            name: user.user_metadata.name || 'Utilizador',
            avatar_url: user.user_metadata.avatar_url || '',
            bio: user.user_metadata.bio || '',
            location: user.user_metadata.location || ''
          });
        }
      } catch (error) {
        console.error("Erro ao carregar perfil:", error);
      }
    };
    loadProfile();
  }, []);

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
        }
      );
    } else {
      fetchWeather(38.7169, -9.1399);
    }
  }, []);

  const fetchWeather = async (lat: number, lon: number) => {
    if (!API_KEY) {
        setWeather(prev => ({ ...prev, temp: 18, city: 'Modo Demo', loading: false }));
        return;
    }

    try {
      const res = await fetch(`${API_URL}?lat=${lat}&lon=${lon}&units=metric&appid=${API_KEY}&lang=pt`);
      const data = await res.json();

      const code = data.weather[0].id;
      let condition = 'cloudy';
      let isRaining = false;

      if (code === 800) condition = 'sunny';
      else if (code >= 200 && code <= 531) {
        condition = 'rainy';
        isRaining = true;
      }

      setWeather({
        temp: Math.round(data.main.temp),
        humidity: data.main.humidity,
        condition,
        rain: isRaining,
        city: data.name,
        loading: false
      });

    } catch (error) {
      setWeather(prev => ({ ...prev, loading: false, city: 'Erro API' }));
    }
  };

  // 4. Lógica de Sugestão
  const getSuggestedOutfit = () => {
    const temp = weather.temp;
    const layer1Items = items.filter(item => item.layer === 1 && item.status === 'clean');
    const layer1 = layer1Items.find(item => item.tempMin <= temp && item.tempMax >= temp) || layer1Items[0];

    const layer2Items = items.filter(item => item.layer === 2 && item.status === 'clean');
    const layer2 = temp < 15 ? (layer2Items.find(item => item.tempMin <= temp) || layer2Items[0]) : null;

    const layer3Items = items.filter(item => item.layer === 3 && item.status === 'clean');
    const layer3 = weather.rain ? layer3Items.find(item => item.waterproof) : (temp < 10 ? layer3Items[0] : null);

    return { layer1, layer2, layer3 };
  };

  const outfit = getSuggestedOutfit();
  const cleanItems = items.filter(item => item.status === 'clean').length;
  const dirtyItems = items.filter(item => item.status === 'dirty').length;
  const missingLayers = [1, 2, 3].filter(layer => !items.some(item => item.layer === layer && item.status === 'clean'));

  const WeatherIcon = weather.condition === 'sunny' ? Sun : weather.rain ? CloudRain : Cloud;
  const todayDate = new Date().toLocaleDateString('pt-PT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* AVATAR DINÂMICO */}
            <div className="w-12 h-12 rounded-full bg-emerald-700 flex items-center justify-center text-white text-xl font-bold overflow-hidden border-2 border-emerald-100 shadow-sm">
              {userProfile.avatar_url ? (
                <img src={userProfile.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                userProfile.name.charAt(0).toUpperCase()
              )}
            </div>

            {/* NOME E LOCALIZAÇÃO */}
            <div>
              <h1 className="text-xl text-emerald-900 font-semibold">Bem-vindo de volta!</h1>
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
            <Button variant="outline" onClick={() => onNavigate('inventory')}>
              <Layers className="mr-2 h-4 w-4" /> Inventário
            </Button>
            <Button variant="outline" onClick={() => onNavigate('search')}>
              <Search className="mr-2 h-4 w-4" /> Pesquisar
            </Button>

            {/* BOTÃO VIAGEM */}
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
                    <span className="text-6xl font-bold tracking-tighter">{weather.temp}°C</span>
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
                <span className="font-medium">{weather.humidity}% Humidade</span>
              </div>
              {weather.rain && (
                <div className="flex items-center gap-2 justify-end bg-white/20 px-3 py-1.5 rounded-full backdrop-blur-sm">
                  <CloudRain className="h-4 w-4" />
                  <span className="text-sm font-medium">Chuva Prevista</span>
                </div>
              )}
              {weather.temp < 10 && (
                <div className="flex items-center gap-2 justify-end">
                  <Wind className="h-5 w-5" />
                  <span>Vento Frio</span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Sugestão do Dia */}
        <section>
          <h2 className="text-2xl font-semibold mb-4 text-emerald-900 flex items-center gap-2">
            <span className="bg-emerald-100 p-1.5 rounded-md"><TrendingUp className="h-5 w-5 text-emerald-700"/></span>
            Sugestão do Dia
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SuggestionCard layer={1} item={outfit.layer1} onViewItem={onViewItem} title="Base" color="emerald" />
            <SuggestionCard layer={2} item={outfit.layer2} onViewItem={onViewItem} title="Isolamento" color="amber" />
            <SuggestionCard layer={3} item={outfit.layer3} onViewItem={onViewItem} title="Proteção" color="sky" />
          </div>
        </section>

        {/* Resumo Inventário */}
        <section>
          <h2 className="text-xl font-semibold mb-4 text-stone-700">Resumo do Inventário</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Peças" value={items.length} icon={<TrendingUp className="h-4 w-4 text-emerald-600" />} />
            <StatCard label="Limpas" value={cleanItems} indicator="bg-emerald-500" />
            <StatCard label="Para Lavar" value={dirtyItems} indicator="bg-amber-500" />
            <StatCard label="Em Falta" value={missingLayers.length} indicator="bg-red-500" subtext={missingLayers.length > 0 ? `Camadas: ${missingLayers.join(', ')}` : undefined} />
          </div>
        </section>
      </main>

      {/* --- DIALOGS --- */}
      <EditProfileDialog
        open={isProfileOpen}
        onOpenChange={setIsProfileOpen}
        userData={userProfile}
        onUpdate={(newData: any) => setUserProfile({ ...userProfile, ...newData })}
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

function SuggestionCard({ layer, item, onViewItem, title, color }: any) {
  const bgColors: any = { emerald: 'bg-emerald-100', amber: 'bg-amber-100', sky: 'bg-sky-100' };

  return (
    <Card
      className={`p-4 h-full flex flex-col border-stone-100 transition-all hover:shadow-lg hover:-translate-y-1 duration-300 cursor-pointer ${item ? 'bg-white' : 'bg-stone-50 opacity-70'}`}
      onClick={() => item && onViewItem(item)}
    >
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-8 h-8 rounded-full ${bgColors[color]} flex items-center justify-center font-bold text-stone-700 shrink-0`}>
          {layer}
        </div>
        <h3 className="text-stone-600 font-medium">Camada {layer} - {title}</h3>
      </div>

      {item ? (
        <>
          <div className="h-48 w-full overflow-hidden rounded-lg mb-4 bg-stone-50 border border-stone-100 flex items-center justify-center">
            <img src={item.image} alt={item.name} className="w-full h-full object-contain p-2" />
          </div>
          <div>
            <p className="font-medium text-emerald-900 truncate">{item.name}</p>
            <p className="text-xs text-stone-500">{item.type}</p>
          </div>
        </>
      ) : (
        <div className="h-48 w-full rounded-lg mb-4 border-2 border-dashed border-stone-200 flex flex-col items-center justify-center text-stone-400 gap-2">
          <Search className="h-8 w-8 opacity-20" />
          <span className="text-sm">Sem sugestão</span>
        </div>
      )}
    </Card>
  );
}

function StatCard({ label, value, icon, indicator, subtext }: any) {
  return (
    <Card className="p-5 bg-white border-stone-100 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-stone-500 uppercase tracking-wider">{label}</span>
        {icon}
        {indicator && <div className={`w-2 h-2 rounded-full ${indicator}`} />}
      </div>
      <p className="text-3xl font-bold text-stone-800">{value}</p>
      {subtext && <p className="text-xs text-stone-400 mt-1">{subtext}</p>}
    </Card>
  );
}