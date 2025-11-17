import { useState } from 'react';
import { ClothingItem, Screen, UserType } from '../App';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { 
  Plus, 
  Search, 
  Filter,
  Heart,
  Droplet,
  Wind,
  LogOut,
  Home,
  Camera
} from 'lucide-react';
import { AddItemDialog } from './AddItemDialog';
import Masonry from 'react-responsive-masonry';

interface InventoryProps {
  items: ClothingItem[];
  userType: UserType;
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onAddItem: (item: ClothingItem) => void;
  onViewItem: (item: ClothingItem) => void;
}

export function Inventory({ 
  items, 
  userType,
  onNavigate, 
  onLogout, 
  onAddItem, 
  onViewItem 
}: InventoryProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterLayer, setFilterLayer] = useState<number | null>(null);
  const [filterSeason, setFilterSeason] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  const filteredItems = items.filter(item => {
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (filterType && item.type !== filterType) {
      return false;
    }
    if (filterLayer && item.layer !== filterLayer) {
      return false;
    }
    if (filterSeason && !item.seasons.includes(filterSeason)) {
      return false;
    }
    if (filterStatus && item.status !== filterStatus) {
      return false;
    }
    return true;
  });

  const types = [...new Set(items.map(item => item.type))];
  const seasons = ['Inverno', 'Outono', 'Primavera', 'Verão'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl text-emerald-900">
            {userType === 'client' ? 'O Meu Inventário' : 'Base de Dados Pública'}
          </h1>
          
          <div className="flex gap-2">
            {userType === 'client' && (
              <>
                <Button 
                  variant="outline" 
                  onClick={() => onNavigate('dashboard')}
                >
                  <Home className="mr-2 h-4 w-4" />
                  Dashboard
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => onNavigate('search')}
                >
                  <Camera className="mr-2 h-4 w-4" />
                  Pesquisa por Imagem
                </Button>
              </>
            )}
            <Button 
              variant="ghost" 
              onClick={onLogout}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {/* Search and Filters */}
        <div className="mb-6 space-y-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-stone-400" />
              <Input
                placeholder="Pesquisar peças..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Filter Chips */}
          <div className="flex flex-wrap gap-2 items-center">
            <div className="flex items-center gap-2 text-stone-600">
              <Filter className="h-4 w-4" />
              <span className="text-sm">Filtros:</span>
            </div>

            {/* Type Filters */}
            <div className="flex gap-2 flex-wrap">
              {types.map(type => (
                <Badge
                  key={type}
                  variant={filterType === type ? 'default' : 'outline'}
                  className={`cursor-pointer ${filterType === type ? 'bg-emerald-700' : ''}`}
                  onClick={() => setFilterType(filterType === type ? null : type)}
                >
                  {type}
                </Badge>
              ))}
            </div>

            <div className="w-px h-6 bg-stone-300" />

            {/* Layer Filters */}
            <div className="flex gap-2">
              {[1, 2, 3].map(layer => (
                <Badge
                  key={layer}
                  variant={filterLayer === layer ? 'default' : 'outline'}
                  className={`cursor-pointer ${filterLayer === layer ? 'bg-emerald-700' : ''}`}
                  onClick={() => setFilterLayer(filterLayer === layer ? null : layer)}
                >
                  Camada {layer}
                </Badge>
              ))}
            </div>

            <div className="w-px h-6 bg-stone-300" />

            {/* Season Filters */}
            <div className="flex gap-2 flex-wrap">
              {seasons.map(season => (
                <Badge
                  key={season}
                  variant={filterSeason === season ? 'default' : 'outline'}
                  className={`cursor-pointer ${filterSeason === season ? 'bg-emerald-700' : ''}`}
                  onClick={() => setFilterSeason(filterSeason === season ? null : season)}
                >
                  {season}
                </Badge>
              ))}
            </div>

            <div className="w-px h-6 bg-stone-300" />

            {/* Status Filters */}
            <div className="flex gap-2">
              <Badge
                variant={filterStatus === 'clean' ? 'default' : 'outline'}
                className={`cursor-pointer ${filterStatus === 'clean' ? 'bg-emerald-700' : ''}`}
                onClick={() => setFilterStatus(filterStatus === 'clean' ? null : 'clean')}
              >
                Limpo
              </Badge>
              <Badge
                variant={filterStatus === 'dirty' ? 'default' : 'outline'}
                className={`cursor-pointer ${filterStatus === 'dirty' ? 'bg-emerald-700' : ''}`}
                onClick={() => setFilterStatus(filterStatus === 'dirty' ? null : 'dirty')}
              >
                Sujo
              </Badge>
            </div>

            {/* Clear Filters */}
            {(filterType || filterLayer || filterSeason || filterStatus) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFilterType(null);
                  setFilterLayer(null);
                  setFilterSeason(null);
                  setFilterStatus(null);
                }}
              >
                Limpar Filtros
              </Button>
            )}
          </div>
        </div>

        {/* Results Count */}
        <p className="text-stone-600 mb-4">
          {filteredItems.length} {filteredItems.length === 1 ? 'peça encontrada' : 'peças encontradas'}
        </p>

        {/* Masonry Grid */}
        <Masonry columnsCount={4} gutter="1rem">
          {filteredItems.map(item => (
            <div
              key={item.id}
              className="bg-white rounded-lg overflow-hidden shadow-md hover:shadow-xl transition-all cursor-pointer group"
              onClick={() => onViewItem(item)}
            >
              <div className="relative">
                <img
                  src={item.image}
                  alt={item.name}
                  className="w-full h-64 object-cover group-hover:scale-105 transition-transform"
                />
                {item.favorite && (
                  <div className="absolute top-2 right-2 bg-white/90 rounded-full p-2">
                    <Heart className="h-5 w-5 fill-red-500 text-red-500" />
                  </div>
                )}
                <div className="absolute top-2 left-2">
                  <Badge className="bg-emerald-700">
                    Camada {item.layer}
                  </Badge>
                </div>
              </div>
              
              <div className="p-4">
                <p className="mb-1 text-emerald-900">{item.name}</p>
                <p className="text-sm text-stone-600 mb-3">{item.type}</p>
                
                <div className="flex gap-1 flex-wrap mb-3">
                  {item.waterproof && (
                    <Badge variant="outline" className="text-xs">
                      <Droplet className="h-3 w-3 mr-1" />
                      Impermeável
                    </Badge>
                  )}
                  {item.windproof && (
                    <Badge variant="outline" className="text-xs">
                      <Wind className="h-3 w-3 mr-1" />
                      Corta-vento
                    </Badge>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-stone-500">
                  <span>{item.tempMin}°C - {item.tempMax}°C</span>
                  <div className={`w-2 h-2 rounded-full ${item.status === 'clean' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                </div>
              </div>
            </div>
          ))}
        </Masonry>

        {filteredItems.length === 0 && (
          <div className="text-center py-12">
            <p className="text-stone-400 mb-4">Nenhuma peça encontrada</p>
            {userType === 'client' && (
              <Button onClick={() => setShowAddDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Adicionar Primeira Peça
              </Button>
            )}
          </div>
        )}
      </main>

      {/* FAB - Floating Action Button */}
      {userType === 'client' && (
        <button
          onClick={() => setShowAddDialog(true)}
          className="fixed bottom-6 right-6 w-16 h-16 rounded-full bg-emerald-700 hover:bg-emerald-800 text-white shadow-xl hover:shadow-2xl transition-all flex items-center justify-center"
        >
          <Plus className="h-8 w-8" />
        </button>
      )}

      {/* Add Item Dialog */}
      <AddItemDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onAdd={onAddItem}
      />
    </div>
  );
}
