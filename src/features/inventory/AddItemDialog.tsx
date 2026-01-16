import React, { useState, useEffect } from 'react';
import { ClothingItem } from '../../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Slider } from '../../components/ui/slider';
import {
  Upload, ChevronRight, ChevronLeft, Shirt, Layers, Thermometer, Loader2, RotateCcw
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

  // Reset e Carregamento
  useEffect(() => {
    if (open) {
      if (itemToEdit) {
        setName(itemToEdit.name); setBrand(itemToEdit.brand); setSize(itemToEdit.size);
        setType(itemToEdit.type); setLayer(itemToEdit.layer); setMaterials(itemToEdit.materials);
        setWeight(itemToEdit.weight.toString()); setTempRange([itemToEdit.tempMin, itemToEdit.tempMax]);
        setWaterproof(itemToEdit.waterproof); setWindproof(itemToEdit.windproof); setSeasons(itemToEdit.seasons);
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
      reader.onloadend = () => setImagePreview(reader.result as string);
      reader.readAsDataURL(file);

      if (api.getAccessToken()) {
        setUploading(true);
        try {
          const { url } = await api.uploadImage(file, file.name);
          setUploadedImageUrl(url);
        } catch (error) {
          console.error("Upload error:", error);
          alert("Erro ao enviar imagem");
          setImagePreview('');
        } finally {
          setUploading(false);
        }
      }
    }
  };

  const resetForm = () => {
    setImagePreview(''); setUploadedImageUrl(''); setName(''); setBrand(''); setSize('');
    setType(''); setLayer(1); setMaterials([]); setMaterialInput(''); setWeight('');
    setTempRange([5, 15]); setWaterproof(false); setWindproof(false); setSeasons([]);
    setUploading(false);
  };

  const handleSubmit = () => {
    const finalItem: ClothingItem = {
      id: itemToEdit ? itemToEdit.id : Date.now().toString(),
      name, brand, size, type, layer, materials,
      weight: parseFloat(weight) || 0,
      tempMin: tempRange[0], tempMax: tempRange[1],
      waterproof, windproof, seasons,
      image: uploadedImageUrl || imagePreview,
      status: itemToEdit ? itemToEdit.status : 'clean',
      favorite: itemToEdit ? itemToEdit.favorite : false,
      isPublic: itemToEdit ? itemToEdit.isPublic : false
    };
    if (itemToEdit && onUpdate) onUpdate(finalItem);
    else if (onAdd) onAdd(finalItem);
    onOpenChange(false);
  };

  const addMaterial = () => { if (materialInput && !materials.includes(materialInput)) { setMaterials([...materials, materialInput]); setMaterialInput(''); } };
  const removeMaterial = (m: string) => setMaterials(materials.filter(x => x !== m));
  const toggleSeason = (s: string) => setSeasons(seasons.includes(s) ? seasons.filter(x => x !== s) : [...seasons, s]);

  const canProceedStep1 = name && brand && size && (uploadedImageUrl || (itemToEdit && imagePreview)) && !uploading;
  const canProceedStep2 = type && materials.length > 0 && weight;
  const canSubmit = seasons.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* MODIFICAÇÃO IMPORTANTE DE LAYOUT:
          h-[85vh]: Altura fixa de 85% do ecrã.
          flex-col: Para organizar Header, Body e Footer verticalmente.
          p-0 gap-0: Remove paddings padrão para controlarmos nós.
      */}
      <DialogContent className="max-w-3xl w-full max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">

        {/* --- 1. CABEÇALHO FIXO --- */}
        <DialogHeader className="px-6 py-4 border-b border-stone-100 bg-white shrink-0">
          <DialogTitle className="text-2xl text-emerald-900">{itemToEdit ? 'Editar Peça' : 'Adicionar Nova Peça'}</DialogTitle>
        </DialogHeader>

        {/* --- 2. ÁREA DE SCROLL (Onde está o formulário) --- */}
        <div className="flex-1 overflow-y-auto p-6 bg-white">

          {/* Stepper */}
          <div className="flex items-center justify-center gap-2 mb-8">
            <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 1 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}><Shirt className="h-5 w-5" /></div>
            <div className={`h-1 w-16 ${step >= 2 ? 'bg-emerald-700' : 'bg-stone-200'}`} />
            <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 2 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}><Layers className="h-5 w-5" /></div>
            <div className={`h-1 w-16 ${step >= 3 ? 'bg-emerald-700' : 'bg-stone-200'}`} />
            <div className={`flex items-center justify-center w-10 h-10 rounded-full ${step >= 3 ? 'bg-emerald-700 text-white' : 'bg-stone-200'}`}><Thermometer className="h-5 w-5" /></div>
          </div>

          {step === 1 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Lado Esquerdo: Imagem */}
              <div className="space-y-2">
                <Label>Foto da Peça</Label>
                <div className="mt-2 w-full bg-stone-50 rounded-lg border-2 border-dashed border-stone-300 overflow-hidden relative flex items-center justify-center h-[350px]">
                  {imagePreview ? (
                    <div className="relative group w-full h-full flex items-center justify-center bg-stone-100">
                      <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                      {uploading && (
                        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-20">
                          <div className="bg-white px-4 py-2 rounded-full flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> A enviar...</div>
                        </div>
                      )}
                      {!uploading && (
                        <div className="absolute top-2 right-2">
                          <label className="cursor-pointer bg-white/90 hover:bg-white shadow-sm text-stone-900 text-xs font-medium px-3 py-1.5 rounded-md flex items-center border border-stone-200">
                            <RotateCcw className="h-3 w-3 mr-1" /> Trocar
                            <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
                          </label>
                        </div>
                      )}
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer hover:bg-stone-100 transition-colors">
                      <div className="bg-white p-3 rounded-full mb-3 shadow-sm border border-stone-200">
                        <Upload className="h-6 w-6 text-emerald-600" />
                      </div>
                      <span className="text-stone-900 font-medium">Carregar imagem</span>
                      <span className="text-xs text-stone-500 mt-1">JPG ou PNG</span>
                      <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
                    </label>
                  )}
                </div>
                <p className="text-[10px] text-stone-400 text-center">* Ajuste automático ao centro.</p>
              </div>

              {/* Lado Direito: Inputs */}
              <div className="space-y-6">
                <div><Label>Nome *</Label><Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1" /></div>
                <div><Label>Marca *</Label><Input value={brand} onChange={(e) => setBrand(e.target.value)} className="mt-1" /></div>
                <div><Label>Tamanho *</Label><Input value={size} onChange={(e) => setSize(e.target.value)} className="mt-1" /></div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <h3 className="text-emerald-900 font-medium text-lg">Step 2: Classificação</h3>
              <div><Label>Tipo *</Label><div className="grid grid-cols-4 gap-2 mt-2">{clothingTypes.map(t => <Button key={t} variant={type === t ? 'default' : 'outline'} onClick={() => setType(t)} className={type === t ? 'bg-emerald-700' : ''}>{t}</Button>)}</div></div>
              <div><Label>Camada *</Label><div className="grid grid-cols-3 gap-2 mt-2">{[1, 2, 3].map(l => <Button key={l} variant={layer === l ? 'default' : 'outline'} onClick={() => setLayer(l as 1 | 2 | 3)} className={layer === l ? 'bg-emerald-700' : ''}>Camada {l}</Button>)}</div></div>
              <div><Label>Materiais *</Label><div className="flex gap-2 mt-2"><Input value={materialInput} onChange={(e) => setMaterialInput(e.target.value)} placeholder="Ex: Algodão" onKeyDown={(e) => e.key === 'Enter' && addMaterial()} /><Button onClick={addMaterial} type="button">Adicionar</Button></div><div className="flex gap-2 flex-wrap mt-2">{materials.map(m => <Badge key={m} variant="secondary" onClick={() => removeMaterial(m)} className="cursor-pointer">{m} ×</Badge>)}</div></div>
              <div><Label>Peso (g) *</Label><Input type="number" value={weight} onChange={(e) => setWeight(e.target.value)} className="mt-1" /></div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <h3 className="text-emerald-900 font-medium">Step 3: Condições</h3>
              <div><Label>Temp: {tempRange[0]}°C - {tempRange[1]}°C</Label><Slider min={-20} max={40} step={1} value={tempRange} onValueChange={setTempRange} className="mt-4" /></div>
              <div className="flex gap-4 mt-2"><label className="flex gap-2"><input type="checkbox" checked={waterproof} onChange={(e) => setWaterproof(e.target.checked)} /> Impermeável</label><label className="flex gap-2"><input type="checkbox" checked={windproof} onChange={(e) => setWindproof(e.target.checked)} /> Corta-vento</label></div>
              <div><Label>Estações *</Label><div className="grid grid-cols-2 gap-2 mt-2">{allSeasons.map(s => <Button key={s} variant={seasons.includes(s) ? 'default' : 'outline'} onClick={() => toggleSeason(s)} className={seasons.includes(s) ? 'bg-emerald-700' : ''}>{s}</Button>)}</div></div>
            </div>
          )}
        </div>

        {/* --- 3. RODAPÉ FIXO --- */}
        <div className="flex justify-between p-4 border-t border-stone-100 bg-stone-50 shrink-0">
          <Button variant="outline" onClick={() => step > 1 ? setStep(step - 1) : onOpenChange(false)}><ChevronLeft className="mr-2 h-4 w-4" /> {step > 1 ? 'Anterior' : 'Cancelar'}</Button>
          {step < 3 ? (
            <Button onClick={() => setStep(step + 1)} disabled={step === 1 ? !canProceedStep1 : !canProceedStep2} className="bg-emerald-700 hover:bg-emerald-800 text-white">Próximo <ChevronRight className="ml-2 h-4 w-4" /></Button>
          ) : (
            <Button onClick={handleSubmit} disabled={!canSubmit || uploading} className="bg-emerald-700 hover:bg-emerald-800 text-white">{itemToEdit ? 'Guardar' : 'Adicionar'}</Button>
          )}
        </div>

      </DialogContent>
    </Dialog>
  );
}