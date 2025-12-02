import { useState } from 'react';
import { ClothingItem } from '../../types';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Card } from '../../components/ui/card';
import { AddItemDialog } from './AddItemDialog'; // Importar o Dialog
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
  Calendar
} from 'lucide-react';

interface ItemDetailProps {
  item: ClothingItem;
  onBack: () => void;
  onUpdate: (item: ClothingItem) => void;
  onDelete: (id: string) => void;
}

export function ItemDetail({ item, onBack, onUpdate, onDelete }: ItemDetailProps) {
  const [isWashing, setIsWashing] = useState(item.status === 'dirty');
  const [isEditing, setIsEditing] = useState(false); // Estado para controlar o Dialog

  const toggleWashing = () => {
    const newStatus = isWashing ? 'clean' : 'dirty';
    setIsWashing(!isWashing);
    onUpdate({ ...item, status: newStatus });
  };

  const toggleFavorite = () => {
    onUpdate({ ...item, favorite: !item.favorite });
  };

  const handleDelete = () => {
    if (confirm('Tem certeza que deseja apagar esta peça?')) {
      onDelete(item.id);
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

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={toggleFavorite}
              className={item.favorite ? 'text-red-500' : ''}
            >
              <Heart className={`h-4 w-4 ${item.favorite ? 'fill-red-500' : ''}`} />
            </Button>

            {/* BOTÃO DE EDITAR AGORA ABRE O DIALOG */}
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              <Edit className="h-4 w-4" />
            </Button>

            <Button variant="outline" onClick={handleDelete} className="text-red-600 hover:text-red-700">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Image Section */}
          <div>
            <div className="sticky top-6">
              <img
                src={item.image}
                alt={item.name}
                className="w-full h-[600px] object-contain bg-white rounded-lg shadow-xl border border-stone-100"
              />
              <div className="flex gap-2 mt-4">
                <Button
                  variant={isWashing ? 'default' : 'outline'}
                  className={`flex-1 ${isWashing ? 'bg-amber-600 hover:bg-amber-700' : ''}`}
                  onClick={toggleWashing}
                >
                  {isWashing ? 'Está a lavar' : 'Marcar como sujo'}
                </Button>
              </div>
            </div>
          </div>

          {/* Details Section */}
          <div className="space-y-6">
            <div>
              <h1 className="text-4xl mb-2 text-emerald-900">{item.name}</h1>
              <p className="text-xl text-stone-600">{item.brand} • Tamanho {item.size}</p>
            </div>

            <div className="flex gap-2">
              <Badge className={`${item.status === 'clean' ? 'bg-emerald-600' : 'bg-amber-600'}`}>
                {item.status === 'clean' ? 'Limpo' : 'Para Lavar'}
              </Badge>
              {item.favorite && (
                <Badge variant="outline" className="text-red-600 border-red-600">
                  ❤ Favorito
                </Badge>
              )}
            </div>

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

        {/* DIALOG DE EDIÇÃO (ESCONDIDO ATÉ CLICARES NO LÁPIS) */}
        <AddItemDialog
          open={isEditing}
          onOpenChange={setIsEditing}
          itemToEdit={item}
          onUpdate={(updatedItem) => {
            onUpdate(updatedItem);
            setIsEditing(false);
          }}
        />
      </main>
    </div>
  );
}