import { useState } from 'react';
import { ClothingItem } from '../App';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { 
  ArrowLeft,
  Camera,
  Upload,
  Search
} from 'lucide-react';

interface ImageSearchProps {
  items: ClothingItem[];
  onBack: () => void;
  onViewItem: (item: ClothingItem) => void;
}

export function ImageSearch({ items, onBack, onViewItem }: ImageSearchProps) {
  const [uploadedImage, setUploadedImage] = useState<string>('');
  const [searchResults, setSearchResults] = useState<Array<ClothingItem & { match: number }>>([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setUploadedImage(reader.result as string);
        performSearch();
      };
      reader.readAsDataURL(file);
    }
  };

  const performSearch = () => {
    setIsSearching(true);
    
    // Simular busca por imagem - em produção usaria AI/ML
    // Para demo, vamos retornar resultados aleatórios com percentagens
    setTimeout(() => {
      const results = items
        .map(item => ({
          ...item,
          match: Math.floor(Math.random() * 40) + 60 // 60-100% match
        }))
        .sort((a, b) => b.match - a.match)
        .slice(0, 4);
      
      setSearchResults(results);
      setIsSearching(false);
    }, 1500);
  };

  const resetSearch = () => {
    setUploadedImage('');
    setSearchResults([]);
  };

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
            {/* Uploaded Image */}
            <Card className="p-6">
              <div className="flex items-start gap-6">
                <div className="flex-shrink-0">
                  <img
                    src={uploadedImage}
                    alt="Uploaded"
                    className="w-64 h-64 object-cover rounded-lg"
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-4">
                    <Search className="h-6 w-6 text-emerald-700" />
                    <h2 className="text-2xl text-emerald-900">Imagem Carregada</h2>
                  </div>
                  <p className="text-stone-600 mb-4">
                    A procurar peças semelhantes no seu inventário...
                  </p>
                  <Button variant="outline" onClick={resetSearch}>
                    <Upload className="mr-2 h-4 w-4" />
                    Carregar Outra Imagem
                  </Button>
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
                  <h2 className="text-2xl text-emerald-900">
                    Resultados Encontrados ({searchResults.length})
                  </h2>
                  <p className="text-stone-600">
                    Ordenado por compatibilidade
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {searchResults.map(result => (
                    <Card
                      key={result.id}
                      className="overflow-hidden cursor-pointer hover:shadow-xl transition-all"
                      onClick={() => onViewItem(result)}
                    >
                      <div className="relative">
                        <img
                          src={result.image}
                          alt={result.name}
                          className="w-full h-64 object-cover"
                        />
                        <div className="absolute top-2 right-2">
                          <Badge 
                            className={`${
                              result.match >= 90 
                                ? 'bg-emerald-600' 
                                : result.match >= 75 
                                  ? 'bg-blue-600' 
                                  : 'bg-amber-600'
                            }`}
                          >
                            {result.match}% Match
                          </Badge>
                        </div>
                      </div>
                      
                      <div className="p-4">
                        <p className="mb-1 text-emerald-900">{result.name}</p>
                        <p className="text-sm text-stone-600 mb-2">{result.type}</p>
                        
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-stone-500">Camada {result.layer}</span>
                            <span className="text-stone-500">{result.tempMin}°C - {result.tempMax}°C</span>
                          </div>
                          
                          {result.match >= 90 && (
                            <div className="bg-emerald-50 text-emerald-800 text-xs p-2 rounded">
                              ✓ Muito semelhante! Talvez já tenha esta peça.
                            </div>
                          )}
                          {result.match >= 75 && result.match < 90 && (
                            <div className="bg-blue-50 text-blue-800 text-xs p-2 rounded">
                              Peça semelhante encontrada no seu armário.
                            </div>
                          )}
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
