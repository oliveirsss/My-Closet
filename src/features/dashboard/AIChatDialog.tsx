import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { ScrollArea } from "../../components/ui/scroll-area";
import { Sparkles, Send, User, Bot, AlertTriangle, RefreshCw } from "lucide-react";
import * as api from "../../services/api";
import { ClothingItem } from "../../types";
import { OutfitMannequin } from "../../components/OutfitMannequin";

interface AIChatDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  weather: { temp: number; condition: string; humidity: number; windSpeed: number; rain: boolean; city: string };
  items: ClothingItem[];
  onViewItem: (item: ClothingItem) => void;
  onAcceptOutfit?: (outfitItems: ClothingItem[]) => void;
}

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  isError?: boolean;
  outfitData?: any;
  missingItems?: string[];
}

export function AIChatDialog({ open, onOpenChange, weather, items, onViewItem, onAcceptOutfit }: AIChatDialogProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), sender: "user", text: inputValue };
    setMessages(prev => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      const dirtyIds = items.filter(i => i.status === "dirty").map(i => i.id);
      const response = await api.getAIDailyOutfit(weather, { style: userMsg.text }, dirtyIds);

      if (response.success) {
        // Parse "PECAS_EM_FALTA" from reasoning text
        const reasoning = response.primary_outfit?.reasoning || "";
        const missingMatch = reasoning.match(/PECAS_EM_FALTA:\s*([^\n]+)/i);
        const missingItems = missingMatch
          ? missingMatch[1].trim().toLowerCase() === "nenhuma" ? [] : missingMatch[1].trim().split(",").map((s: string) => s.trim()).filter(Boolean)
          : [];

        // Clean display text (remove internal tags)
        const displayText = reasoning
          .replace(/PECAS_EM_FALTA:[^\n]*/gi, "")
          .trim() || "Aqui está a minha sugestão!";

        const aiMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: "ai",
          text: displayText,
          outfitData: response,
          missingItems,
        };
        setMessages(prev => [...prev, aiMsg]);
      } else {
        const errorMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: "ai",
          text: response.error || "Ocorreu um erro ao processar o seu pedido.",
          isError: true
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (e: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        text: e.message || "Não foi possível contactar o LLaVA. Verifique se o backend/Ollama está a correr.",
        isError: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSendMessage();
    }
  };

  const isBottomType = (item: any) => {
    const t = ((item.type || '') + ' ' + (item.name || '')).toLowerCase();
    return t.includes('calça') || t.includes('calca') || t.includes('short') || t.includes('jeans') || t.includes('trousers') || t.includes('pant') || t.includes('skirt') || t.includes('saia');
  };

  const isShoeType = (item: any) => {
    const t = ((item.type || '') + ' ' + (item.name || '')).toLowerCase();
    return t.includes('sapato') || t.includes('sapatilha') || t.includes('ténis') || t.includes('tenis') || t.includes('sneaker') || t.includes('bota') || t.includes('calçado') || t.includes('shoe') || t.includes('jordan') || t.includes('dunk') || t.includes('af1');
  };

  const isJacketType = (item: any) => {
    const t = ((item.type || '') + ' ' + (item.name || '')).toLowerCase();
    return t.includes('casaco') || t.includes('jacket') || t.includes('sobretudo') || t.includes('coat') || t.includes('blusão') || t.includes('hoodie') || t.includes('sweat') || t.includes('shirt');
  };

  const mapAiToLayers = (aiItems: any[]) => {
    const baseItems: any[] = [];
    const insulationItems: any[] = [];
    const outerItems: any[] = [];

    aiItems.forEach(item => {
      if (isShoeType(item)) {
        item.category = 'shoes';
        outerItems.push(item);
      } else if (isJacketType(item)) {
        item.category = 'jacket';
        outerItems.push(item);
      } else if (isBottomType(item)) {
        item.category = 'bottoms';
        baseItems.push(item);
      } else if (item.layer === 2) {
        insulationItems.push(item);
      } else {
        baseItems.push(item);
      }
    });

    // Fallback com peças REAIS do armário em vez de placeholders SVG
    const hasBottoms = baseItems.some(i => isBottomType(i));
    if (!hasBottoms) {
      // Procura calças reais no armário do utilizador
      const realBottom = items.find(i =>
        i.status === 'clean' &&
        isBottomType(i)
      );
      if (realBottom) {
        baseItems.push({ ...realBottom, category: 'bottoms' });
      }
    }

    const hasShoes = outerItems.some(i => i.category === 'shoes');
    if (!hasShoes) {
      // Procura sapatos reais no armário do utilizador
      const realShoe = items.find(i =>
        i.status === 'clean' &&
        isShoeType(i)
      );
      if (realShoe) {
        outerItems.push({ ...realShoe, category: 'shoes' });
      }
    }

    return {
      baseLayer: { items: baseItems.map(item => ({ item, reasoning: "" })), reasoning: "", isMissing: baseItems.length === 0 },
      insulationLayer: { items: insulationItems.map(item => ({ item, reasoning: "" })), reasoning: "", isMissing: insulationItems.length === 0 },
      outerLayer: { items: outerItems.map(item => ({ item, reasoning: "" })), reasoning: "", isMissing: outerItems.length === 0 },
    };
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl h-[85vh] flex flex-col p-0 gap-0 overflow-hidden bg-stone-50 border-emerald-100">
        <DialogHeader className="p-4 bg-emerald-700 text-white shadow-md z-10 shrink-0">
          <DialogTitle className="flex items-center gap-2 text-xl tracking-wide">
            <Sparkles className="h-5 w-5 text-emerald-200" /> AI Style Assistant
          </DialogTitle>
          <DialogDescription className="text-emerald-50">
            Peça sugestões de estilo específicas ou outfits para diferentes ocasiões.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 p-4 bg-transparent overflow-y-auto w-full">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 pt-10 pb-10">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-emerald-600" />
              </div>
              <div className="max-w-md">
                <h3 className="text-lg font-semibold text-emerald-900 mb-2">Como o posso ajudar hoje?</h3>
                <p className="text-stone-500 text-sm">
                  Experimente pedir: "Quero um look mais casual e em tons mais escuros." ou "Sugere algo quente para o trabalho hoje."
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6 max-w-full overflow-hidden pb-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex max-w-full ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-3 max-w-[85%] ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"}`}>
                    <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1 shadow-sm ${msg.sender === "user" ? "bg-stone-200 text-stone-600" : "bg-emerald-600 text-white"}`}>
                      {msg.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    
                    <div className={`flex flex-col gap-2 min-w-0 max-w-full ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                      <div className={`rounded-2xl px-5 py-3 shadow-sm inline-block break-words max-w-full
                        ${msg.sender === "user" ? "bg-emerald-600 text-white rounded-tr-none" 
                        : msg.isError ? "bg-red-50 text-red-700 border border-red-200 rounded-tl-none" 
                        : "bg-white text-stone-700 border border-stone-200 rounded-tl-none"}
                      `}>
                        {msg.isError && <AlertTriangle className="w-4 h-4 inline mr-2 text-red-500 shrink-0" />}
                        <span className="whitespace-pre-wrap">{msg.text}</span>
                      </div>
                      
                      {/* Banner de pecas em falta */}
                      {msg.missingItems && msg.missingItems.length > 0 && (
                        <div className="mt-2 w-full rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 flex gap-2 items-start">
                          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-sm font-semibold text-amber-700">Peças em falta no teu armário:</p>
                            <ul className="mt-1 space-y-0.5">
                              {msg.missingItems.map((item, i) => (
                                <li key={i} className="text-sm text-amber-600">• {item}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {msg.outfitData && msg.outfitData.primary_outfit?.items?.length > 0 && (
                        <div className="mt-2 w-full min-w-0 rounded-xl bg-white border border-emerald-100 shadow-sm p-4 animate-in fade-in zoom-in duration-300 overflow-hidden max-w-full mx-auto" style={{ maxWidth: '40rem' }}>
                           <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-4 border-b border-emerald-50 pb-2 flex items-center gap-2"><Sparkles className="w-3 h-3"/> Outfit Sugerido</p>
                           <div className="scale-90 origin-top overflow-visible -mb-8">
                             <OutfitMannequin
                               baseLayer={mapAiToLayers(msg.outfitData.primary_outfit.items).baseLayer}
                               insulationLayer={mapAiToLayers(msg.outfitData.primary_outfit.items).insulationLayer}
                               outerLayer={mapAiToLayers(msg.outfitData.primary_outfit.items).outerLayer}
                               onViewItem={onViewItem}
                               hideDetails={true}
                             />
                           </div>
                           {onAcceptOutfit && (
                             <button
                               onClick={() => {
                                 onAcceptOutfit(msg.outfitData.primary_outfit.items as ClothingItem[]);
                                 onOpenChange(false);
                               }}
                               className="mt-4 w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold transition-all shadow-sm shadow-emerald-600/20 flex items-center justify-center gap-2"
                             >
                               <Sparkles className="w-4 h-4" />
                               Definir como Sugestão do Dia
                             </button>
                           )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                 <div className="flex justify-start">
                   <div className="flex gap-3 max-w-[80%]">
                     <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center mt-1">
                        <Bot className="w-4 h-4" />
                     </div>
                     <div className="bg-white border border-stone-200 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm flex items-center gap-3">
                         <div className="flex gap-1">
                           <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                           <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                           <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                         </div>
                         <span className="text-sm text-stone-500 font-medium ml-1">A pensar no outfit ideal...</span>
                     </div>
                   </div>
                 </div>
              )}
            </div>
          )}
        </ScrollArea>

        <div className="p-4 bg-white border-t border-stone-200 shrink-0">
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Descreva o estilo ou a ocasião (ex: Casual com tons escuros)..."
              disabled={isLoading}
              className="flex-1 focus-visible:ring-emerald-500 text-base py-6 rounded-xl border-stone-300 shadow-sm"
            />
            <Button 
              onClick={handleSendMessage} 
              disabled={isLoading || !inputValue.trim()}
              className="bg-emerald-600 hover:bg-emerald-700 text-white h-auto px-6 rounded-xl shadow-sm transition-all shadow-emerald-600/20"
            >
              {isLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
