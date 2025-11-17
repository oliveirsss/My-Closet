import { useState } from 'react';
import { ClothingItem } from '../App';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Slider } from './ui/slider';
import { 
  Upload, 
  ChevronRight, 
  ChevronLeft,
  Shirt,
  Layers,
  Thermometer
} from 'lucide-react';
import * as api from '../utils/api';

interface AddItemDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (item: ClothingItem) => void;
}

export function AddItemDialog({ open, onOpenChange, onAdd }: AddItemDialogProps) {
  const [step, setStep] = useState(1);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  
  // Step 1: Identificação Visual
  const [name, setName] = useState('');
  const [brand, setBrand] = useState('');
  const [size, setSize] = useState('');
  
  // Step 2: Classificação Têxtil
  const [type, setType] = useState('');
  const [layer, setLayer] = useState<1 | 2 | 3>(1);
  const [materials, setMaterials] = useState<string[]>([]);
  const [materialInput, setMaterialInput] = useState('');
  const [weight, setWeight] = useState('');
  
  // Step 3: Condições de Uso
  const [tempRange, setTempRange] = useState([5, 15]);
  const [waterproof, setWaterproof] = useState(false);
  const [windproof, setWindproof] = useState(false);
  const [seasons, setSeasons] = useState<string[]>([]);

  const clothingTypes = ['Casaco', 'Camisola', 'T-shirt', 'Camisa', 'Calças', 'Calções', 'Vestido'];
  const allSeasons = ['Inverno', 'Outono', 'Primavera', 'Verão'];

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64 = reader.result as string;
        setImagePreview(base64);
        
        // Upload to Supabase Storage
        if (api.getAccessToken()) {
          setUploading(true);
          try {
            const { url } = await api.uploadImage(base64, file.name);
            setUploadedImageUrl(url);
          } catch (error) {
            console.error('Image upload error:', error);
            alert('Erro ao fazer upload da imagem');
          } finally {
            setUploading(false);
          }
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const addMaterial = () => {
    if (materialInput && !materials.includes(materialInput)) {
      setMaterials([...materials, materialInput]);
      setMaterialInput('');
    }
  };

  const removeMaterial = (material: string) => {
    setMaterials(materials.filter(m => m !== material));
  };

  const toggleSeason = (season: string) => {
    if (seasons.includes(season)) {
      setSeasons(seasons.filter(s => s !== season));
    } else {
      setSeasons([...seasons, season]);
    }
  };

  const handleSubmit = () => {
    const newItem: ClothingItem = {
      id: Date.now().toString(),
      name,
      brand,
      size,
      type,
      layer,
      materials,
      weight: parseFloat(weight),
      tempMin: tempRange[0],
      tempMax: tempRange[1],
      waterproof,
      windproof,
      seasons,
      image: uploadedImageUrl || imagePreview || 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400',
      status: 'clean',
      favorite: false
    };
    
    onAdd(newItem);
    resetForm();
    onOpenChange(false);
  };

  const resetForm = () => {
    setStep(1);
    setImagePreview('');
    setUploadedImageUrl('');
    setName('');
    setBrand('');
    setSize('');
    setType('');
    setLayer(1);
    setMaterials([]);
    setMaterialInput('');
    setWeight('');
    setTempRange([5, 15]);
    setWaterproof(false);
    setWindproof(false);
    setSeasons([]);
  };

  const canProceedStep1 = name && brand && size;
  const canProceedStep2 = type && materials.length > 0 && weight;
  const canSubmit = seasons.length > 0;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      onOpenChange(isOpen);
      if (!isOpen) {
        resetForm();
      }
    }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl text-emerald-900">
            Adicionar Nova Peça
          </DialogTitle>
        </DialogHeader>

        {/* Progress Indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 1 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}>
            <Shirt className="h-5 w-5" />
          </div>
          <div className={`h-1 w-16 ${step >= 2 ? 'bg-emerald-700' : 'bg-stone-200'}`} />
          <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 2 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}>
            <Layers className="h-5 w-5" />
          </div>
          <div className={`h-1 w-16 ${step >= 3 ? 'bg-emerald-700' : 'bg-stone-200'}`} />
          <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 3 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}>
            <Thermometer className="h-5 w-5" />
          </div>
        </div>

        {/* Step 1: Identificação Visual */}
        {step === 1 && (
          <div className="space-y-4">
            <h3 className="text-emerald-900">Step 1: Identificação Visual</h3>
            
            <div>
              <Label>Foto da Peça</Label>
              <div className="mt-2">
                {imagePreview ? (
                  <div className="relative">
                    <img src={imagePreview} alt="Preview" className="w-full h-64 object-cover rounded-lg" />
                    <Button
                      variant="outline"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={() => setImagePreview('')}
                    >
                      Alterar
                    </Button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-stone-300 rounded-lg cursor-pointer hover:border-emerald-700 transition-colors">
                    <Upload className="h-12 w-12 text-stone-400 mb-2" />
                    <span className="text-stone-600">Carregar imagem</span>
                    <span className="text-sm text-stone-400">ou arrastar ficheiro</span>
                    <input
                      type="file"
                      className="hidden"
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                  </label>
                )}
              </div>
            </div>

            <div>
              <Label htmlFor="name">Nome da Peça *</Label>
              <Input
                id="name"
                placeholder="Ex: Casaco North Face Azul"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="brand">Marca *</Label>
                <Input
                  id="brand"
                  placeholder="Ex: The North Face"
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="size">Tamanho *</Label>
                <Input
                  id="size"
                  placeholder="Ex: M"
                  value={size}
                  onChange={(e) => setSize(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Classificação Têxtil */}
        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-emerald-900">Step 2: Classificação Têxtil</h3>
            
            <div>
              <Label>Tipo de Roupa *</Label>
              <div className="grid grid-cols-4 gap-2 mt-2">
                {clothingTypes.map(t => (
                  <Button
                    key={t}
                    variant={type === t ? 'default' : 'outline'}
                    onClick={() => setType(t)}
                    className={type === t ? 'bg-emerald-700' : ''}
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <Label>Camada *</Label>
              <div className="grid grid-cols-3 gap-2 mt-2">
                <Button
                  variant={layer === 1 ? 'default' : 'outline'}
                  onClick={() => setLayer(1)}
                  className={layer === 1 ? 'bg-emerald-700' : ''}
                >
                  <div className="text-center">
                    <div>Camada 1</div>
                    <div className="text-xs opacity-70">Base / Pele</div>
                  </div>
                </Button>
                <Button
                  variant={layer === 2 ? 'default' : 'outline'}
                  onClick={() => setLayer(2)}
                  className={layer === 2 ? 'bg-emerald-700' : ''}
                >
                  <div className="text-center">
                    <div>Camada 2</div>
                    <div className="text-xs opacity-70">Isolamento</div>
                  </div>
                </Button>
                <Button
                  variant={layer === 3 ? 'default' : 'outline'}
                  onClick={() => setLayer(3)}
                  className={layer === 3 ? 'bg-emerald-700' : ''}
                >
                  <div className="text-center">
                    <div>Camada 3</div>
                    <div className="text-xs opacity-70">Proteção</div>
                  </div>
                </Button>
              </div>
            </div>

            <div>
              <Label>Materiais *</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  placeholder="Ex: Algodão, Poliéster, Lã"
                  value={materialInput}
                  onChange={(e) => setMaterialInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addMaterial())}
                />
                <Button onClick={addMaterial} type="button">
                  Adicionar
                </Button>
              </div>
              <div className="flex gap-2 flex-wrap mt-2">
                {materials.map(material => (
                  <Badge
                    key={material}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => removeMaterial(material)}
                  >
                    {material} ×
                  </Badge>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="weight">Peso (gramas) *</Label>
              <Input
                id="weight"
                type="number"
                placeholder="Ex: 450"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
        )}

        {/* Step 3: Condições de Uso */}
        {step === 3 && (
          <div className="space-y-4">
            <h3 className="text-emerald-900">Step 3: Condições de Uso</h3>
            
            <div>
              <Label>Range de Temperatura: {tempRange[0]}°C - {tempRange[1]}°C</Label>
              <Slider
                min={-20}
                max={40}
                step={1}
                value={tempRange}
                onValueChange={setTempRange}
                className="mt-4"
              />
            </div>

            <div>
              <Label>Resistência</Label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={waterproof}
                    onChange={(e) => setWaterproof(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Impermeável</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={windproof}
                    onChange={(e) => setWindproof(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span>Corta-vento</span>
                </label>
              </div>
            </div>

            <div>
              <Label>Estações *</Label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {allSeasons.map(season => (
                  <Button
                    key={season}
                    variant={seasons.includes(season) ? 'default' : 'outline'}
                    onClick={() => toggleSeason(season)}
                    className={seasons.includes(season) ? 'bg-emerald-700' : ''}
                  >
                    {season}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-6">
          <Button
            variant="outline"
            onClick={() => step > 1 ? setStep(step - 1) : onOpenChange(false)}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            {step > 1 ? 'Anterior' : 'Cancelar'}
          </Button>

          {step < 3 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={step === 1 ? !canProceedStep1 : !canProceedStep2}
              className="bg-emerald-700 hover:bg-emerald-800"
            >
              Próximo
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="bg-emerald-700 hover:bg-emerald-800"
            >
              Adicionar Peça
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}