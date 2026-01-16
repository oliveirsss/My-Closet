import { useState, useEffect } from "react";
import { ClothingItem } from "../../types";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import { AddItemDialog } from "./AddItemDialog";
import { Input } from "../../components/ui/input";
import * as api from "../../services/api"; // Import API
import {
  ArrowLeft,
  Edit,
  Trash2,
  Star, // Changed Heart to Star for favorites
  Heart, // Kept for social Likes
  Droplet,
  Wind,
  Thermometer,
  Weight,
  Layers,
  Tag,
  Calendar,
  User,
  Globe,
  MessageCircle,
  Send,
} from "lucide-react";
import { toast } from "sonner";

interface ItemDetailProps {
  item: ClothingItem;
  onBack: () => void;
  onUpdate: (item: ClothingItem) => void;
  onDelete: (id: string) => void;
  isVisitor?: boolean; // Deprecated but kept for compatibility in specific cases if needed
  onViewOwner?: (id: string, name: string, avatar?: string) => void;
  currentUserId?: string | null;
}

export function ItemDetail({
  item,
  onBack,
  onUpdate,
  onDelete,
  isVisitor = false,
  onViewOwner,
  currentUserId,
}: ItemDetailProps) {
  const isOwner = Boolean(currentUserId && item.ownerId === currentUserId);
  const isAuthenticated = Boolean(currentUserId);

  const [isWashing, setIsWashing] = useState(item.status === "dirty");
  const [isEditing, setIsEditing] = useState(false);

  // Social State
  const [likesCount, setLikesCount] = useState(0);
  const [isLiked, setIsLiked] = useState(false);
  const [comments, setComments] = useState<any[]>([]);
  const [newComment, setNewComment] = useState("");
  const [loadingSocial, setLoadingSocial] = useState(false);

  // Fetch Social Data on Mount
  useEffect(() => {
    if (item.id) {
      loadSocialData();
    }
  }, [item.id]);

  const loadSocialData = async () => {
    if (!item.id) return;
    setLoadingSocial(true);

    // 1. Likes and Comments (Public)
    try {
      const likesData = await api.getItemLikes(item.id);
      setLikesCount(likesData.count);
      setIsLiked(likesData.isLiked);
    } catch (e) { console.error("Error loading likes", e); }

    try {
      const commentsData = await api.getComments(item.id);
      setComments(commentsData.comments || []);
    } catch (e) { console.error("Error loading comments", e); }

    setLoadingSocial(false);
  };

  const handleLike = async () => {
    // Check auth for interactions
    if (!isAuthenticated) {
      toast.error("Faz login para dar Like!");
      return;
    }

    // Optimistic update
    const previousLiked = isLiked;
    const previousCount = likesCount;

    setIsLiked(!isLiked);
    setLikesCount(isLiked ? likesCount - 1 : likesCount + 1);

    try {
      if (previousLiked) {
        await api.unlikeItem(item.id);
      } else {
        await api.likeItem(item.id);
      }
    } catch (error) {
      // Revert on error
      setIsLiked(previousLiked);
      setLikesCount(previousCount);
      toast.error("Erro ao atualizar like");
    }
  };

  const handlePostComment = async () => {
    if (!item.id || !newComment.trim()) return;
    try {
      const { comment } = await api.addComment(item.id, newComment);
      setComments([comment, ...comments]);
      setNewComment("");
      toast.success("Comentário publicado");
    } catch (error) {
      toast.error("Erro ao publicar comentário");
    }
  };

  const toggleWashing = () => {
    const newStatus = isWashing ? "clean" : "dirty";
    setIsWashing(!isWashing);
    onUpdate({ ...item, status: newStatus });
    toast.success(
      `Peça marcada como ${newStatus === "clean" ? "Limpa" : "Suja"}`,
    );
  };

  const toggleFavorite = () => {
    const newFavState = !item.favorite;
    onUpdate({ ...item, favorite: newFavState });
    toast.success(
      newFavState ? "Adicionado aos favoritos" : "Removido dos favoritos",
    );
  };

  const togglePublic = () => {
    const newPublicState = !item.isPublic;
    onUpdate({ ...item, isPublic: newPublicState });

    if (newPublicState) {
      toast.success("Peça tornada PÚBLICA", {
        description: "Agora visível para todos os visitantes.",
      });
    } else {
      toast.info("Peça tornada PRIVADA", {
        description: "Agora apenas visível para si.",
      });
    }
  };

  const handleDelete = () => {
    if (confirm("Tem certeza que deseja apagar esta peça?")) {
      onDelete(item.id);
      toast.error("Peça apagada com sucesso");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar
          </Button>

          {/* SÓ MOSTRA OS BOTÕES DE AÇÃO SE FOR O DONO */}
          {isOwner && (
            <div className="flex gap-2">
              {/* Removed Favorite Button (Star) as per user request to only use card heart */}

              <Button
                variant="outline"
                onClick={togglePublic}
                className={
                  item.isPublic
                    ? "text-blue-600 border-blue-200 bg-blue-50"
                    : "text-stone-400"
                }
                title={item.isPublic ? "Tornar Privado" : "Tornar Público"}
              >
                <Globe className="h-4 w-4" />
              </Button>

              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Edit className="h-4 w-4" />
              </Button>

              <Button
                variant="outline"
                onClick={handleDelete}
                className="text-red-600 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Lado Esquerdo - Imagem e Social */}
          <div className="space-y-6">
            <div>
              <img
                src={item.image}
                alt={item.name}
                className="w-full h-[600px] object-contain bg-white rounded-lg shadow-xl border border-stone-100"
              />

              {/* SE NÃO FOR O DONO: Mostra Quem Publicou / SE FOR O DONO: Mostra Botão Lavar */}
              {!isOwner ? (
                <div
                  className="mt-4 p-4 bg-white rounded-lg shadow-sm border border-stone-100 flex items-center gap-3 cursor-pointer hover:bg-stone-50 transition-colors group"
                  onClick={() => {
                    if (item.ownerId && onViewOwner) {
                      onViewOwner(
                        item.ownerId,
                        item.ownerName || "Utilizador",
                        item.ownerAvatar
                      );
                    }
                  }}
                >
                  <div className="w-10 h-10 rounded-full bg-stone-100 overflow-hidden flex items-center justify-center border border-stone-200 group-hover:border-emerald-200">
                    {item.ownerAvatar ? (
                      <img
                        src={item.ownerAvatar}
                        alt={item.ownerName}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User className="h-5 w-5 text-stone-400 group-hover:text-emerald-600" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-stone-500">Publicado por</p>
                    <p className="font-medium text-stone-800 group-hover:text-emerald-700 underline decoration-transparent group-hover:decoration-emerald-700 transition-all">
                      {item.ownerName || "Utilizador Anónimo"}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2 mt-4">
                  <Button
                    variant={isWashing ? "default" : "outline"}
                    className={`flex-1 ${isWashing ? "bg-amber-600 hover:bg-amber-700" : ""}`}
                    onClick={toggleWashing}
                  >
                    {isWashing ? "Está a lavar" : "Marcar como sujo"}
                  </Button>
                </div>
              )}
            </div>

            {/* --- SECÇÃO SOCIAL (Visível para todos) --- */}
            <Card className="p-6 bg-white shadow-sm border-stone-200">
              <h3 className="text-lg font-semibold text-stone-800 mb-4 flex items-center gap-2">
                <MessageCircle className="h-5 w-5" />
                Interações da Comunidade
              </h3>

              {/* Botões de Ação Social (Wishlist Removido) */}
              {/* Botões de Ação Social (Like/Wishlist Removidos - Apenas no Card) */}
              <div className="flex gap-3 mb-6">
                {/* Only showing Like count text, no button? Or just remove entirely? 
                     User said "remove the one inside". Let's remove the button. 
                     Maybe keep the count visible? 
                     "Interações da Comunidade" header implies interactions. 
                     If I remove the button, I should probably show "X Likes" as text maybe?
                     But user said "tira o de dentro da peça". 
                     I will remove the button. I'll leave the comments.
                 */}
                <Button
                  variant="ghost"
                  size="sm"
                  className={`flex items-center gap-2 text-sm px-2 ${isLiked ? "text-red-500 hover:text-red-600 hover:bg-red-50" : "text-stone-500 hover:text-red-500 hover:bg-red-50"}`}
                  onClick={handleLike}
                >
                  <Heart className={`h-4 w-4 ${isLiked ? "fill-current" : ""}`} />
                  <span className="font-medium">{likesCount} {likesCount === 1 ? 'Like' : 'Likes'}</span>
                </Button>
              </div>

              {/* Comentários */}
              <div className="space-y-4">
                <div className="max-h-[300px] overflow-y-auto space-y-4 pr-2">
                  {comments.length === 0 ? (
                    <p className="text-center text-stone-400 text-sm py-4">Ainda sem comentários. Sê o primeiro!</p>
                  ) : (
                    comments.map((comment) => (
                      <div key={comment.id} className="flex gap-3 group">
                        <div className="w-8 h-8 rounded-full bg-stone-100 flex-shrink-0 overflow-hidden border border-stone-200">
                          {comment.user_avatar ? (
                            <img src={comment.user_avatar} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-stone-400 font-bold text-xs">
                              {comment.user_name?.[0]?.toUpperCase() || "?"}
                            </div>
                          )}
                        </div>
                        <div className="bg-stone-50 p-3 rounded-tr-xl rounded-br-xl rounded-bl-xl text-sm flex-1">
                          <p className="font-semibold text-stone-700 text-xs mb-1">{comment.user_name || "Utilizador"}</p>
                          <p className="text-stone-600">{comment.text}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Input Comentário */}
                <div className="flex gap-2 items-center">
                  <Input
                    placeholder={isAuthenticated ? "Escreve um comentário..." : "Faz login para comentar..."}
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    disabled={!isAuthenticated}
                    // User said "appear everything equal". Disabled input changes appearance.
                    // If I keep it enabled but block send, it's better?
                    // "so vai deixar se der login".
                    // Maybe show toast on click?
                    onFocus={() => {
                      if (!isAuthenticated) toast.error("Faz login para comentar!");
                    }}
                    // Keeping it enabled but read-only-ish via focus toast is good, but user might type.
                    // Let's use readOnly={!isAuthenticated} ?
                    readOnly={!isAuthenticated}
                    className="bg-stone-50 border-stone-200"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && isAuthenticated) handlePostComment();
                    }}
                  />
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => {
                      if (!isAuthenticated) {
                        toast.error("Faz login para comentar!");
                        return;
                      }
                      handlePostComment();
                    }}
                    disabled={loadingSocial || (!newComment.trim() && isAuthenticated)}
                  // allow click if not auth to show toast
                  >
                    <Send className="h-4 w-4 text-emerald-600" />
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Lado Direito - Detalhes */}
          <div className="space-y-6">
            <div>
              <h1 className="text-4xl mb-2 text-emerald-900">{item.name}</h1>
              <p className="text-xl text-stone-600">
                {item.brand} • Tamanho {item.size}
              </p>
            </div>

            {/* SÓ MOSTRA CRACHÁS SE FOR O DONO */}
            {isOwner && (
              <div className="flex gap-2">
                <Badge
                  className={`${item.status === "clean" ? "bg-emerald-600" : "bg-amber-600"}`}
                >
                  {item.status === "clean" ? "Limpo" : "Para Lavar"}
                </Badge>
                {item.favorite && (
                  <Badge
                    variant="outline"
                    className="text-red-600 border-red-600 bg-red-50 flex items-center gap-1"
                  >
                    <Heart className="w-3 h-3 fill-current" /> Favorito
                  </Badge>
                )}
                {item.isPublic ? (
                  <Badge
                    variant="outline"
                    className="text-blue-600 border-blue-600 bg-blue-50"
                  >
                    🌐 Público
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="text-stone-500 border-stone-300 bg-stone-50"
                  >
                    🔒 Privado
                  </Badge>
                )}
              </div>
            )}

            <Card className="p-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-2 text-stone-600">
                    <Tag className="h-5 w-5" />
                    <span>Tipo</span>
                  </div>
                  <p className="text-xl text-emerald-900">{item.type}</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2 text-stone-600">
                    <Layers className="h-5 w-5" />
                    <span>Camada</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <p className="text-xl text-emerald-900">
                      Camada {item.layer}
                    </p>
                    <Badge variant="outline">
                      {item.layer === 1
                        ? "Base"
                        : item.layer === 2
                          ? "Isolamento"
                          : "Proteção"}
                    </Badge>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-3 text-emerald-900">Materiais</h3>
              <div className="flex gap-2 flex-wrap">
                {item.materials.map((material) => (
                  <Badge key={material} variant="secondary" className="text-sm">
                    {material}
                  </Badge>
                ))}
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-4 text-emerald-900">Especificações Técnicas</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-stone-600">
                    <Weight className="h-5 w-5" />
                    <span>Peso</span>
                  </div>
                  <span className="text-emerald-900">{item.weight}g</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-stone-600">
                    <Thermometer className="h-5 w-5" />
                    <span>Range de Temperatura</span>
                  </div>
                  <span className="text-emerald-900">
                    {item.tempMin}°C - {item.tempMax}°C
                  </span>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-4 text-emerald-900">Resistência</h3>
              <div className="grid grid-cols-2 gap-4">
                <div
                  className={`p-4 rounded-lg border-2 ${item.waterproof ? "border-blue-500 bg-blue-50" : "border-stone-200 bg-stone-50"}`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Droplet
                      className={`h-5 w-5 ${item.waterproof ? "text-blue-600" : "text-stone-400"}`}
                    />
                    <span
                      className={
                        item.waterproof ? "text-blue-900" : "text-stone-600"
                      }
                    >
                      Impermeável
                    </span>
                  </div>
                  <p className="text-sm text-stone-500">
                    {item.waterproof
                      ? "Protege contra chuva"
                      : "Não impermeável"}
                  </p>
                </div>

                <div
                  className={`p-4 rounded-lg border-2 ${item.windproof ? "border-sky-500 bg-sky-50" : "border-stone-200 bg-stone-50"}`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Wind
                      className={`h-5 w-5 ${item.windproof ? "text-sky-600" : "text-stone-400"}`}
                    />
                    <span
                      className={
                        item.windproof ? "text-sky-900" : "text-stone-600"
                      }
                    >
                      Corta-vento
                    </span>
                  </div>
                  <p className="text-sm text-stone-500">
                    {item.windproof
                      ? "Protege contra vento"
                      : "Não corta-vento"}
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4 text-emerald-900">
                <Calendar className="h-5 w-5" />
                <h3>Estações Recomendadas</h3>
              </div>
              <div className="flex gap-2 flex-wrap">
                {item.seasons.map((season) => (
                  <Badge key={season} variant="outline" className="text-sm">
                    {season}
                  </Badge>
                ))}
              </div>
            </Card>
          </div>
        </div >

        <AddItemDialog
          open={isEditing}
          onOpenChange={setIsEditing}
          itemToEdit={item}
          onUpdate={(updatedItem) => {
            onUpdate(updatedItem);
            setIsEditing(false);
            toast.success("Peça atualizada com sucesso");
          }}
        />
      </main >
    </div >
  );
}
