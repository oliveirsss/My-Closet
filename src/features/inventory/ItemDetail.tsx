import { useState } from 'react';
import { ClothingItem } from '../../types';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Card } from '../../components/ui/card';
import { AddItemDialog } from './AddItemDialog';
import {
  ArrowLeft,
  Edit,
  Trash2,
  Heart,
  Droplet,
  Wind,
  Thermometer,
  Weight,
  Layers,
  Tag,
  Calendar,
  Globe,
  User
} from 'lucide-react';
import { toast } from 'sonner';

interface ItemDetailProps {
  item: ClothingItem;
  onBack: () => void;
  onUpdate: (item: ClothingItem) => void;
  onDelete: (id: string) => void;
  isVisitor?: boolean;
  onViewOwner?: (id: string, name: string) => void;
}

export function ItemDetail({ item, onBack, onUpdate, onDelete, isVisitor = false, onViewOwner }: ItemDetailProps) {
  const [isWashing, setIsWashing] = useState(item.status === 'dirty');
  const [isEditing, setIsEditing] = useState(false);

  const toggleWashing = () => {
    const newStatus = isWashing ? 'clean' : 'dirty';
    setIsWashing(!isWashing);
    onUpdate({ ...item, status: newStatus });
    toast.success(`Peça marcada como ${newStatus === 'clean' ? 'Limpa' : 'Suja'}`);
  };

  const toggleFavorite = () => {
    const newFavState = !item.favorite;
    onUpdate({ ...item, favorite: newFavState });
    toast.success(newFavState ? 'Adicionado aos favoritos' : 'Removido dos favoritos');
  };

  const togglePublic = () => {
    const newPublicState = !item.isPublic;
    onUpdate({ ...item, isPublic: newPublicState });

    if (newPublicState) {
      toast.success('Peça tornada PÚBLICA', {
        description: 'Agora visível para todos os visitantes.'
      });
    } else {
      toast.info('Peça tornada PRIVADA', {
        description: 'Agora apenas visível para si.'
      });
    }
  };

  const handleDelete = () => {
    if (confirm('Tem certeza que deseja apagar esta peça?')) {
      onDelete(item.id);
      toast.error('Peça apagada com sucesso');
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

          {/* SÓ MOSTRA OS BOTÕES DE AÇÃO SE NÃO FOR VISITANTE */}
          {!isVisitor && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={toggleFavorite}
                className={item.favorite ? 'text-red-500' : ''}
                title={item.favorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}
              >
                <Heart className={`h-4 w-4 ${item.favorite ? 'fill-red-500' : ''}`} />
              </Button>

              <Button
                variant="outline"
                onClick={togglePublic}
                className={item.isPublic ? 'text-blue-600 border-blue-200 bg-blue-50' : 'text-stone-400'}
                title={item.isPublic ? "Tornar Privado" : "Tornar Público"}
              >
                <Globe className="h-4 w-4" />
              </Button>

              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Edit className="h-4 w-4" />
              </Button>

              <Button variant="outline" onClick={handleDelete} className="text-red-600 hover:text-red-700">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Lado Esquerdo - Imagem */}
          <div>
            <div className="sticky top-6">
              <img
                src={item.image}
                alt={item.name}
                className="w-full h-[600px] object-contain bg-white rounded-lg shadow-xl border border-stone-100"
              />

              {/* MODO VISITANTE: Mostra o Dono / MODO CLIENTE: Mostra botão Lavar */}
              {isVisitor ? (
                <div
                  className="mt-4 p-4 bg-white rounded-lg shadow-sm border border-stone-100 flex items-center gap-3 cursor-pointer hover:bg-stone-50 transition-colors group"
                  onClick={() => {
                    if (item.ownerId && onViewOwner) {
                      onViewOwner(item.ownerId, item.ownerName || 'Utilizador');
                    }
                  }}
                >
                  <div className="w-10 h-10 rounded-full bg-stone-100 overflow-hidden flex items-center justify-center border border-stone-200 group-hover:border-emerald-200">
                    {item.ownerAvatar ? (
                      <img src={item.ownerAvatar} alt={item.ownerName} className="w-full h-full object-cover" />
                    ) : (
                      <User className="h-5 w-5 text-stone-400 group-hover:text-emerald-600" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-stone-500">Publicado por</p>
                    <p className="font-medium text-stone-800 group-hover:text-emerald-700 underline decoration-transparent group-hover:decoration-emerald-700 transition-all">
                      {item.ownerName || 'Utilizador Anónimo'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2 mt-4">
                  <Button
                    variant={isWashing ? 'default' : 'outline'}
                    className={`flex-1 ${isWashing ? 'bg-amber-600 hover:bg-amber-700' : ''}`}
                    onClick={toggleWashing}
                  >
                    {isWashing ? 'Está a lavar' : 'Marcar como sujo'}
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Lado Direito - Detalhes */}
          <div className="space-y-6">
            <div>
              <h1 className="text-4xl mb-2 text-emerald-900">{item.name}</h1>
              <p className="text-xl text-stone-600">{item.brand} • Tamanho {item.size}</p>
            </div>

            {/* SÓ MOSTRA CRACHÁS SE NÃO FOR VISITANTE */}
            {!isVisitor && (
              <div className="flex gap-2">
                <Badge className={`${item.status === 'clean' ? 'bg-emerald-600' : 'bg-amber-600'}`}>
                  {item.status === 'clean' ? 'Limpo' : 'Para Lavar'}
                </Badge>
                {item.favorite && (
                  <Badge variant="outline" className="text-red-600 border-red-600">
                    ❤ Favorito
                  </Badge>
                )}
                {item.isPublic ? (
                  <Badge variant="outline" className="text-blue-600 border-blue-600 bg-blue-50">
                    🌐 Público
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-stone-500 border-stone-300 bg-stone-50">
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
                    <p className="text-xl text-emerald-900">Camada {item.layer}</p>
                    <Badge variant="outline">
                      {item.layer === 1 ? 'Base' : item.layer === 2 ? 'Isolamento' : 'Proteção'}
                    </Badge>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-3 text-emerald-900">Materiais</h3>
              <div className="flex gap-2 flex-wrap">
                {item.materials.map(material => (
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
                  <span className="text-emerald-900">{item.tempMin}°C - {item.tempMax}°C</span>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-4 text-emerald-900">Resistência</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className={`p-4 rounded-lg border-2 ${item.waterproof ? 'border-blue-500 bg-blue-50' : 'border-stone-200 bg-stone-50'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Droplet className={`h-5 w-5 ${item.waterproof ? 'text-blue-600' : 'text-stone-400'}`} />
                    <span className={item.waterproof ? 'text-blue-900' : 'text-stone-600'}>
                      Impermeável
                    </span>
                  </div>
                  <p className="text-sm text-stone-500">
                    {item.waterproof ? 'Protege contra chuva' : 'Não impermeável'}
                  </p>
                </div>

                <div className={`p-4 rounded-lg border-2 ${item.windproof ? 'border-sky-500 bg-sky-50' : 'border-stone-200 bg-stone-50'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Wind className={`h-5 w-5 ${item.windproof ? 'text-sky-600' : 'text-stone-400'}`} />
                    <span className={item.windproof ? 'text-sky-900' : 'text-stone-600'}>
                      Corta-vento
                    </span>
                  </div>
                  <p className="text-sm text-stone-500">
                    {item.windproof ? 'Protege contra vento' : 'Não corta-vento'}
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
                {item.seasons.map(season => (
                  <Badge key={season} variant="outline" className="text-sm">
                    {season}
                  </Badge>
                ))}
              </div>
            </Card>
          </div>
        </div>

        <AddItemDialog
          open={isEditing}
          onOpenChange={setIsEditing}
          itemToEdit={item}
          onUpdate={(updatedItem) => {
            onUpdate(updatedItem);
            setIsEditing(false);
            toast.success('Peça atualizada com sucesso');
          }}
        />
      </main>
    </div>
  );
}