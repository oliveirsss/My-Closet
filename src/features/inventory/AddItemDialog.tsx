import { useState, useEffect } from 'react';
import { ClothingItem } from '../../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Slider } from '../../components/ui/slider';
import {
  Upload,
  ChevronRight,
  ChevronLeft,
  Shirt,
  Layers,
  Thermometer,
  Loader2
} from 'lucide-react';
import * as api from '../../services/api';

interface AddItemDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (item: ClothingItem) => void;
  onUpdate?: (item: ClothingItem) => void;
  itemToEdit?: ClothingItem | null;
}

export function AddItemDialog({ open, onOpenChange, onAdd, onUpdate, itemToEdit }: AddItemDialogProps) {
  const [step, setStep] = useState(1);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string>('');
  const [uploading, setUploading] = useState(false);

  // Form States
  const [name, setName] = useState('');
  const [brand, setBrand] = useState('');
  const [size, setSize] = useState('');
  const [type, setType] = useState('');
  const [layer, setLayer] = useState<1 | 2 | 3>(1);
  const [materials, setMaterials] = useState<string[]>([]);
  const [materialInput, setMaterialInput] = useState('');
  const [weight, setWeight] = useState('');
  const [tempRange, setTempRange] = useState([5, 15]);
  const [waterproof, setWaterproof] = useState(false);
  const [windproof, setWindproof] = useState(false);
  const [seasons, setSeasons] = useState<string[]>([]);

  const clothingTypes = ['Casaco', 'Camisola', 'T-shirt', 'Camisa', 'Calças', 'Calções', 'Vestido', 'Calçado'];
  const allSeasons = ['Inverno', 'Outono', 'Primavera', 'Verão'];

  useEffect(() => {
    if (open) {
      if (itemToEdit) {
        setName(itemToEdit.name);
        setBrand(itemToEdit.brand);
        setSize(itemToEdit.size);
        setType(itemToEdit.type);
        setLayer(itemToEdit.layer);
        setMaterials(itemToEdit.materials);
        setWeight(itemToEdit.weight.toString());
        setTempRange([itemToEdit.tempMin, itemToEdit.tempMax]);
        setWaterproof(itemToEdit.waterproof);
        setWindproof(itemToEdit.windproof);
        setSeasons(itemToEdit.seasons);
        setImagePreview(itemToEdit.image);
        setUploadedImageUrl(itemToEdit.image);
      } else {
        resetForm();
      }
      setStep(1);
    }
  }, [open, itemToEdit]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64 = reader.result as string;
        setImagePreview(base64);

        if (api.getAccessToken()) {
          setUploading(true);
          try {
            const { url } = await api.uploadImage(base64, file.name);
            setUploadedImageUrl(url);
          } catch (error) {
            console.error('Image upload error:', error);
            alert('Erro ao fazer upload da imagem');
            setImagePreview('');
            setUploadedImageUrl('');
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
    const finalImage = uploadedImageUrl || imagePreview;

    const finalItem: ClothingItem = {
      id: itemToEdit ? itemToEdit.id : Date.now().toString(),
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
      image: finalImage,
      status: itemToEdit ? itemToEdit.status : 'clean',
      favorite: itemToEdit ? itemToEdit.favorite : false
    };

    if (itemToEdit && onUpdate) {
      onUpdate(finalItem);
    } else if (onAdd) {
      onAdd(finalItem);
    }

    onOpenChange(false);
  };

  const resetForm = () => {
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
    setUploading(false);
  };

  const canProceedStep1 = name && brand && size && uploadedImageUrl && !uploading;
  const canProceedStep2 = type && materials.length > 0 && weight;
  const canSubmit = seasons.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] p-0 flex flex-col">
        {/* HEADER FIXO */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-stone-200 shrink-0">
          <DialogTitle className="text-2xl text-emerald-900">
            {itemToEdit ? 'Editar Peça' : 'Adicionar Nova Peça'}
          </DialogTitle>
        </DialogHeader>

        {/* STEPPER FIXO */}
        <div className="flex items-center justify-center gap-2 px-6 pt-4 shrink-0">
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

        {/* CONTEÚDO COM SCROLL */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-emerald-900 font-semibold">Step 1: Identificação Visual</h3>
              <div>
                <Label>Foto da Peça</Label>
                <div className="mt-2">
                  {imagePreview ? (
                    <div className="relative group">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className={`w-full h-48 object-cover bg-stone-50 rounded-lg border transition-opacity ${uploading ? 'opacity-50' : ''}`}
                      />

                      {uploading && (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="bg-black/70 text-white px-4 py-2 rounded-full flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm font-medium">A enviar...</span>
                          </div>
                        </div>
                      )}

                      {!uploading && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="absolute top-2 right-2 bg-white/90 hover:bg-white"
                          onClick={() => { setImagePreview(''); setUploadedImageUrl(''); }}
                        >
                          Alterar
                        </Button>
                      )}
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-stone-300 rounded-lg cursor-pointer hover:border-emerald-700 hover:bg-emerald-50/50 transition-colors">
                      <Upload className="h-12 w-12 text-stone-400 mb-2" />
                      <span className="text-stone-600 font-medium">Carregar imagem</span>
                      <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
                    </label>
                  )}
                </div>
              </div>
              <div><Label>Nome *</Label><Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><Label>Marca *</Label><Input value={brand} onChange={(e) => setBrand(e.target.value)} className="mt-1" /></div>
                <div><Label>Tamanho *</Label><Input value={size} onChange={(e) => setSize(e.target.value)} className="mt-1" /></div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-emerald-900 font-semibold">Step 2: Classificação</h3>
              <div>
                <Label>Tipo *</Label>
                <div className="grid grid-cols-4 gap-2 mt-2">
                  {clothingTypes.map(t => (
                    <Button key={t} variant={type === t ? 'default' : 'outline'} onClick={() => setType(t)} className={type === t ? 'bg-emerald-700' : ''}>{t}</Button>
                  ))}
                </div>
              </div>
              <div>
                <Label>Camada *</Label>
                <div className="grid grid-cols-3 gap-2 mt-2">
                  {[1, 2, 3].map(l => (
                    <Button key={l} variant={layer === l ? 'default' : 'outline'} onClick={() => setLayer(l as 1|2|3)} className={layer === l ? 'bg-emerald-700' : ''}>Camada {l}</Button>
                  ))}
                </div>
              </div>
              <div>
                <Label>Materiais *</Label>
                <div className="flex gap-2 mt-2">
                  <Input value={materialInput} onChange={(e) => setMaterialInput(e.target.value)} placeholder="Ex: Algodão" onKeyDown={(e) => e.key === 'Enter' && addMaterial()} />
                  <Button onClick={addMaterial} type="button">Adicionar</Button>
                </div>
                <div className="flex gap-2 flex-wrap mt-2">{materials.map(m => <Badge key={m} variant="secondary" onClick={() => removeMaterial(m)} className="cursor-pointer">{m} ×</Badge>)}</div>
              </div>
              <div><Label>Peso (g) *</Label><Input type="number" value={weight} onChange={(e) => setWeight(e.target.value)} className="mt-1" /></div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-emerald-900 font-semibold">Step 3: Condições</h3>
              <div><Label>Temperatura: {tempRange[0]}°C - {tempRange[1]}°C</Label><Slider min={-20} max={40} step={1} value={tempRange} onValueChange={setTempRange} className="mt-4" /></div>
              <div className="flex gap-4 mt-2">
                <label className="flex gap-2 cursor-pointer"><input type="checkbox" checked={waterproof} onChange={(e) => setWaterproof(e.target.checked)} className="w-4 h-4" /> Impermeável</label>
                <label className="flex gap-2 cursor-pointer"><input type="checkbox" checked={windproof} onChange={(e) => setWindproof(e.target.checked)} className="w-4 h-4" /> Corta-vento</label>
              </div>
              <div>
                <Label>Estações *</Label>
                <div className="grid grid-cols-2 gap-2 mt-2">{allSeasons.map(s => <Button key={s} variant={seasons.includes(s) ? 'default' : 'outline'} onClick={() => toggleSeason(s)} className={seasons.includes(s) ? 'bg-emerald-700' : ''}>{s}</Button>)}</div>
              </div>
            </div>
          )}
        </div>

        {/* FOOTER FIXO */}
        <div className="flex justify-between px-6 py-4 border-t border-stone-200 shrink-0">
          <Button variant="outline" onClick={() => step > 1 ? setStep(step - 1) : onOpenChange(false)}>
            <ChevronLeft className="mr-2 h-4 w-4" /> {step > 1 ? 'Anterior' : 'Cancelar'}
          </Button>

          {step < 3 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={(step === 1 ? !canProceedStep1 : !canProceedStep2) || uploading}
              className="bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50"
            >
              {uploading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> A carregar foto...</>
              ) : (
                <>Próximo <ChevronRight className="ml-2 h-4 w-4" /></>
              )}
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={!canSubmit || uploading} className="bg-emerald-700 hover:bg-emerald-800">
              {itemToEdit ? 'Guardar Alterações' : 'Adicionar Peça'}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}