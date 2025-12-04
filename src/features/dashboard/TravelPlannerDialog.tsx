import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card } from '../../components/ui/card';
import { ClothingItem } from '../../types';
import { Plane, Search, CloudRain, Sun, Wind, MapPin, Luggage } from 'lucide-react';
import { Badge } from '../../components/ui/badge';

const API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY || '';

interface TravelPlannerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: ClothingItem[]; // Recebe o inventário para sugerir peças
}

export function TravelPlannerDialog({ open, onOpenChange, items }: TravelPlannerDialogProps) {
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);
  const [forecast, setForecast] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any>(null);

  const handleSearch = async () => {
    if (!city || !API_KEY) return;
    setLoading(true);
    setForecast(null);
    setSuggestions(null);

    try {
      // 1. Buscar tempo para a cidade destino
      const res = await fetch(`https://api.openweathermap.org/data/2.5/weather?q=${city}&units=metric&appid=${API_KEY}&lang=pt`);
      const data = await res.json();

      if (data.cod !== 200) throw new Error(data.message);

      const temp = Math.round(data.main.temp);
      const isRaining = data.weather[0].main.toLowerCase().includes('rain');

      setForecast({
        temp,
        desc: data.weather[0].description,
        rain: isRaining,
        city: data.name,
        country: data.sys.country
      });

      // 2. Gerar Sugestões da Mala de Viagem
      generatePackingList(temp, isRaining);

    } catch (error) {
      console.error(error);
      alert("Cidade não encontrada ou erro na API.");
    } finally {
      setLoading(false);
    }
  };

  const generatePackingList = (temp: number, isRain: boolean) => {
    // Filtra peças adequadas à temperatura e condições
    const suitableItems = items.filter(item =>
      item.tempMin <= temp && item.tempMax >= temp
    );

    // Seleciona 1 de cada tipo essencial
    const pack = {
      base: suitableItems.find(i => i.layer === 1) || items.find(i => i.layer === 1),
      mid: temp < 20 ? (suitableItems.find(i => i.layer === 2) || items.find(i => i.layer === 2)) : null,
      outer: (isRain || temp < 15) ? (suitableItems.find(i => i.layer === 3) || items.find(i => i.layer === 3)) : null,
      extra: suitableItems.filter(i => i.id !== 'used').slice(0, 2) // Peças extra
    };

    setSuggestions(pack);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl text-emerald-900">
            <Plane className="h-6 w-6" /> Planeador de Viagem
          </DialogTitle>
          <DialogDescription>
            Para onde vais viajar? Vamos ver o tempo e sugerir a mala ideal.
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2 my-4">
          <div className="relative flex-1">
            <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
            <Input
              placeholder="Ex: Londres, Paris, Nova Iorque..."
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="pl-9"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <Button onClick={handleSearch} disabled={loading} className="bg-emerald-700 hover:bg-emerald-800">
            {loading ? 'A ver...' : 'Planear'}
          </Button>
        </div>

        {forecast && (
          <div className="space-y-6 animate-in fade-in slide-in-from-top-2">

            {/* Previsão do Tempo */}
            <div className="bg-sky-50 p-4 rounded-lg border border-sky-100 flex items-center justify-between">
              <div>
                <p className="text-sm text-sky-600 font-medium uppercase tracking-wide">Tempo em {forecast.city}, {forecast.country}</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-4xl font-bold text-sky-900">{forecast.temp}°C</span>
                  <span className="text-sky-700 capitalize">{forecast.desc}</span>
                </div>
              </div>
              {forecast.rain ? <CloudRain className="h-10 w-10 text-sky-400" /> : <Sun className="h-10 w-10 text-amber-400" />}
            </div>

            {/* Sugestão de Mala */}
            {suggestions && (
              <div>
                <h3 className="font-semibold text-stone-700 mb-3 flex items-center gap-2">
                  <Luggage className="h-4 w-4" /> Sugestão de Mala
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  {suggestions.base && <PackItem item={suggestions.base} label="Base" />}
                  {suggestions.mid && <PackItem item={suggestions.mid} label="Isolamento" />}
                  {suggestions.outer && <PackItem item={suggestions.outer} label="Proteção" />}
                </div>

                {/* Aviso se faltar algo */}
                {(!suggestions.base || (forecast.rain && !suggestions.outer?.waterproof)) && (
                   <div className="mt-3 p-3 bg-amber-50 text-amber-800 text-sm rounded border border-amber-100">
                      ⚠️ Atenção: O teu armário pode não ter proteção suficiente para esta viagem.
                   </div>
                )}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function PackItem({ item, label }: any) {
  return (
    <Card className="p-2 flex flex-col items-center text-center border-stone-200 shadow-sm hover:border-emerald-300 transition-colors">
      <div className="w-full aspect-square bg-stone-50 rounded mb-2 overflow-hidden flex items-center justify-center">
         <img src={item.image} alt={item.name} className="w-full h-full object-contain p-1" />
      </div>
      <Badge variant="outline" className="mb-1 text-[10px]">{label}</Badge>
      <p className="text-xs font-medium text-stone-700 truncate w-full">{item.name}</p>
    </Card>
  );
}