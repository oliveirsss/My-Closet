import { useState, useEffect } from 'react';
// Tipos sobem 2 níveis
import { ClothingItem } from '../../types';
// UI sobe 2 níveis e entra em components/ui
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import * as tf from '@tensorflow/tfjs';
import * as mobilenet from '@tensorflow-models/mobilenet';
import {
  ArrowLeft,
  Camera,
  Upload,
  Search,
  Check,
  AlertTriangle
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "../../components/ui/alert";

interface ImageSearchProps {
  items: ClothingItem[];
  onBack: () => void;
  onViewItem: (item: ClothingItem) => void;
}

export function ImageSearch({ items, onBack, onViewItem }: ImageSearchProps) {
  const [uploadedImage, setUploadedImage] = useState<string>('');
  const [searchResults, setSearchResults] = useState<ClothingItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [model, setModel] = useState<mobilenet.MobileNet | null>(null);
  const [predictions, setPredictions] = useState<Array<{ className: string; probability: number }>>([]);
  const [detectedCategory, setDetectedCategory] = useState<string>("");
  const [isModelLoading, setIsModelLoading] = useState(true);

  // Carregar o modelo MobileNet ao iniciar
  useEffect(() => {
    async function loadModel() {
      try {
        await tf.ready();
        const loadedModel = await mobilenet.load();
        setModel(loadedModel);
        setIsModelLoading(false);
      } catch (error) {
        console.error("Erro ao carregar modelo:", error);
        setIsModelLoading(false);
      }
    }
    loadModel();
  }, []);

  const mapPredictionToCategory = (preds: Array<{ className: string; probability: number }>) => {
    // Mapeamento simples de classes do ImageNet para as nossas categorias
    const categoryMap: Record<string, string> = {
      'jersey': 'T-shirt',
      't-shirt': 'T-shirt',
      'sweatshirt': 'Camisola',
      'cardigan': 'Camisola',
      'shirt': 'Camisa',
      'jean': 'Calças',
      'pants': 'Calças',
      'trousers': 'Calças',
      'short': 'Calções',
      'shorts': 'Calções',
      'trunks': 'Calções',
      'swim': 'Calções',
      'suit': 'Casaco',
      'coat': 'Casaco',
      'jacket': 'Casaco',
      'trench coat': 'Casaco',
      'clog': 'Calçado',
      'sandal': 'Calçado',
      'shoe': 'Calçado',
      'sneaker': 'Calçado',
      'boot': 'Calçado',
      'sock': 'Acessório',
      'hat': 'Acessório',
      'cap': 'Acessório',
      'sunglasses': 'Acessório',
      'scarf': 'Acessório',
      'tie': 'Acessório'
    };

    for (const pred of preds) {
      const className = pred.className.toLowerCase();
      // Procura palavras-chave
      for (const [key, value] of Object.entries(categoryMap)) {
        if (className.includes(key)) {
          return value;
        }
      }
    }
    return "Outros"; // Fallback
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedImage(reader.result as string);
        // Pequeno delay para garantir que a imagem renderizou antes de classificar
        setTimeout(() => classifyImage(reader.result as string), 100);
      };
      reader.readAsDataURL(file);
    }
  };

  const classifyImage = async (imageSrc: string) => {
    if (!model) return;
    setIsSearching(true);

    try {
      // Criar elemento de imagem temporário
      const img = document.createElement('img');
      img.src = imageSrc;
      img.width = 224;
      img.height = 224;

      // Classificar
      const preds = await model.classify(img);
      setPredictions(preds);

      const mappedCategory = mapPredictionToCategory(preds);
      setDetectedCategory(mappedCategory);

      performSearch(mappedCategory);
    } catch (error) {
      console.error("Erro na classificação:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const performSearch = (category: string) => {
    // Definir grupos de categorias relacionadas
    const categoryGroups: Record<string, string[]> = {
      'Calças': ['Calças', 'Calções'],
      'Calções': ['Calças', 'Calções'],
    };

    const targetCategories = categoryGroups[category] || [category];

    // Filtrar items por qualquer uma das categorias alvo
    const results = items.filter(item =>
      targetCategories.some(target =>
        item.type.toLowerCase().includes(target.toLowerCase()) ||
        target.toLowerCase().includes(item.type.toLowerCase())
      )
    );
    setSearchResults(results);
  };

  const handleCategoryChange = (newCategory: string) => {
    setDetectedCategory(newCategory);
    performSearch(newCategory);
  };

  const resetSearch = () => {
    setUploadedImage('');
    setSearchResults([]);
    setPredictions([]);
    setDetectedCategory("");
  };

  // Obter lista única de categorias do inventário para o dropdown
  const availableCategories = Array.from(new Set(items.map(i => i.type))).sort();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-stone-100">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={onBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar
            </Button>
            <div>
              <h1 className="text-2xl text-emerald-900">Pesquisa por Imagem</h1>
              <p className="text-sm text-stone-600">Verifique se uma peça já existe no seu armário</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {/* Upload Section */}
        {!uploadedImage ? (
          <div className="max-w-2xl mx-auto">
            <Card className="p-12">
              <div className="text-center mb-8">
                <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Camera className="h-10 w-10 text-emerald-700" />
                </div>
                <h2 className="text-2xl mb-2 text-emerald-900">Carregar Imagem</h2>
                <p className="text-stone-600">
                  Faça upload de uma foto para encontrar peças semelhantes no seu inventário
                </p>
              </div>

              <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-stone-300 rounded-lg cursor-pointer hover:border-emerald-700 transition-colors bg-stone-50 hover:bg-stone-100">
                <Upload className="h-12 w-12 text-stone-400 mb-2" />
                <span className="text-stone-600">Clique para carregar imagem</span>
                <span className="text-sm text-stone-400 mt-1">ou arrastar ficheiro</span>
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  onChange={handleImageUpload}
                />
              </label>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="mb-2 text-blue-900">Como funciona?</h3>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>1. Carregue uma foto da peça de roupa</li>
                  <li>2. O sistema analisa as características visuais</li>
                  <li>3. Mostra peças semelhantes no seu armário</li>
                  <li>4. Evite comprar peças duplicadas!</li>
                </ul>
              </div>
            </Card>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Uploaded Image & Classification */}
            <Card className="p-6">
              <div className="flex flex-col md:flex-row items-start gap-6">
                <div className="flex-shrink-0 relative group">
                  <img
                    src={uploadedImage}
                    alt="Uploaded"
                    className="w-full md:w-64 h-64 object-cover rounded-lg shadow-md"
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg">
                    <Button variant="secondary" size="sm" onClick={resetSearch}>
                      <Camera className="mr-2 h-4 w-4" />
                      Nova Foto
                    </Button>
                  </div>
                </div>

                <div className="flex-1 w-full space-y-4">
                  <div>
                    <h2 className="text-xl font-semibold text-emerald-900 mb-1">Análise da Imagem 🤖</h2>
                    <p className="text-stone-600 text-sm">
                      A nossa IA analisou a tua foto. Confirma se a categoria está correta.
                    </p>
                  </div>

                  {predictions.length > 0 && (
                    <div className="bg-stone-50 p-3 rounded-md text-xs text-stone-500 font-mono">
                      Detetado: {predictions[0].className} ({Math.round(predictions[0].probability * 100)}%)
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-stone-700">Categoria Identificada:</label>
                    <div className="flex gap-2">
                      <Select
                        value={detectedCategory}
                        onValueChange={handleCategoryChange}
                      >
                        <SelectTrigger className="w-full md:w-[280px] bg-white border-emerald-200">
                          <SelectValue placeholder="Selecione a categoria" />
                        </SelectTrigger>
                        <SelectContent className="bg-white z-[100] border-emerald-100 shadow-xl">
                          {availableCategories.map(cat => (
                            <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Alerta se não houver resultados */}
                  {!isSearching && searchResults.length === 0 && detectedCategory && (
                    <Alert variant="destructive" className="bg-red-50 border-red-200 text-red-900 mt-4">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertTitle>Nada encontrado!</AlertTitle>
                      <AlertDescription>
                        Não encontrámos nenhuma peça do tipo <strong>{detectedCategory}</strong> no teu inventário.
                        <br />
                        <span className="text-sm mt-1 block">Isto é uma boa notícia! Significa que provavelmente não tens nada igual.</span>
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </div>
            </Card>

            {/* Loading State */}
            {isSearching && (
              <Card className="p-12 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-emerald-700 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-stone-600">A analisar imagem...</p>
              </Card>
            )}

            {/* Search Results */}
            {!isSearching && searchResults.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl text-emerald-900 font-semibold flex items-center gap-2">
                      <Check className="h-5 w-5 text-emerald-600" />
                      Peças Semelhantes ({searchResults.length})
                    </h2>
                    <p className="text-sm text-stone-500">
                      Encontrámos estas peças do tipo <strong>{detectedCategory}</strong> no teu armário.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {searchResults.map(result => (
                    <Card
                      key={result.id}
                      className="overflow-hidden cursor-pointer hover:shadow-xl transition-all border-emerald-100 ring-1 ring-emerald-50"
                      onClick={() => onViewItem(result)}
                    >
                      <div className="relative">
                        <img
                          src={result.image}
                          alt={result.name}
                          className="w-full h-48 object-cover"
                        />
                        {result.favorite && (
                          <div className="absolute top-2 right-2 bg-white/90 p-1 rounded-full shadow-sm">
                            <Check className="h-3 w-3 text-red-500" />
                          </div>
                        )}
                      </div>

                      <div className="p-4">
                        <p className="mb-1 text-emerald-900 font-medium truncate">{result.name}</p>
                        <Badge variant="secondary" className="mb-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100">
                          {result.type}
                        </Badge>

                        <div className="bg-stone-50 rounded p-2 text-xs text-stone-600 space-y-1">
                          <div className="flex justify-between">
                            <span>Camada: {result.layer}</span>
                            <span>{result.tempMin}°-{result.tempMax}°</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                {searchResults.length === 0 && (
                  <Card className="p-12 text-center">
                    <p className="text-stone-600 mb-4">
                      Nenhuma peça semelhante encontrada no seu inventário.
                    </p>
                    <p className="text-sm text-stone-500">
                      Esta parece ser uma peça nova!
                    </p>
                  </Card>
                )}
              </div>
            )}
          </div>
        )}

        {/* Info Section */}
        <Card className="mt-8 p-6 bg-gradient-to-br from-emerald-50 to-stone-50 border-emerald-200">
          <h3 className="mb-3 text-emerald-900">Dica de Utilização</h3>
          <p className="text-sm text-stone-700">
            Use esta funcionalidade antes de comprar roupa nova! Tire uma foto na loja e
            verifique se já tem peças semelhantes no seu armário. Ajuda a evitar compras
            duplicadas e a gerir melhor o seu guarda-roupa.
          </p>
        </Card>
      </main>
    </div>
  );
}
