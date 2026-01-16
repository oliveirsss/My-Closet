import { useState, useEffect } from "react";
import { ClothingItem, Screen, UserType } from "../../types";
import { toast } from "sonner";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import {
  Search,
  Droplet,
  LogOut,
  Home,
  Camera,
  TrendingUp,
  Zap,
  User,
  X,
  ChevronDown,
  BarChart3,
  Shirt,
  Thermometer,
  Plus,
  Heart,
  Waves,
  Layers,
  Tag,
  Crown,
  Sparkles,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { AddItemDialog } from "./AddItemDialog";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

interface InventoryProps {
  items: ClothingItem[];
  userType: UserType;
  onNavigate: (screen: Screen) => void;
  onLogout: () => void;
  onAddItem: (item: ClothingItem) => void;
  onViewItem: (item: ClothingItem) => void;
  ownerFilter?: { id: string; name: string; avatar?: string } | null;
  onClearOwnerFilter?: () => void;
  onToggleFavorite: (item: ClothingItem) => void;
  onViewOwner: (ownerId: string, ownerName: string, avatar?: string) => void;
  viewMode?: "personal" | "community";
  onToggleViewMode?: () => void;
  showLikedOnly?: boolean;
  onToggleLikedOnly?: () => void;
}

export function Inventory({
  items,
  userType,
  onNavigate,
  onLogout,
  onAddItem,
  onViewItem,
  onToggleFavorite,
  ownerFilter,
  onClearOwnerFilter,
  onViewOwner,
  viewMode = "personal",
  onToggleViewMode,
  showLikedOnly,
  onToggleLikedOnly,
}: InventoryProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showStatsDialog, setShowStatsDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(8);
  const [showDirtyOnly, setShowDirtyOnly] = useState(false);
  const [brandFilter, setBrandFilter] = useState<string>("all");
  const [sizeFilter, setSizeFilter] = useState<string>("all");

  // Resetar a paginação ao mudar filtros
  useEffect(() => {
    setVisibleCount(8);
  }, [searchQuery, filterType, ownerFilter, brandFilter, sizeFilter]);

  // Derived Data for Filters
  const uniqueBrands = Array.from(new Set(items.map(i => i.brand).filter(Boolean))).sort();
  const uniqueSizes = Array.from(new Set(items.map(i => i.size).filter(Boolean))).sort();

  // Community Spotlight Logic (Find user with most items)
  // RUNS IF: user matches 'visitor' OR (client AND viewing community)
  const featuredUser = (() => {
    if (userType === 'client' && viewMode === 'personal') return null;

    const ownerCounts: Record<string, { count: number, id: string, name: string, avatar?: string }> = {};
    items.forEach(item => {
      if (item.ownerId && item.ownerName) {
        if (!ownerCounts[item.ownerId]) {
          ownerCounts[item.ownerId] = { count: 0, id: item.ownerId, name: item.ownerName, avatar: item.ownerAvatar };
        }
        ownerCounts[item.ownerId].count++;
      }
    });

    const owners = Object.values(ownerCounts);
    if (owners.length === 0) return null;

    // Sort by count descending
    return owners.sort((a, b) => b.count - a.count)[0];
  })();

  // --- Lógica de Filtragem ---
  const filteredItems = items.filter((item) => {
    if (ownerFilter && item.ownerId !== ownerFilter.id) return false;
    if (showDirtyOnly && item.status !== "dirty") return false;
    if (
      searchQuery &&
      !item.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    if (filterType && item.type !== filterType) return false;
    if (brandFilter !== "all" && item.brand !== brandFilter) return false;
    if (sizeFilter !== "all" && item.size !== sizeFilter) return false;
    return true;
  });

  // Itens visíveis (Paginação)
  const visibleItems = filteredItems.slice(0, visibleCount);

  // --- Dados para as Estatísticas ---
  const materialData = getMaterialData(items);
  const seasonData = getSeasonData(items);
  const topCategories = getTopCategories(items);
  const totalItems = items.length;
  const dominantSeason = seasonData.length > 0 ? seasonData[0].name : "-";
  const topMaterial = materialData.length > 0 ? materialData[0].name : "-";
  const topCategory = topCategories.length > 0 ? topCategories[0][0] : "-";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* --- HEADER --- */}
      <header className="bg-white border-b border-stone-200 px-6 py-4 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* TOGGLE: My Closet vs Our Closet (Only for Clients) */}
            {userType === 'client' ? (
              <div className="flex bg-stone-100 p-1 rounded-lg border border-stone-200">
                <button
                  onClick={() => onToggleViewMode && viewMode !== 'personal' && onToggleViewMode()}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'personal' ? 'bg-white text-emerald-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'}`}
                >
                  My Closet
                </button>
                <button
                  onClick={() => onToggleViewMode && viewMode !== 'community' && onToggleViewMode()}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === 'community' ? 'bg-white text-emerald-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'}`}
                >
                  Our Closet
                </button>
              </div>
            ) : (
              <h1 className="text-2xl text-emerald-900 font-semibold flex items-center gap-2">
                <span>Our Closet</span>
                <span className="text-sm font-normal text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full border border-stone-200">
                  Comunidade
                </span>
              </h1>
            )}
          </div>

          <div className="flex gap-2">
            {userType === "client" ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => onNavigate("dashboard")}
                >
                  <Home className="mr-2 h-4 w-4" />
                  Dashboard
                </Button>
                {viewMode === 'personal' && (
                  <Button variant="outline" onClick={() => onNavigate("search")}>
                    <Camera className="mr-2 h-4 w-4" />
                    Pesquisa
                  </Button>
                )}
              </>
            ) : null}

            {/* BOTÃO LAVANDARIA - Apenas para Client e My Closet */}
            {userType === "client" && viewMode === 'personal' && (
              <Button
                variant={showDirtyOnly ? "default" : "outline"}
                onClick={() => setShowDirtyOnly(!showDirtyOnly)}
                className={`${showDirtyOnly
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "text-blue-600 border-blue-200 hover:bg-blue-50"
                  }`}
              >
                <Waves className="h-4 w-4 mr-2" />
                {showDirtyOnly ? "Ver Tudo" : "Lavandaria"}
              </Button>
            )}

            {/* Removed Meus Likes from Header */}

            {/* BOTÃO INSIGHTS - Agora visível em ambos, mas talvez com dados diferentes? Por agora, mostra sempre para Client */}
            {userType === 'client' && (
              <Button
                variant="outline"
                onClick={() => setShowStatsDialog(true)}
                className="text-emerald-700 border-emerald-200 hover:bg-emerald-50"
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Insights
              </Button>
            )}

            <Button variant="ghost" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {/* --- HEADER DE PERFIL --- */}
        {ownerFilter && (
          <div className="mb-8 p-6 bg-white rounded-xl shadow-sm border border-stone-200 flex items-center justify-between animate-in fade-in slide-in-from-top-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 overflow-hidden border border-emerald-200">
                {ownerFilter.avatar ? (
                  <img src={ownerFilter.avatar} className="w-full h-full object-cover" alt={ownerFilter.name} />
                ) : (
                  <User className="h-8 w-8" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm text-stone-500 uppercase tracking-wide font-bold">
                    Perfil de Visitante
                  </p>
                  {featuredUser?.id === ownerFilter.id && (
                    <Badge className="bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-100 gap-1 px-2 py-0">
                      <Sparkles className="w-3 h-3" />
                      Top Creator
                    </Badge>
                  )}
                </div>
                <h2 className="text-2xl font-bold text-stone-900">
                  {ownerFilter.name}
                </h2>
                <p className="text-stone-500">
                  {filteredItems.length} peças partilhadas
                </p>
              </div>
            </div>
            <Button
              onClick={onClearOwnerFilter}
              variant="outline"
              className="gap-2"
            >
              <X className="h-4 w-4" />
              Voltar a ver tudo
            </Button>
          </div>
        )}

        {/* --- SPOTLIGHT BANNER (Community Only) --- */}
        {featuredUser && !searchQuery && !ownerFilter && (
          <div className="mb-8 p-6 bg-slate-900 rounded-2xl shadow-xl text-white relative overflow-hidden group">
            {/* Background Pattern */}
            <div className="absolute inset-0 opacity-20 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500 via-transparent to-transparent" />

            <div className="absolute top-0 right-0 p-8 opacity-10 transform rotate-12 group-hover:rotate-6 transition-transform duration-700">
              <Crown className="w-40 h-40 text-white" />
            </div>

            <div className="relative z-10 flex flex-col sm:flex-row items-center sm:items-start gap-6 text-center sm:text-left">
              <div className="shrink-0 relative">
                <div className="w-24 h-24 rounded-full border-4 border-white/20 p-1 flex items-center justify-center bg-white/5 backdrop-blur-sm shadow-inner">
                  {featuredUser.avatar ? (
                    <img src={featuredUser.avatar} className="w-full h-full rounded-full object-cover shadow-sm bg-white" alt={featuredUser.name} />
                  ) : (
                    <User className="w-10 h-10 text-white/50" />
                  )}
                </div>
                <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-amber-400 text-amber-950 text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm flex items-center gap-1 whitespace-nowrap">
                  <Sparkles className="w-3 h-3" />
                  TOP CREATOR
                </div>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-center sm:justify-start gap-2 mb-2">
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-300">Community Spotlight</span>
                </div>
                <h2 className="text-3xl font-bold mb-2 tracking-tight text-white drop-shadow-sm">
                  O Closet de <span className="text-amber-300">{featuredUser.name}</span> está em alta!
                </h2>
                <p className="text-slate-300 mb-6 max-w-lg text-lg">
                  Descobre a coleção que está a inspirar a comunidade, com <strong className="text-white">{featuredUser.count} peças</strong> incríveis.
                </p>
                <Badge
                  className="bg-white text-slate-900 hover:bg-indigo-50 border-none cursor-pointer px-6 py-2.5 text-sm font-semibold transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
                  onClick={() => onViewOwner(featuredUser.id, featuredUser.name, featuredUser.avatar)}
                >
                  Explorar Closet
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* --- BARRA DE PESQUISA E FILTROS --- */}
        <div className="mb-6 flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-stone-400" />
            <Input
              placeholder="Pesquisar peças..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white"
            />
          </div>

          <div className="flex gap-2">
            <Select value={brandFilter} onValueChange={setBrandFilter}>
              <SelectTrigger className="w-[140px] bg-white">
                <SelectValue placeholder="Marca" />
              </SelectTrigger>
              <SelectContent className="bg-white">
                <SelectItem value="all">Todas as Marcas</SelectItem>
                {uniqueBrands.map(brand => (
                  <SelectItem key={brand} value={brand}>{brand}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sizeFilter} onValueChange={setSizeFilter}>
              <SelectTrigger className="w-[100px] bg-white">
                <SelectValue placeholder="Tam." />
              </SelectTrigger>
              <SelectContent className="bg-white">
                <SelectItem value="all">Todos</SelectItem>
                {uniqueSizes.map(size => (
                  <SelectItem key={size} value={size}>{size}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* FILTER: FAVORITOS (Likes in Community / Favorites in Personal) */}
            {userType === "client" && (
              <Button
                variant={showLikedOnly ? "default" : "outline"}
                onClick={onToggleLikedOnly}
                className={`bg-white ${showLikedOnly
                  ? "bg-red-600 hover:bg-red-700 text-white border-red-600"
                  : "text-stone-500 border-stone-200 hover:bg-stone-50"
                  }`}
                title="Ver apenas peças que gostei"
              >
                <Heart className={`h-4 w-4 mr-2 ${showLikedOnly ? "fill-white" : ""}`} />
                Favoritos
              </Button>
            )}


          </div>
        </div>

        {/* --- GRID (4 Colunas) --- */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {visibleItems.map((item) => (
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
                <div className="absolute top-2 right-2 flex flex-col gap-1 items-end">
                  {!ownerFilter && ( // Removed userType check to show for visitors too
                    <FavoriteButton
                      isFavorite={viewMode === 'community' ? !!item.isLikedByMe : item.favorite}
                      onToggle={(item) => {
                        if (userType === 'visitor') {
                          toast.error("Faz login ou cria conta para dar Like! ❤️", {
                            action: {
                              label: "Login",
                              onClick: () => window.location.reload() // Or navigate to login? App handles login via state.
                              // Actually, I can't easily navigate to login from here without callback.
                              // Simple toast is enough for now.
                            }
                          });
                          return;
                        }
                        onToggleFavorite(item);
                      }}
                      item={item}
                    />
                  )}
                  {item.seasons.includes("Inverno") && (
                    <Badge className="bg-white/90 text-blue-600 hover:bg-white">
                      <Droplet className="h-3 w-3" />
                    </Badge>
                  )}
                </div>
              </div>

              <div className="p-4 flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start">
                    <p
                      className="font-semibold text-emerald-900 truncate flex-1"
                      title={item.name}
                    >
                      {item.name}
                    </p>
                    {item.status === "dirty" && userType === "client" && (
                      <Badge variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-200 text-[10px] h-5 px-1.5 ml-2 shrink-0">
                        <Waves className="w-3 h-3 mr-1" />
                        Lavar
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-stone-500 mt-1">{item.type}</p>

                  {/* Brand and Size Chips */}
                  <div className="flex gap-2 mt-2">
                    {item.brand && (
                      <span className="text-[10px] font-medium bg-stone-100 text-stone-600 px-2 py-0.5 rounded-full border border-stone-200">
                        {item.brand}
                      </span>
                    )}
                    {item.size && (
                      <span className="text-[10px] font-medium bg-stone-100 text-stone-600 px-2 py-0.5 rounded-full border border-stone-200">
                        {item.size}
                      </span>
                    )}
                  </div>
                </div>

                {!ownerFilter && (userType === "visitor" || viewMode === "community") && (item.ownerAvatar || item.ownerName) && (
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-stone-100">
                    {item.ownerAvatar ? (
                      <img
                        src={item.ownerAvatar}
                        className="w-5 h-5 rounded-full object-cover"
                        alt="User"
                      />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-stone-100 flex items-center justify-center">
                        <User className="w-3 h-3 text-stone-400" />
                      </div>
                    )}
                    <span className="text-xs text-stone-500 truncate">
                      {item.ownerName || "Utilizador Desconhecido"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
          }
        </div >

        {/* --- BOTÃO CARREGAR MAIS --- */}
        {
          visibleCount < filteredItems.length && (
            <div className="mt-12 flex justify-center pb-8">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setVisibleCount((prev) => prev + 8)}
                className="group border-emerald-200 text-emerald-800 hover:bg-emerald-50 hover:text-emerald-900"
              >
                Carregar Mais Peças
                <ChevronDown className="ml-2 h-4 w-4 group-hover:translate-y-1 transition-transform" />
              </Button>
            </div>
          )
        }

        {/* Estado Vazio */}
        {
          filteredItems.length === 0 && (
            <div className="text-center py-20">
              <p className="text-stone-400">Nenhuma peça encontrada.</p>
              <Button
                variant="link"
                onClick={() => {
                  setSearchQuery("");
                }}
                className="text-emerald-600"
              >
                Limpar filtros
              </Button>
            </div>
          )
        }
      </main >

      {/* ===== BOTÃO FAB ADICIONAR (VERDE) - Apenas em My Closet ===== */}
      {
        userType === "client" && viewMode === 'personal' && (
          <div
            onClick={() => setShowAddDialog(true)}
            style={{
              position: "fixed",
              bottom: "32px",
              right: "32px",
              width: "64px",
              height: "64px",
              backgroundColor: "#10b981",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 10px 30px rgba(16, 185, 129, 0.4)",
              zIndex: 10000,
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "scale(1.1)";
              e.currentTarget.style.backgroundColor = "#059669";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "scale(1)";
              e.currentTarget.style.backgroundColor = "#10b981";
            }}
          >
            <Plus
              style={{
                width: "32px",
                height: "32px",
                color: "white",
                strokeWidth: 3,
              }}
            />
          </div>
        )
      }

      <AddItemDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onAdd={onAddItem}
      />

      <Dialog open={showStatsDialog} onOpenChange={setShowStatsDialog}>
        <DialogContent className="max-w-[90vw] xl:max-w-7xl w-full max-h-[90vh] overflow-y-auto bg-white">
          <DialogHeader className="mb-8 p-2">
            <DialogTitle className="text-2xl font-bold text-stone-900 flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg text-emerald-700">
                <BarChart3 className="h-6 w-6" />
              </div>
              <div className="flex flex-col">
                <span>Analytics do Guarda-Roupa</span>
                <span className="text-sm font-normal text-stone-500">
                  Visão detalhada e métricas do seu inventário
                </span>
              </div>
            </DialogTitle>
          </DialogHeader>

          {totalItems > 0 ? (
            <div className="space-y-8 p-1">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="p-6 border-none shadow-sm bg-white relative overflow-hidden group hover:shadow-md transition-all">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Shirt className="h-24 w-24 text-emerald-900" />
                  </div>
                  <div className="relative z-10">
                    <p className="text-sm font-medium text-stone-500 uppercase tracking-wider mb-2">
                      Total de Peças
                    </p>
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-4xl font-bold text-stone-900">
                        {totalItems}
                      </h4>
                      <span className="text-sm text-emerald-600 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">
                        Itens
                      </span>
                    </div>
                  </div>
                </Card>

                <Card className="p-6 border-none shadow-sm bg-white relative overflow-hidden group hover:shadow-md transition-all">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Thermometer className="h-24 w-24 text-blue-900" />
                  </div>
                  <div className="relative z-10">
                    <p className="text-sm font-medium text-stone-500 uppercase tracking-wider mb-2">
                      Estação Dominante
                    </p>
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-3xl font-bold text-stone-900 break-words leading-tight" title={dominantSeason}>
                        {dominantSeason}
                      </h4>
                    </div>
                    <p className="text-xs text-stone-400 mt-2">
                      Baseado na frequência de uso
                    </p>
                  </div>
                </Card>

                <Card className="p-6 border-none shadow-sm bg-white relative overflow-hidden group hover:shadow-md transition-all">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Layers className="h-24 w-24 text-amber-900" />
                  </div>
                  <div className="relative z-10">
                    <p className="text-sm font-medium text-stone-500 uppercase tracking-wider mb-2">
                      Material Top
                    </p>
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-3xl font-bold text-stone-900 break-words leading-tight" title={topMaterial}>
                        {topMaterial}
                      </h4>
                    </div>
                    <p className="text-xs text-stone-400 mt-2">
                      Material mais comum
                    </p>
                  </div>
                </Card>

                <Card className="p-6 border-none shadow-sm bg-white relative overflow-hidden group hover:shadow-md transition-all">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Tag className="h-24 w-24 text-purple-900" />
                  </div>
                  <div className="relative z-10">
                    <p className="text-sm font-medium text-stone-500 uppercase tracking-wider mb-2">
                      Top Categoria
                    </p>
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-3xl font-bold text-stone-900 break-words leading-tight" title={topCategory}>
                        {topCategory}
                      </h4>
                    </div>
                    <p className="text-xs text-stone-400 mt-2">
                      Tipo de peça mais frequente
                    </p>
                  </div>
                </Card>
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Materials Chart */}
                <Card className="border-none shadow-sm bg-white p-6 flex flex-col">
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h3 className="text-lg font-bold text-stone-900">
                        Composição de Materiais
                      </h3>
                      <p className="text-sm text-stone-500">Distribuição dos materiais no inventário</p>
                    </div>
                    <div className="p-2 bg-stone-50 rounded-full">
                      <Zap className="h-5 w-5 text-stone-400" />
                    </div>
                  </div>

                  <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={materialData}
                          cx="50%"
                          cy="50%"
                          innerRadius={80}
                          outerRadius={110}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {materialData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444"][index % 5]}
                              stroke="#fff"
                              strokeWidth={2}
                            />
                          ))}
                        </Pie>
                        <RechartsTooltip
                          contentStyle={{
                            borderRadius: '8px',
                            border: 'none',
                            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                          }}
                        />
                        <Legend
                          verticalAlign="middle"
                          align="right"
                          layout="vertical"
                          iconType="circle"
                          iconSize={8}
                          wrapperStyle={{ fontSize: "13px", color: "#57534e" }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                {/* Seasons Chart */}
                <Card className="border-none shadow-sm bg-white p-6 flex flex-col">
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h3 className="text-lg font-bold text-stone-900">
                        Distribuição por Estação
                      </h3>
                      <p className="text-sm text-stone-500">Quantidade de peças por estação do ano</p>
                    </div>
                    <div className="p-2 bg-stone-50 rounded-full">
                      <Thermometer className="h-5 w-5 text-stone-400" />
                    </div>
                  </div>

                  <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={seasonData}
                        margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
                        barSize={40}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          vertical={false}
                          stroke="#e7e5e4"
                        />
                        <XAxis
                          dataKey="name"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#78716c", fontSize: 13 }}
                          dy={10}
                        />
                        <YAxis
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#78716c", fontSize: 13 }}
                        />
                        <RechartsTooltip
                          cursor={{ fill: "#f5f5f4", radius: 4 }}
                          contentStyle={{
                            borderRadius: '8px',
                            border: 'none',
                            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                          }}
                        />
                        <Bar
                          dataKey="value"
                          fill="#3b82f6"
                          radius={[6, 6, 0, 0]}
                        >
                          {seasonData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.name === 'Verão' ? '#f59e0b' : entry.name === 'Inverno' ? '#3b82f6' : entry.name === 'Primavera' ? '#10b981' : '#f97316'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-stone-200 m-1">
              <div className="w-16 h-16 bg-stone-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="h-8 w-8 text-stone-300" />
              </div>
              <h3 className="text-lg font-medium text-stone-900 mb-1">Sem dados suficientes</h3>
              <p className="text-stone-500">
                Adicione peças ao seu guarda-roupa para gerar estatísticas.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// --- FUNÇÕES AUXILIARES ---

function getMaterialData(items: ClothingItem[]) {
  // O "|| []" impede o site de ir abaixo se uma peça não tiver materiais
  const allMaterials = items.flatMap((i) => i.materials || []);
  const counts: Record<string, number> = {};
  allMaterials.forEach((m) => {
    if (m) counts[m] = (counts[m] || 0) + 1;
  });
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);
}

function getSeasonData(items: ClothingItem[]) {
  const seasons = ["Inverno", "Outono", "Primavera", "Verão"];
  const counts: Record<string, number> = {
    Inverno: 0,
    Outono: 0,
    Primavera: 0,
    Verão: 0,
  };
  items.forEach((item) => {
    (item.seasons || []).forEach((s) => {
      if (counts[s] !== undefined) counts[s]++;
    });
  });
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

// --- COMPONENTES AUXILIARES ---

function FavoriteButton({
  isFavorite,
  onToggle,
  item,
}: {
  isFavorite: boolean;
  onToggle: (item: ClothingItem) => void;
  item: ClothingItem;
}) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsAnimating(true);
    onToggle({ ...item, favorite: !isFavorite });

    // Reset animation state after animation duration
    setTimeout(() => setIsAnimating(false), 400);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      className={`h-8 w-8 rounded-full bg-white/80 hover:bg-white transition-all shadow-sm mb-1 ${isAnimating ? "animate-pop" : ""
        }`}
      onClick={handleClick}
    >
      <Heart
        className={`h-4 w-4 transition-colors duration-300 ${isFavorite ? "fill-red-500 text-red-500" : "text-stone-500"
          }`}
      />
    </Button>
  );
}

function getTopCategories(items: ClothingItem[]) {
  const counts: Record<string, number> = {};
  items.forEach((i) => {
    if (i.type) counts[i.type] = (counts[i.type] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
}
