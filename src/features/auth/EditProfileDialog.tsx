import { useEffect, useRef, useState } from "react";
import { Camera } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

import { UserProfile } from "../../types";
import * as api from "../../services/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userData: {
    name: string;
    avatar_url: string;
    bio: string;
    location: string;
  };
  onUpdate: (data: Partial<UserProfile>) => void;
}

export function EditProfileDialog({ open, onOpenChange, userData, onUpdate }: Props) {
  const [form, setForm] = useState({
    name: "",
    location: "",
    bio: "",
    avatar_url: "",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // sincronizar com dados atuais sempre que se abre o modal
  useEffect(() => {
    if (userData && open) {
      setForm({
        name: userData.name || "",
        location: userData.location || "",
        bio: userData.bio || "",
        avatar_url: userData.avatar_url || "",
      });
    }
  }, [userData, open]);

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (
      event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64 = reader.result as string;

      try {
        // upload para o backend (rota /upload-image)
        const { url } = await api.uploadImage(base64, file.name);
        setForm((prev) => ({ ...prev, avatar_url: url }));
      } catch (error) {
        console.error("Erro ao enviar imagem:", error);
        alert("Erro ao enviar imagem de perfil.");
      } finally {
        setIsUploading(false);
      }
    };

    reader.readAsDataURL(file);
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        location: form.location.trim() || null,
        bio: form.bio.trim() || null,
        avatar_url: form.avatar_url || null,
      };

      // grava no backend
      await api.updateProfile(payload);
      // atualiza imediatamente o Dashboard
      onUpdate(payload);

      onOpenChange(false);
    } catch (error: any) {
      console.error("Erro ao atualizar perfil:", error);
      alert(error?.message || "Erro ao guardar alterações do perfil.");
    } finally {
      setIsSaving(false);
    }
  };

  const avatarSrc =
      form.avatar_url && form.avatar_url.length > 0
          ? form.avatar_url
          : "/default-avatar.png"; // mete aqui um placeholder que tenhas na app

  return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent
            className="
          max-w-md
          w-full
          bg-white
          rounded-2xl
          shadow-2xl
          p-6
          animate-in
          fade-in
          zoom-in-95
          duration-300
        "
        >
          <DialogHeader className="text-center space-y-2">
            <DialogTitle className="text-xl font-semibold text-stone-800">
              Editar Perfil
            </DialogTitle>

            <p className="text-sm text-stone-500">
              Atualiza o teu nome, fotografia e detalhes pessoais.
            </p>
          </DialogHeader>

          {/* Avatar + botão da câmara */}
          <div className="flex flex-col items-center mt-4 mb-6">
            <div className="relative">
              <img
                  src={avatarSrc}
                  className="w-28 h-28 rounded-full object-cover shadow-md border border-stone-200 bg-stone-100"
              />
              <button
                  type="button"
                  onClick={handleAvatarClick}
                  disabled={isUploading}
                  className="
                absolute bottom-0 right-0
                p-2 rounded-full bg-emerald-600
                text-white shadow-lg hover:bg-emerald-700
                disabled:opacity-60
              "
              >
                <Camera size={16} />
              </button>
            </div>

            <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleAvatarChange}
            />

            {isUploading && (
                <p className="mt-2 text-xs text-stone-500">
                  A enviar fotografia...
                </p>
            )}
          </div>

          {/* Form fields */}
          <div className="space-y-4 mt-2">
            <div>
              <label className="text-sm font-medium text-stone-700">
                Nome de utilizador
              </label>
              <Input
                  value={form.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  className="mt-1"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-stone-700">
                Localização
              </label>
              <Input
                  value={form.location}
                  onChange={(e) => handleChange("location", e.target.value)}
                  className="mt-1"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-stone-700">
                Sobre mim
              </label>
              <Textarea
                  value={form.bio}
                  onChange={(e) => handleChange("bio", e.target.value)}
                  className="mt-1 h-24"
              />
            </div>
          </div>

          <DialogFooter className="mt-6 flex justify-between">
            <Button
                variant="ghost"
                onClick={() => onOpenChange(false)}
                disabled={isSaving}
            >
              Cancelar
            </Button>

            <Button
                onClick={handleSubmit}
                disabled={isSaving || isUploading}
                className="bg-emerald-600 hover:bg-emerald-700"
            >
              {isSaving ? "A guardar..." : "Guardar alterações"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
  );
}