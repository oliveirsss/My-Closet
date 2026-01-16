import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card } from '../../components/ui/card';
import { ClothingItem } from '../../types';
import { Plane, MapPin, Luggage, Calendar as CalendarIcon, CloudRain, Sun, Wind } from 'lucide-react';
import { Badge } from '../../components/ui/badge';
import { recommendOutfit, WeatherData } from '../../services/outfitRecommendation';

const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || '';

interface TravelPlannerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: ClothingItem[];
}

// Helper para agrupar array em chunks (dias)
const chunk = (arr: any[], size: number) =>
  Array.from({ length: Math.ceil(arr.length / size) }, (_, i) =>
    arr.slice(i * size, i * size + size)
  );

export function TravelPlannerDialog({ open, onOpenChange, items }: TravelPlannerDialogProps) {
  const [city, setCity] = useState('');
  const [startDate, setStartDate] = useState('');
  const [duration, setDuration] = useState('3'); // Dias
  const [loading, setLoading] = useState(false);
  const [tripPlan, setTripPlan] = useState<any>(null);

  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState('');

  // Debounce para pesquisa de cidades
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (city.length >= 3) {
        try {
          // Usar Geocoding API para sujestões
          const res = await fetch(
            `https://api.openweathermap.org/geo/1.0/direct?q=${encodeURIComponent(city)}&limit=15&appid=${API_KEY}`
          );
          const data = await res.json();
          if (Array.isArray(data)) {
            // Filtrar duplicados (mesmo nome e país)
            const unique = data.filter((v, i, a) =>
              a.findIndex(v2 => (v2.name === v.name && v2.country === v.country)) === i
            );
            setSuggestions(unique);
            setShowSuggestions(true);
          }
        } catch (err) {
          console.error("Erro ao buscar sugestões", err);
        }
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [city]);

  const handleSelectCity = (suggestion: any) => {
    setCity(suggestion.name);
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const handleSearch = async () => {
    if (!city) {
      setError('Por favor, insira o nome de uma cidade.');
      return;
    }
    if (!API_KEY) {
      setError('Erro de configuração: Chave API em falta.');
      return;
    }

    setLoading(true);
    setError('');
    // Fechar sugestões ao pesquisar
    setShowSuggestions(false);
    setTripPlan(null);

    try {
      // 1. Buscar Previsão 5 dias / 3 horas
      const res = await fetch(`https://api.openweathermap.org/data/2.5/forecast?q=${city}&units=metric&appid=${API_KEY}&lang=pt`);
      const data = await res.json();

      if (data.cod === "404") {
        throw new Error("Cidade não encontrada. Verifique o nome e tente novamente.");
      }
      if (data.cod !== "200") {
        throw new Error(data.message || "Erro desconhecido ao buscar dados.");
      }

      // 2. Processar dias da viagem (max 5 dias devido à API gratuita)
      const numDays = Math.min(parseInt(duration) || 3, 5);
      const dailyForecasts = processForecast(data.list, numDays);

      // 3. Gerar Outfits para cada dia
      const dailyOutfits = dailyForecasts.map((weather, index) => {
        return {
          day: index + 1,
          weather,
          outfit: recommendOutfit(items, weather)
        };
      });

      // 4. Gerar Lista de Mala Agregada
      const packingList = generatePackingList(dailyOutfits);

      setTripPlan({
        city: data.city.name,
        country: data.city.country,
        dailyOutfits,
        packingList
      });

    } catch (error: any) {
      console.error(error);
      setError(error.message || "Erro ao planear viagem. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const processForecast = (list: any[], days: number): WeatherData[] => {
    // A API retorna dados a cada 3 horas (8 registos por dia)
    // Vamos pegar no ponto do meio-dia (aprox) para simplificar a "temperatura do dia"
    // Ou calcular média/max/min. Para simplificar: pegar o max do dia.

    // Agrupar por dia (aproximado, pegando chunks de 8)
    const dayChunks = chunk(list, 8).slice(0, days);

    return dayChunks.map(chunk => {
      // Calcular temp max e min do bloco
      const maxTemp = Math.max(...chunk.map((i: any) => i.main.temp));
      const hasRain = chunk.some((i: any) => i.weather[0].main.toLowerCase().includes('rain'));
      const maxWind = Math.max(...chunk.map((i: any) => i.wind.speed));

      // Usar a descrição do meio do dia
      const midDay = chunk[Math.floor(chunk.length / 2)];

      return {
        temperature: maxTemp,
        rain: hasRain,
        windSpeed: maxWind,
        season: calculateSeason(maxTemp), // Helper simples
        humidity: midDay.main.humidity
      };
    });
  };

  const calculateSeason = (temp: number) => {
    if (temp >= 20) return 'Summer';
    if (temp <= 10) return 'Winter';
    return 'Spring/Fall';
  };

  const generatePackingList = (dailyOutfits: any[]) => {
    // Lógica para otimizar mala
    // 1. Base Layers: 1 por dia (são sujos rápido)
    // 2. Mid/Outer/Pants: Tentar reutilizar

    const uniqueItems = new Set<string>();
    const list: Record<string, { item: ClothingItem, count: number }> = {};

    dailyOutfits.forEach(day => {
      const parts = [
        day.outfit.baseLayer.items[0]?.item,
        day.outfit.insulationLayer.items[0]?.item,
        day.outfit.outerLayer.items[0]?.item,
        // Adicionar calças (assumindo que insulationLayer items[1] é calça se for layer 2 strategy antiga, 
        // mas agora temos items array. Vamos simplificar e pegar tudo o que foi recomendado)
      ].filter(Boolean);

      // A `recommendOutfit` nova estrutura retorna items[] para cada layer.
      // Vamos varrer todos.
      [
        ...day.outfit.baseLayer.items,
        ...day.outfit.insulationLayer.items,
        ...day.outfit.outerLayer.items
      ].forEach(rec => {
        const item = rec.item;
        if (item) {
          if (!list[item.id]) {
            list[item.id] = { item, count: 0 };
          }
          // Lógica simples: Se for Base layer -> +1 por uso. 
          // Se for Outer/Bottom -> Só conta 1 vez (leva o mesmo)
          // Para simplificar nesta versão: Adiciona à lista se não existir ("Leva este casaco").
          // Se for base layer (layer 1), incrementa contador idealmente.

          if (item.layer === 1) {
            list[item.id].count += 1;
          } else {
            list[item.id].count = 1; // Leva 1 deste, reutiliza
          }
        }
      });
    });

    return Object.values(list);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl text-emerald-900">
            <Plane className="h-6 w-6" /> Planeador de Viagem
          </DialogTitle>
          <DialogDescription>
            Planeie a sua mala para os próximos 5 dias.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 my-4 bg-white p-4 rounded-lg shadow-sm border border-stone-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative">
              <label className="text-xs text-stone-500 mb-1 block">Destino</label>
              <div className="relative">
                <Input
                  placeholder="Ex: Londres..."
                  value={city}
                  onChange={(e) => {
                    setCity(e.target.value);
                    if (error) setError('');
                  }}
                  onBlur={() => {
                    // Pequeno delay para permitir o clique na sugestão
                    setTimeout(() => setShowSuggestions(false), 200);
                  }}
                  className={error ? "border-red-300 focus-visible:ring-red-200" : ""}
                />

                {/* SUGESTÕES DROPDOWN */}
                {showSuggestions && suggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white rounded-md shadow-lg border border-stone-100 max-h-60 overflow-y-auto">
                    {suggestions.map((option, index) => (
                      <button
                        key={`${option.name}-${index}`}
                        className="w-full text-left px-4 py-2 text-sm hover:bg-emerald-50 text-stone-700 transition-colors flex items-center justify-between"
                        onClick={() => handleSelectCity(option)}
                      >
                        <span>{option.name}</span>
                        <span className="text-xs text-stone-400">{option.country}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {error && (
                <span className="text-xs text-red-500 mt-1 block">{error}</span>
              )}
            </div>
            <div className="relative">
              <label className="text-xs text-stone-500 mb-1 block">Duração (Dias)</label>
              <Input
                type="number"
                min="1"
                max="5"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
              />
            </div>
          </div>
          <Button onClick={handleSearch} disabled={loading} className="w-full bg-emerald-700 hover:bg-emerald-800 text-white mt-2">
            {loading ? 'A Planear Viagem...' : 'Gerar Mala de Viagem'}
          </Button>
        </div>

        {tripPlan && (
          <div className="space-y-6 animate-in fade-in slide-in-from-top-2">

            {/* Resumo da Mala */}
            <div className="bg-stone-50/50 p-6 rounded-xl border border-stone-100">
              <h3 className="font-medium text-stone-800 mb-4 flex items-center gap-2">
                <Luggage className="h-5 w-5 text-emerald-600" />
                <span className="tracking-tight">A tua Mala de Viagem</span>
              </h3>
              <div className="grid grid-cols-5 gap-3 w-full">
                {tripPlan.packingList.map((entry: any) => (
                  <div key={entry.item.id} className="group relative flex flex-col items-center">
                    <div className="w-full aspect-[4/5] bg-white rounded-2xl border border-stone-100 shadow-sm group-hover:shadow-md transition-all duration-300 overflow-hidden mb-2 p-3 flex items-center justify-center relative">
                      <img src={entry.item.image} className="w-full h-full object-contain transform group-hover:scale-105 transition-transform" alt="" />
                      {entry.count > 1 && (
                        <span className="absolute top-2 right-2 bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">
                          {entry.count}x
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-stone-600 font-medium text-center leading-tight line-clamp-2 px-1">
                      {entry.item.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Detalhe Dia a Dia */}
            <div>
              <h3 className="font-semibold text-stone-700 mb-3">Trajes por Dia</h3>
              <div className="space-y-4">
                {tripPlan.dailyOutfits.map((dayPlan: any) => (
                  <div key={dayPlan.day} className="border border-stone-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-emerald-800">Dia {dayPlan.day}</span>
                      <div className="flex items-center gap-2 text-sm text-stone-600">
                        {dayPlan.weather.rain ? <CloudRain className="h-4 w-4 text-blue-400" /> : <Sun className="h-4 w-4 text-amber-400" />}
                        <span>{Math.round(dayPlan.weather.temperature)}°C</span>
                        {dayPlan.weather.windSpeed > 10 && <Wind className="h-4 w-4 text-stone-400" />}
                      </div>
                    </div>
                    <div className="flex gap-2 text-sm text-stone-500">
                      <span className={dayPlan.outfit.baseLayer.isMissing ? "text-red-400" : ""}>
                        {dayPlan.outfit.baseLayer.items[0]?.item.name || "Sem Base"}
                      </span>
                      <span>+</span>
                      <span>{dayPlan.outfit.insulationLayer.items[0]?.item.name || "Sem Isolamento"}</span>
                      {dayPlan.outfit.outerLayer.items.length > 0 && (
                        <>
                          <span>+</span>
                          <span>{dayPlan.outfit.outerLayer.items[0]?.item.name}</span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function PackItem({ item, label }: any) {
  if (!item) return null;
  return (
    <Card className="p-2 flex flex-col items-center text-center border-stone-200 shadow-sm">
      <div className="w-full aspect-square bg-stone-50 rounded mb-2 overflow-hidden flex items-center justify-center">
        <img src={item.image} alt={item.name} className="w-full h-full object-contain p-1" />
      </div>
      <Badge variant="outline" className="mb-1 text-[10px]">{label}</Badge>
      <p className="text-xs font-medium text-stone-700 truncate w-full">{item.name}</p>
    </Card>
  );
}