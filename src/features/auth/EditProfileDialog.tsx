import { useState, useEffect } from 'react';
import { Dialog, DialogContent } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { User, Upload, MapPin, FileText, Sparkles } from 'lucide-react';
import * as api from '../../services/api';

interface EditProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userData: {
    name: string;
    avatar_url?: string;
    bio?: string;
    location?: string;
  };
  onUpdate: (data: any) => void;
}

export function EditProfileDialog({ open, onOpenChange, userData, onUpdate }: EditProfileDialogProps) {
  const [name, setName] = useState('');
  const [bio, setBio] = useState('');
  const [location, setLocation] = useState('');
  const [imagePreview, setImagePreview] = useState<string>('');
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  useEffect(() => {
    if (open) {
      setName(userData.name || '');
      setBio(userData.bio || '');
      setLocation(userData.location || '');
      setImagePreview(userData.avatar_url || '');
      setUploadedImageUrl(userData.avatar_url || '');
    }
  }, [open, userData]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64 = reader.result as string;
      setImagePreview(base64);

      if (!api.getAccessToken()) {
        return;
      }

      setUploadingImage(true);
      try {
        const { url } = await api.uploadImage(base64, `avatar_${Date.now()}_${file.name}`);
        setUploadedImageUrl(url);
      } catch (error) {
        console.error('Erro upload avatar:', error);
        alert('Erro ao carregar imagem.');
      } finally {
        setUploadingImage(false);
      }
    };

    reader.readAsDataURL(file);
  };

  const sanitize = (value: string) => value.trim() || undefined;

  const handleSubmit = async () => {
    if (!name.trim()) {
      alert('O nome é obrigatório.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name: name.trim(),
        avatar_url: uploadedImageUrl || userData.avatar_url || undefined,
        bio: sanitize(bio),
        location: sanitize(location),
      };

      const { profile } = await api.updateProfile(payload);
      onUpdate({
        name: profile.name,
        avatar_url: profile.avatar_url,
        bio: profile.bio,
        location: profile.location,
      });
      onOpenChange(false);
    } catch (error) {
      console.error('Erro:', error);
      alert('Erro ao atualizar perfil.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl p-0 overflow-hidden border-none shadow-2xl">
        <div className="bg-gradient-to-r from-emerald-700 via-emerald-600 to-emerald-500 px-8 py-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-white/70 mb-1">Perfil</p>
              <h2 className="text-3xl font-semibold flex items-center gap-3">
                <Sparkles className="h-6 w-6 text-amber-300" />
                Personaliza a tua identidade
              </h2>
              <p className="text-white/80 mt-2 max-w-2xl">
                Torna o teu closet mais pessoal. Actualiza o nome, adiciona uma biografia curta e partilha a tua localização.
              </p>
            </div>
            <Button variant="secondary" onClick={handleSubmit} disabled={loading || uploadingImage} className="bg-white text-emerald-800 hover:bg-emerald-50 border-0">
              {loading ? 'A guardar...' : 'Guardar Alterações'}
            </Button>
          </div>
        </div>

        <div className="bg-white px-8 py-10">
          <div className="grid gap-8 md:grid-cols-[260px,1fr]">
            <section className="bg-stone-50 rounded-2xl p-6 border border-stone-100 flex flex-col items-center text-center">
              <div className="relative">
                <div className="w-32 h-32 rounded-full overflow-hidden ring-4 ring-white shadow-xl bg-white">
                  {imagePreview ? (
                    <img src={imagePreview} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-stone-100 to-stone-200 text-stone-400">
                      <User className="h-14 w-14" />
                    </div>
                  )}
                </div>

                <label className="absolute -bottom-2 right-2 bg-emerald-600 hover:bg-emerald-700 text-white p-3 rounded-full cursor-pointer shadow-lg transition-all hover:scale-110 active:scale-95 border-2 border-white">
                  {uploadingImage ? (
                    <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} disabled={uploadingImage} />
                </label>
              </div>
              <p className="text-sm text-stone-500 mt-6">Formatos aceites: JPG, PNG. Dimensões recomendadas 512x512.</p>
            </section>

            <section className="space-y-6">
              <div className="grid gap-2">
                <Label htmlFor="name" className="text-sm font-semibold uppercase tracking-wide text-stone-500">Nome de Utilizador</Label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-emerald-600" />
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="pl-12 h-12 text-lg border-stone-200 focus-visible:ring-emerald-500 rounded-xl"
                    placeholder="O teu nome"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="location" className="text-sm font-semibold uppercase tracking-wide text-stone-500">Localização</Label>
                <div className="relative">
                  <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-emerald-600" />
                  <Input
                    id="location"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="pl-12 h-12 border-stone-200 focus-visible:ring-emerald-500 rounded-xl"
                    placeholder="Ex: Viana do Castelo"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="bio" className="text-sm font-semibold uppercase tracking-wide text-stone-500">Sobre mim</Label>
                <div className="relative">
                  <FileText className="absolute left-4 top-4 h-4 w-4 text-emerald-600" />
                  <Textarea
                    id="bio"
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    className="pl-12 min-h-[130px] resize-none border-stone-200 focus-visible:ring-emerald-500 rounded-xl"
                    placeholder="Conta-nos um pouco sobre o teu estilo, peças favoritas ou como queres usar o teu closet."
                  />
                </div>
              </div>

              <div className="flex justify-end gap-4 pt-4">
                <Button variant="ghost" onClick={() => onOpenChange(false)} className="text-stone-500 hover:text-stone-700">
                  Cancelar
                </Button>
                <Button onClick={handleSubmit} disabled={loading || uploadingImage} className="bg-emerald-700 hover:bg-emerald-800 text-white px-6">
                  {loading ? 'A guardar...' : 'Guardar Alterações'}
                </Button>
              </div>
            </section>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}