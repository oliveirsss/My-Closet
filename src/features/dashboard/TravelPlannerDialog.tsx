import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { ClothingItem } from '../../types';
import { Plane, Luggage, CloudRain, Sun, Wind } from 'lucide-react';
import * as api from '../../services/api';
import { Sparkles, RefreshCw } from 'lucide-react';

const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || '';

interface TravelPlannerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: ClothingItem[];
}

const sectionLabels: Record<string, string> = {
  base_layer: "Base",
  insulation_layer: "Isolamento",
  pants: "Calças",
  outer_layer: "Casaco",
  shoes: "Calçado",
  accessories: "Acessórios",
};

const sectionOrder = ["base_layer", "insulation_layer", "pants", "outer_layer", "shoes", "accessories"];

function groupItemsBySection(items: any[]) {
  return items.reduce((groups: Record<string, any[]>, item: any) => {
    const section = item.section || "base_layer";
    groups[section] = groups[section] || [];
    groups[section].push(item);
    return groups;
  }, {});
}

export function TravelPlannerDialog({ open, onOpenChange, items: _items }: TravelPlannerDialogProps) {
  const [city, setCity] = useState('');
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
    const numDays = parseInt(duration) || 3;
    if (numDays < 1 || numDays > 5) {
      setError('A duração deve estar entre 1 e 5 dias.');
      return;
    }
    setLoading(true);
    setError('');
    setShowSuggestions(false);
    setTripPlan(null);

    try {
      const response = await api.getAITravelOutfits({
        destination: city,
        days: numDays,
        preferences: { style: "casual" },
        luggage_limit: 15,
      });

      if (response.success && response.daily_outfits) {
        const dailyOutfits = response.daily_outfits.map((dayPlan: any) => {
          const items = dayPlan.outfit?.items || [];
          return {
            day: dayPlan.day,
            weather: dayPlan.weather || { temp: 18, condition: "cloudy" },
            items,
            groupedItems: groupItemsBySection(items),
            reasoning: dayPlan.outfit?.reasoning || "",
          };
        });

        const packingList = (response.packing_items || response.packing_list || []).map((item: any) => ({
          item: item, count: 1
        }));

        setTripPlan({
          city: city,
          country: "",
          dailyOutfits,
          packingList,
          warnings: response.warnings || [],
          isAI: true
        });
      } else {
        setError(response.error || "Ocorreu um erro com o LLaVA. Usa a opção standard.");
      }
    } catch (error: any) {
      console.error(error);
      setError(error.message || "Erro no serviço AI. Usa a opção de geração local.");
    } finally {
      setLoading(false);
    }
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
          <div className="flex flex-col mt-4">
             <Button onClick={handleSearch} disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm font-medium py-6 text-md">
               {loading ? <RefreshCw className="mr-2 h-5 w-5 animate-spin"/> : <span className="flex items-center gap-2"><Sparkles className="h-5 w-5"/> Gerar Mala de Viagem (AI)</span>}
             </Button>
          </div>
        </div>

        {tripPlan && (
          <div className="space-y-6 animate-in fade-in slide-in-from-top-2">

            {/* Resumo da Mala */}
            <div className="bg-stone-50/50 p-6 rounded-xl border border-stone-100">
              <h3 className="font-medium text-stone-800 mb-4 flex items-center gap-2">
                <Luggage className="h-5 w-5 text-emerald-600" />
                <span className="tracking-tight">A tua Mala de Viagem</span>
              </h3>
              {tripPlan.warnings?.length > 0 && (
                <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {tripPlan.warnings.join(' ')}
                </div>
              )}
              <div className="grid grid-cols-5 gap-3 w-full">
                {tripPlan.packingList.map((entry: any) => (
                  <div key={entry.item.id} className="group relative flex flex-col items-center">
                    <div className="w-full aspect-[4/5] bg-white rounded-2xl border border-stone-100 shadow-sm group-hover:shadow-md transition-all duration-300 overflow-hidden mb-2 p-3 flex items-center justify-center relative">
                      <img src={api.getAssetUrl(entry.item.image)} className="w-full h-full object-contain transform group-hover:scale-105 transition-transform" alt="" />
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
                        {String(dayPlan.weather.condition || '').includes('rain') ? <CloudRain className="h-4 w-4 text-blue-400" /> : <Sun className="h-4 w-4 text-amber-400" />}
                        <span>{Math.round(dayPlan.weather.temp ?? dayPlan.weather.temperature ?? 18)}°C</span>
                        {Number(dayPlan.weather.wind_speed || dayPlan.weather.windSpeed || 0) > 10 && <Wind className="h-4 w-4 text-stone-400" />}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {sectionOrder.flatMap((section) =>
                        (dayPlan.groupedItems[section] || []).map((item: any) => (
                          <div key={`${dayPlan.day}-${item.id}`} className="flex items-center gap-2 rounded-md border border-stone-100 bg-stone-50 p-2">
                            <div className="h-12 w-12 shrink-0 rounded bg-white border border-stone-100 overflow-hidden flex items-center justify-center">
                              <img src={api.getAssetUrl(item.image)} alt="" className="h-full w-full object-contain p-1" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-[10px] uppercase tracking-wide text-stone-400">{sectionLabels[section]}</p>
                              <p className="truncate text-xs font-medium text-stone-700">{item.name}</p>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    {dayPlan.reasoning && (
                      <p className="mt-3 text-xs leading-relaxed text-stone-500">{dayPlan.reasoning}</p>
                    )}
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
