import { useState, useEffect } from 'react';
import { ClothingItem, Screen, UserType } from '../../types';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Card } from '../../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import {
  Search, Droplet, LogOut, Home, Camera,
  TrendingUp, Zap, User, X, ChevronDown, BarChart3, Shirt, Thermometer, Plus
} from 'lucide-react';
import { AddItemDialog } from './AddItemDialog';
import {
  PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

interface InventoryProps {
  items: ClothingItem[];
  userType: UserType;
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onAddItem: (item: ClothingItem) => void;
  onViewItem: (item: ClothingItem) => void;
  ownerFilter?: { id: string, name: string } | null;
  onClearOwnerFilter?: () => void;
}

export function Inventory({
  items, userType, onNavigate, onLogout, onAddItem, onViewItem, ownerFilter, onClearOwnerFilter
}: InventoryProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showStatsDialog, setShowStatsDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(8);

  // Resetar a paginação ao mudar filtros
  useEffect(() => {
    setVisibleCount(8);
  }, [searchQuery, filterType, ownerFilter]);

  // --- Lógica de Filtragem ---
  const filteredItems = items.filter(item => {
    if (ownerFilter && item.ownerId !== ownerFilter.id) return false;
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (filterType && item.type !== filterType) return false;
    return true;
  });

  // Itens visíveis (Paginação)
  const visibleItems = filteredItems.slice(0, visibleCount);

  // --- Dados para as Estatísticas ---
  const materialData = getMaterialData(items);
  const seasonData = getSeasonData(items);
  const topCategories = getTopCategories(items);
  const totalItems = items.length;
  const dominantSeason = seasonData.length > 0 ? seasonData[0].name : '-';
  const topMaterial = materialData.length > 0 ? materialData[0].name : '-';
  const topCategory = topCategories.length > 0 ? topCategories[0][0] : '-';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">

      {/* --- HEADER --- */}
      <header className="bg-white border-b border-stone-200 px-6 py-4 sticky top-0 z-30 shadow-sm">
         <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl text-emerald-900 font-semibold flex items-center gap-2">
            {userType === 'client' ? 'My Closet' : (
              <><span>Our Closet</span><span className="text-sm font-normal text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full border border-stone-200">Comunidade</span></>
            )}
          </h1>
          <div className="flex gap-2">
             {userType === 'client' ? (
                <>
                  <Button variant="outline" onClick={() => onNavigate('dashboard')}><Home className="mr-2 h-4 w-4"/>Dashboard</Button>
                  <Button variant="outline" onClick={() => onNavigate('search')}><Camera className="mr-2 h-4 w-4"/>Pesquisa</Button>
                </>
             ) : null}

             {/* BOTÃO INSIGHTS */}
             <Button variant="outline" onClick={() => setShowStatsDialog(true)} className="text-emerald-700 border-emerald-200 hover:bg-emerald-50">
                <BarChart3 className="h-4 w-4 mr-2"/>
                Insights
             </Button>

             <Button variant="ghost" onClick={onLogout}><LogOut className="h-4 w-4"/></Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">

        {/* --- HEADER DE PERFIL --- */}
        {ownerFilter && (
          <div className="mb-8 p-6 bg-white rounded-xl shadow-sm border border-stone-200 flex items-center justify-between animate-in fade-in slide-in-from-top-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
                <User className="h-8 w-8" />
              </div>
              <div>
                <p className="text-sm text-stone-500 uppercase tracking-wide font-bold">Perfil de Visitante</p>
                <h2 className="text-2xl font-bold text-stone-900">{ownerFilter.name}</h2>
                <p className="text-stone-500">{filteredItems.length} peças partilhadas</p>
              </div>
            </div>
            <Button onClick={onClearOwnerFilter} variant="outline" className="gap-2">
              <X className="h-4 w-4" />
              Voltar a ver tudo
            </Button>
          </div>
        )}

        {/* --- BARRA DE PESQUISA --- */}
        <div className="mb-6 space-y-4">
            <div className="flex gap-4">
                <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-stone-400" />
                <Input
                    placeholder="Pesquisar peças..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-white"
                />
                </div>
            </div>
        </div>

        {/* --- GRID (4 Colunas) --- */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {visibleItems.map(item => (
             <div
                key={item.id}
                className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer group border border-stone-100 flex flex-col h-full"
                onClick={() => onViewItem(item)}
             >
                <div className="relative bg-stone-50 h-64 overflow-hidden">
                    <img
                        src={item.image}
                        alt={item.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                     <div className="absolute top-2 right-2 flex flex-col gap-1">
                        {item.seasons.includes('Inverno') && <Badge className="bg-white/90 text-blue-600 hover:bg-white"><Droplet className="h-3 w-3"/></Badge>}
                     </div>
                </div>

                <div className="p-4 flex-1 flex flex-col justify-between">
                    <div>
                        <p className="font-semibold text-emerald-900 truncate" title={item.name}>{item.name}</p>
                        <p className="text-xs text-stone-500 mt-1">{item.type}</p>
                    </div>

                    {!ownerFilter && userType === 'visitor' && item.ownerAvatar && (
                        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-stone-100">
                            <img src={item.ownerAvatar} className="w-5 h-5 rounded-full object-cover" alt="User" />
                            <span className="text-xs text-stone-500 truncate">{item.ownerName}</span>
                        </div>
                    )}
                </div>
             </div>
          ))}
        </div>

        {/* --- BOTÃO CARREGAR MAIS --- */}
        {visibleCount < filteredItems.length && (
            <div className="mt-12 flex justify-center pb-8">
                <Button
                    variant="outline"
                    size="lg"
                    onClick={() => setVisibleCount(prev => prev + 8)}
                    className="group border-emerald-200 text-emerald-800 hover:bg-emerald-50 hover:text-emerald-900"
                >
                    Carregar Mais Peças
                    <ChevronDown className="ml-2 h-4 w-4 group-hover:translate-y-1 transition-transform" />
                </Button>
            </div>
        )}

        {/* Estado Vazio */}
        {filteredItems.length === 0 && (
            <div className="text-center py-20">
                <p className="text-stone-400">Nenhuma peça encontrada.</p>
                <Button variant="link" onClick={() => { setSearchQuery(''); }} className="text-emerald-600">Limpar filtros</Button>
            </div>
        )}
      </main>

      {/* ===== BOTÃO FAB ADICIONAR (VERDE) ===== */}
      {userType === 'client' && (
        <div
          onClick={() => setShowAddDialog(true)}
          style={{
            position: 'fixed',
            bottom: '32px',
            right: '32px',
            width: '64px',
            height: '64px',
            backgroundColor: '#10b981',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 10px 30px rgba(16, 185, 129, 0.4)',
            zIndex: 10000,
            transition: 'all 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1)';
            e.currentTarget.style.backgroundColor = '#059669';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.backgroundColor = '#10b981';
          }}
        >
          <Plus style={{ width: '32px', height: '32px', color: 'white', strokeWidth: 3 }} />
        </div>
      )}

      <AddItemDialog open={showAddDialog} onOpenChange={setShowAddDialog} onAdd={onAddItem} />

      {/* --- MODAL DE ESTATÍSTICAS --- */}
      <Dialog open={showStatsDialog} onOpenChange={setShowStatsDialog}>
        <DialogContent className="max-w-5xl w-full max-h-[85vh] overflow-y-auto">
          <DialogHeader className="mb-4">
            <DialogTitle className="text-xl font-semibold text-emerald-950 flex items-center gap-2">
              <TrendingUp className="h-5 w-5"/> Analytics do Guarda-Roupa
            </DialogTitle>
            <DialogDescription className="text-stone-500">
              Visão geral da composição do inventário.
            </DialogDescription>
          </DialogHeader>

          {totalItems > 0 ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                 <Card className="p-4 bg-emerald-50/50 border-emerald-100 flex flex-col">
                    <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide">Total de Peças</p>
                    <p className="text-2xl font-bold text-emerald-900 mt-1">{totalItems}</p>
                 </Card>
                 <Card className="p-4 bg-blue-50/50 border-blue-100 flex flex-col">
                    <p className="text-xs font-medium text-blue-600 uppercase tracking-wide">Estação Dominante</p>
                    <p className="text-xl font-bold text-blue-900 mt-1 truncate">{dominantSeason}</p>
                 </Card>
                 <Card className="p-4 bg-amber-50/50 border-amber-100 flex flex-col">
                    <p className="text-xs font-medium text-amber-600 uppercase tracking-wide">Material Top</p>
                    <p className="text-xl font-bold text-amber-900 mt-1 truncate">{topMaterial}</p>
                 </Card>
                 <Card className="p-4 bg-purple-50/50 border-purple-100 flex flex-col">
                    <p className="text-xs font-medium text-purple-600 uppercase tracking-wide">Top Categoria</p>
                    <p className="text-xl font-bold text-purple-900 mt-1 truncate">{topCategory}</p>
                 </Card>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <Card className="p-6 border-stone-200 shadow-sm flex flex-col">
                    <h3 className="text-sm font-semibold text-stone-700 uppercase mb-4 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-stone-400"/> Composição de Materiais
                    </h3>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={materialData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={85}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {materialData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={['#059669', '#0284c7', '#d97706', '#78716c', '#dc2626'][index % 5]} />
                            ))}
                          </Pie>
                          <RechartsTooltip contentStyle={{ fontSize: '12px' }} />
                          <Legend verticalAlign="middle" align="right" layout="vertical" iconType="circle" wrapperStyle={{ fontSize: '12px' }}/>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                 </Card>

                 <Card className="p-6 border-stone-200 shadow-sm flex flex-col">
                    <h3 className="text-sm font-semibold text-stone-700 uppercase mb-4 flex items-center gap-2">
                      <Thermometer className="h-4 w-4 text-stone-400"/> Distribuição por Estação
                    </h3>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={seasonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                          <XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={12} tick={{ fill: '#78716c' }} dy={10} />
                          <YAxis axisLine={false} tickLine={false} fontSize={12} tick={{ fill: '#78716c' }} />
                          <RechartsTooltip cursor={{fill: '#f5f5f4'}} contentStyle={{ fontSize: '12px' }} />
                          <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                 </Card>
              </div>
            </>
          ) : (
            <div className="text-center py-10 text-stone-500">Sem dados suficientes para gerar estatísticas.</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// --- FUNÇÕES AUXILIARES ---

function getMaterialData(items: ClothingItem[]) {
  // O "|| []" impede o site de ir abaixo se uma peça não tiver materiais
  const allMaterials = items.flatMap(i => i.materials || []);
  const counts: Record<string, number> = {};
  allMaterials.forEach(m => {
    if (m) counts[m] = (counts[m] || 0) + 1;
  });
  return Object.entries(counts).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 5);
}

function getSeasonData(items: ClothingItem[]) {
  const seasons = ['Inverno', 'Outono', 'Primavera', 'Verão'];
  const counts: Record<string, number> = { 'Inverno': 0, 'Outono': 0, 'Primavera': 0, 'Verão': 0 };
  items.forEach(item => {
    (item.seasons || []).forEach(s => {
      if (counts[s] !== undefined) counts[s]++;
    });
  });
  return Object.entries(counts).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
}

function getTopCategories(items: ClothingItem[]) {
  const counts: Record<string, number> = {};
  items.forEach(i => {
    if (i.type) counts[i.type] = (counts[i.type] || 0) + 1;
  });
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3);
}