import { useState, useEffect } from 'react';
import { ClothingItem, Screen } from '../App';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { 
  Cloud, 
  CloudRain, 
  Sun, 
  Droplets, 
  Wind,
  Layers,
  Search,
  LogOut,
  TrendingUp
} from 'lucide-react';

interface DashboardProps {
  items: ClothingItem[];
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onViewItem: (item: ClothingItem) => void;
}

export function Dashboard({ items, onNavigate, onLogout, onViewItem }: DashboardProps) {
  const [weather, setWeather] = useState({
    temp: 12,
    humidity: 65,
    condition: 'cloudy',
    rain: false
  });

  // Simular dados meteorológicos - em produção usaria uma API real
  useEffect(() => {
    // Mock weather data
    const conditions = ['sunny', 'cloudy', 'rainy'];
    const randomCondition = conditions[Math.floor(Math.random() * conditions.length)];
    setWeather({
      temp: Math.floor(Math.random() * 20) + 5,
      humidity: Math.floor(Math.random() * 40) + 40,
      condition: randomCondition,
      rain: randomCondition === 'rainy'
    });
  }, []);

  // Sugestão de outfit baseada na temperatura
  const getSuggestedOutfit = () => {
    const temp = weather.temp;
    
    // Camada 1 - Base
    const layer1Items = items.filter(item => item.layer === 1 && item.status === 'clean');
    const layer1 = layer1Items.find(item => 
      item.tempMin <= temp && item.tempMax >= temp
    ) || layer1Items[0];

    // Camada 2 - Isolamento
    const layer2Items = items.filter(item => item.layer === 2 && item.status === 'clean');
    const layer2 = temp < 15 
      ? layer2Items.find(item => item.tempMin <= temp && item.tempMax >= temp) || layer2Items[0]
      : null;

    // Camada 3 - Proteção
    const layer3Items = items.filter(item => item.layer === 3 && item.status === 'clean');
    const layer3 = weather.rain 
      ? layer3Items.find(item => item.waterproof)
      : temp < 10 
        ? layer3Items.find(item => item.windproof) || layer3Items[0]
        : null;

    return { layer1, layer2, layer3 };
  };

  const outfit = getSuggestedOutfit();
  const cleanItems = items.filter(item => item.status === 'clean').length;
  const dirtyItems = items.filter(item => item.status === 'dirty').length;
  const missingLayers = [1, 2, 3].filter(layer => 
    !items.some(item => item.layer === layer && item.status === 'clean')
  );

  const WeatherIcon = weather.condition === 'sunny' ? Sun : weather.rain ? CloudRain : Cloud;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-emerald-700 flex items-center justify-center text-white">
              JD
            </div>
            <div>
              <h1 className="text-xl text-emerald-900">Bem-vindo de volta!</h1>
              <p className="text-sm text-stone-600">João Dias</p>
            </div>
          </div>
          
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => onNavigate('inventory')}
            >
              <Layers className="mr-2 h-4 w-4" />
              Inventário
            </Button>
            <Button 
              variant="outline" 
              onClick={() => onNavigate('search')}
            >
              <Search className="mr-2 h-4 w-4" />
              Pesquisar
            </Button>
            <Button 
              variant="ghost" 
              onClick={onLogout}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Widget Meteorológico */}
        <Card className="bg-gradient-to-br from-sky-400 to-blue-500 text-white p-6 border-0">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <WeatherIcon className="h-8 w-8" />
                <span className="text-5xl">{weather.temp}°C</span>
              </div>
              <p className="text-xl mb-1">Lisboa, Portugal</p>
              <p className="text-sky-100">Segunda-feira, 17 de Novembro 2025</p>
            </div>
            
            <div className="text-right space-y-2">
              <div className="flex items-center gap-2 justify-end">
                <Droplets className="h-5 w-5" />
                <span>{weather.humidity}% Humidade</span>
              </div>
              {weather.rain && (
                <div className="flex items-center gap-2 justify-end">
                  <CloudRain className="h-5 w-5" />
                  <span>Chuva Prevista</span>
                </div>
              )}
              {weather.temp < 10 && (
                <div className="flex items-center gap-2 justify-end">
                  <Wind className="h-5 w-5" />
                  <span>Vento Forte</span>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Sugestão do Dia */}
        <section>
          <h2 className="text-2xl mb-4 text-emerald-900">Sugestão do Dia</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Camada 1 */}
            <Card 
              className={`p-4 cursor-pointer transition-all hover:shadow-lg ${outfit.layer1 ? '' : 'opacity-50'}`}
              onClick={() => outfit.layer1 && onViewItem(outfit.layer1)}
            >
              <div className="flex items-center gap-2 mb-3 text-emerald-900">
                <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                  <span>1</span>
                </div>
                <h3>Camada 1 - Base</h3>
              </div>
              {outfit.layer1 ? (
                <>
                  <img 
                    src={outfit.layer1.image} 
                    alt={outfit.layer1.name}
                    className="w-full h-48 object-cover rounded-lg mb-3"
                  />
                  <p className="mb-1 text-emerald-900">{outfit.layer1.name}</p>
                  <p className="text-sm text-stone-600">{outfit.layer1.type}</p>
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {outfit.layer1.materials.map(material => (
                      <span key={material} className="text-xs bg-stone-100 px-2 py-1 rounded">
                        {material}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="h-48 bg-stone-100 rounded-lg flex items-center justify-center">
                  <p className="text-stone-400">Sem peça disponível</p>
                </div>
              )}
            </Card>

            {/* Camada 2 */}
            <Card 
              className={`p-4 cursor-pointer transition-all hover:shadow-lg ${outfit.layer2 ? '' : 'opacity-50'}`}
              onClick={() => outfit.layer2 && onViewItem(outfit.layer2)}
            >
              <div className="flex items-center gap-2 mb-3 text-emerald-900">
                <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
                  <span>2</span>
                </div>
                <h3>Camada 2 - Isolamento</h3>
              </div>
              {outfit.layer2 ? (
                <>
                  <img 
                    src={outfit.layer2.image} 
                    alt={outfit.layer2.name}
                    className="w-full h-48 object-cover rounded-lg mb-3"
                  />
                  <p className="mb-1 text-emerald-900">{outfit.layer2.name}</p>
                  <p className="text-sm text-stone-600">{outfit.layer2.type}</p>
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {outfit.layer2.materials.map(material => (
                      <span key={material} className="text-xs bg-stone-100 px-2 py-1 rounded">
                        {material}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="h-48 bg-stone-100 rounded-lg flex items-center justify-center">
                  <p className="text-stone-400">Não necessário</p>
                </div>
              )}
            </Card>

            {/* Camada 3 */}
            <Card 
              className={`p-4 cursor-pointer transition-all hover:shadow-lg ${outfit.layer3 ? '' : 'opacity-50'}`}
              onClick={() => outfit.layer3 && onViewItem(outfit.layer3)}
            >
              <div className="flex items-center gap-2 mb-3 text-emerald-900">
                <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center">
                  <span>3</span>
                </div>
                <h3>Camada 3 - Proteção</h3>
              </div>
              {outfit.layer3 ? (
                <>
                  <img 
                    src={outfit.layer3.image} 
                    alt={outfit.layer3.name}
                    className="w-full h-48 object-cover rounded-lg mb-3"
                  />
                  <p className="mb-1 text-emerald-900">{outfit.layer3.name}</p>
                  <p className="text-sm text-stone-600">{outfit.layer3.type}</p>
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {outfit.layer3.materials.map(material => (
                      <span key={material} className="text-xs bg-stone-100 px-2 py-1 rounded">
                        {material}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="h-48 bg-stone-100 rounded-lg flex items-center justify-center">
                  <p className="text-stone-400">Não necessário</p>
                </div>
              )}
            </Card>
          </div>
        </section>

        {/* Resumo do Inventário */}
        <section>
          <h2 className="text-2xl mb-4 text-emerald-900">Resumo do Inventário</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="p-6 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-stone-600">Total de Peças</span>
                <TrendingUp className="h-5 w-5 text-emerald-600" />
              </div>
              <p className="text-4xl text-emerald-900">{items.length}</p>
            </Card>

            <Card className="p-6 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-stone-600">Peças Limpas</span>
                <div className="w-3 h-3 rounded-full bg-emerald-500" />
              </div>
              <p className="text-4xl text-emerald-900">{cleanItems}</p>
            </Card>

            <Card className="p-6 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-stone-600">Para Lavar</span>
                <div className="w-3 h-3 rounded-full bg-amber-500" />
              </div>
              <p className="text-4xl text-emerald-900">{dirtyItems}</p>
            </Card>

            <Card className="p-6 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-stone-600">Camadas em Falta</span>
                <div className="w-3 h-3 rounded-full bg-red-500" />
              </div>
              <p className="text-4xl text-emerald-900">
                {missingLayers.length}
              </p>
              {missingLayers.length > 0 && (
                <p className="text-xs text-stone-500 mt-1">
                  Camadas: {missingLayers.join(', ')}
                </p>
              )}
            </Card>
          </div>
        </section>
      </main>
    </div>
  );
}
