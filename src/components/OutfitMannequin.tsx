import React, { useState } from "react";
import { ClothingItem } from "../types";
import { LayerRecommendation } from "../services/outfitRecommendation";
import { Card } from "./ui/card";
import { AlertCircle, Droplets, Wind } from "lucide-react";

interface OutfitMannequinProps {
  baseLayer: LayerRecommendation;
  insulationLayer: LayerRecommendation;
  outerLayer: LayerRecommendation;
  onViewItem?: (item: ClothingItem) => void;
}

export function OutfitMannequin({
  baseLayer,
  insulationLayer,
  outerLayer,
  onViewItem,
}: OutfitMannequinProps) {
  const [selectedItem, setSelectedItem] = useState<ClothingItem | null>(null);

  // Organizar itens por posição no corpo
  const getAccessories = () =>
    outerLayer.items.filter((item) => item.category === "accessories");
  const getTops = () => [
    ...baseLayer.items.filter(
      (item) => !item.item.type.toLowerCase().includes("calça"),
    ),
    ...insulationLayer.items.filter(
      (item) => !item.item.type.toLowerCase().includes("calça"),
    ),
    ...outerLayer.items.filter(
      (item) =>
        item.category === "jacket" ||
        (!item.category && !item.item.type.toLowerCase().includes("calça")),
    ),
  ];

  const getBottoms = () => [
    ...baseLayer.items.filter((item) =>
      item.item.type.toLowerCase().includes("calça"),
    ),
    ...insulationLayer.items.filter((item) =>
      item.item.type.toLowerCase().includes("calça"),
    ),
  ];

  const getShoes = () =>
    outerLayer.items.filter((item) => item.category === "shoes");

  const accessories = getAccessories();
  const tops = getTops();
  const bottoms = getBottoms();
  const shoes = getShoes();

  const hasAnyRecommendation =
    baseLayer.items.length > 0 ||
    insulationLayer.items.length > 0 ||
    outerLayer.items.length > 0;

  const SmallItemDisplay = ({
    item,
    reasoning,
  }: {
    item: ClothingItem;
    reasoning: string;
  }) => (
    <div
      onClick={() => {
        onViewItem?.(item);
        setSelectedItem(item);
      }}
      className="w-12 h-12 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
      title={`${item.name}\n${reasoning}`}
    >
      <img
        src={item.image || "https://via.placeholder.com/50?text=Item"}
        alt={item.name}
        className="w-full h-full object-contain p-1"
        onError={(e) => {
          e.currentTarget.src = "https://via.placeholder.com/50?text=Item";
        }}
      />
      {/* Badges pequenos */}
      <div className="absolute -top-1 -right-1 flex gap-0.5">
        {item.waterproof && (
          <div className="bg-blue-500 p-0.5 rounded-full" title="Waterproof">
            <Droplets className="w-2 h-2 text-white" />
          </div>
        )}
        {item.windproof && (
          <div className="bg-cyan-500 p-0.5 rounded-full" title="Windproof">
            <Wind className="w-2 h-2 text-white" />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      <Card className="overflow-hidden bg-gradient-to-br from-white via-stone-50/30 to-white border-stone-200/80 shadow-2xl">
        {/* Header */}
        <div className="px-10 pt-10 pb-6">
          <h3 className="text-2xl font-bold text-stone-900 tracking-tight mb-1">
            Visualização do Outfit
          </h3>
          <p className="text-sm text-stone-500">
            Recomendação personalizada baseada nas condições meteorológicas
          </p>
        </div>

        {/* Mannequin Visualization */}
        <div className="px-10 pb-10">
          {hasAnyRecommendation ? (
            <div className="flex flex-col items-center gap-8">
              {/* Mannequim Simples */}
              <div className="flex flex-col items-center gap-2">
                {/* Acessórios (Topo) */}
                {accessories.length > 0 && (
                  <div className="flex gap-3">
                    {accessories.map((item) => (
                      <div
                        key={item.item.id}
                        className="w-20 h-20 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
                        onClick={() => {
                          onViewItem?.(item.item);
                          setSelectedItem(item.item);
                        }}
                      >
                        <img
                          src={
                            item.item.image ||
                            "https://via.placeholder.com/64?text=Item"
                          }
                          alt={item.item.name}
                          className="w-full h-full object-contain p-1"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://via.placeholder.com/64?text=Item";
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Tops/Camisolas */}
                {tops.length > 0 && (
                  <div className="flex gap-3 flex-wrap justify-center max-w-md">
                    {tops.map((item) => (
                      <div
                        key={item.item.id}
                        className="w-20 h-20 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
                        onClick={() => {
                          onViewItem?.(item.item);
                          setSelectedItem(item.item);
                        }}
                      >
                        <img
                          src={
                            item.item.image ||
                            "https://via.placeholder.com/64?text=Item"
                          }
                          alt={item.item.name}
                          className="w-full h-full object-contain p-1"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://via.placeholder.com/64?text=Item";
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Bottoms/Calças */}
                {bottoms.length > 0 && (
                  <div className="flex gap-3 flex-wrap justify-center max-w-md">
                    {bottoms.map((item) => (
                      <div
                        key={item.item.id}
                        className="w-20 h-20 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
                        onClick={() => {
                          onViewItem?.(item.item);
                          setSelectedItem(item.item);
                        }}
                      >
                        <img
                          src={
                            item.item.image ||
                            "https://via.placeholder.com/64?text=Item"
                          }
                          alt={item.item.name}
                          className="w-full h-full object-contain p-1"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://via.placeholder.com/64?text=Item";
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Sapatos */}
                {shoes.length > 0 && (
                  <div className="flex gap-3">
                    {shoes.map((item) => (
                      <div
                        key={item.item.id}
                        className="w-20 h-20 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
                        onClick={() => {
                          onViewItem?.(item.item);
                          setSelectedItem(item.item);
                        }}
                      >
                        <img
                          src={
                            item.item.image ||
                            "https://via.placeholder.com/64?text=Item"
                          }
                          alt={item.item.name}
                          className="w-full h-full object-contain p-1"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://via.placeholder.com/64?text=Item";
                          }}
                        />
                      </div>
                    ))}
                    {shoes.length === 1 && (
                      <div
                        className="w-20 h-20 rounded border border-gray-300 bg-white flex items-center justify-center cursor-pointer hover:border-blue-500 hover:shadow-md transition-all relative group"
                        onClick={() => {
                          onViewItem?.(shoes[0].item);
                          setSelectedItem(shoes[0].item);
                        }}
                      >
                        <img
                          src={
                            shoes[0].item.image ||
                            "https://via.placeholder.com/64?text=Item"
                          }
                          alt={`${shoes[0].item.name} (2)`}
                          className="w-full h-full object-contain p-1"
                          onError={(e) => {
                            e.currentTarget.src =
                              "https://via.placeholder.com/64?text=Item";
                          }}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Mensagem se vazio */}
                {!accessories.length &&
                  !tops.length &&
                  !bottoms.length &&
                  !shoes.length && (
                    <p className="text-sm text-stone-400">
                      Nenhum item sugerido
                    </p>
                  )}
              </div>
            </div>
          ) : (
            /* Empty State */
            <div className="flex items-center justify-center h-96 text-stone-400">
              <div className="text-center">
                <AlertCircle className="h-20 w-20 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium text-stone-500">
                  Nenhuma recomendação disponível
                </p>
                <p className="text-sm text-stone-400 mt-2">
                  Adicione mais itens ao seu inventário
                </p>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Layer Details Cards */}
      <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Layer 1 - Base */}
        <Card className="p-4 border-emerald-200 bg-emerald-50/50">
          <h4 className="font-semibold text-emerald-900 mb-3">
            Camada Base
            <span className="text-xs font-normal text-emerald-700 ml-2">
              ({baseLayer.items.length} item
              {baseLayer.items.length !== 1 ? "s" : ""})
            </span>
          </h4>
          <p className="text-xs text-emerald-700 mb-3">Camisolas e bottoms</p>

          {baseLayer.items.length > 0 ? (
            <div className="space-y-3">
              {baseLayer.items.map((item) => (
                <div
                  key={item.item.id}
                  className="p-4 bg-white rounded border border-emerald-200 cursor-pointer hover:border-emerald-400 hover:bg-emerald-50/30 transition-all flex flex-col items-center gap-3"
                  onClick={() => onViewItem?.(item.item)}
                >
                  <div className="w-32 h-32 rounded-lg border border-emerald-100 bg-gray-50 flex items-center justify-center overflow-hidden">
                    <img
                      src={
                        item.item.image ||
                        "https://via.placeholder.com/128?text=No+Image"
                      }
                      alt={item.item.name}
                      className="w-full h-full object-contain p-2"
                      onError={(e) => {
                        e.currentTarget.src =
                          "https://via.placeholder.com/128?text=No+Image";
                      }}
                    />
                  </div>
                  <div className="text-center w-full">
                    <p className="font-sm font-medium text-emerald-900 text-sm mb-1">
                      {item.item.name}
                    </p>
                    <p className="text-xs text-emerald-700 line-clamp-2">
                      {item.reasoning}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-3 bg-white rounded border border-dashed border-emerald-200 text-center text-emerald-600 text-xs">
              {baseLayer.reasoning || "Sem sugestão"}
            </div>
          )}
        </Card>

        {/* Layer 2 - Insulation */}
        <Card className="p-4 border-amber-200 bg-amber-50/50">
          <h4 className="font-semibold text-amber-900 mb-3">
            Camada Intermédia
            <span className="text-xs font-normal text-amber-700 ml-2">
              ({insulationLayer.items.length} item
              {insulationLayer.items.length !== 1 ? "s" : ""})
            </span>
          </h4>
          <p className="text-xs text-amber-700 mb-3">Camisolas e calças</p>

          {insulationLayer.items.length > 0 ? (
            <div className="space-y-3">
              {insulationLayer.items.map((item) => (
                <div
                  key={item.item.id}
                  className="p-4 bg-white rounded border border-amber-200 cursor-pointer hover:border-amber-400 hover:bg-amber-50/30 transition-all flex flex-col items-center gap-3"
                  onClick={() => onViewItem?.(item.item)}
                >
                  <div className="w-32 h-32 rounded-lg border border-amber-100 bg-gray-50 flex items-center justify-center overflow-hidden">
                    <img
                      src={
                        item.item.image ||
                        "https://via.placeholder.com/128?text=No+Image"
                      }
                      alt={item.item.name}
                      className="w-full h-full object-contain p-2"
                      onError={(e) => {
                        e.currentTarget.src =
                          "https://via.placeholder.com/128?text=No+Image";
                      }}
                    />
                  </div>
                  <div className="text-center w-full">
                    <p className="font-sm font-medium text-amber-900 text-sm mb-1">
                      {item.item.name}
                    </p>
                    <p className="text-xs text-amber-700 line-clamp-2">
                      {item.reasoning}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-3 bg-white rounded border border-dashed border-amber-200 text-center text-amber-600 text-xs">
              {insulationLayer.reasoning || "Sem sugestão"}
            </div>
          )}
        </Card>

        {/* Layer 3 - Outer Protection */}
        <Card className="p-4 border-sky-200 bg-sky-50/50">
          <h4 className="font-semibold text-sky-900 mb-3">
            Proteção Externa
            <span className="text-xs font-normal text-sky-700 ml-2">
              ({outerLayer.items.length} item
              {outerLayer.items.length !== 1 ? "s" : ""})
            </span>
          </h4>
          <p className="text-xs text-sky-700 mb-3">
            Casacos, calçado e acessórios
          </p>

          {outerLayer.items.length > 0 ? (
            <div className="space-y-3">
              {outerLayer.items.map((item) => (
                <div
                  key={item.item.id}
                  className="p-4 bg-white rounded border border-sky-200 cursor-pointer hover:border-sky-400 hover:bg-sky-50/30 transition-all flex flex-col items-center gap-3"
                  onClick={() => onViewItem?.(item.item)}
                >
                  <div className="w-32 h-32 rounded-lg border border-sky-100 bg-gray-50 flex items-center justify-center overflow-hidden">
                    <img
                      src={
                        item.item.image ||
                        "https://via.placeholder.com/128?text=No+Image"
                      }
                      alt={item.item.name}
                      className="w-full h-full object-contain p-2"
                      onError={(e) => {
                        e.currentTarget.src =
                          "https://via.placeholder.com/128?text=No+Image";
                      }}
                    />
                  </div>
                  <div className="text-center w-full">
                    <p className="font-sm font-medium text-sky-900 text-sm mb-1">
                      {item.item.name}
                    </p>
                    <p className="text-xs text-sky-700 line-clamp-2">
                      {item.reasoning}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-3 bg-white rounded border border-dashed border-sky-200 text-center text-sky-600 text-xs">
              {outerLayer.reasoning || "Sem sugestão"}
            </div>
          )}
        </Card>
      </div>

      {/* Item Details Modal */}
      {selectedItem && (
        <Card className="p-6 border-blue-200 bg-blue-50/50">
          <button
            onClick={() => setSelectedItem(null)}
            className="mb-4 text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Voltar
          </button>
          <div className="flex gap-6">
            <div className="w-32 h-32 bg-white rounded-lg border border-blue-200 overflow-hidden flex-shrink-0">
              <img
                src={
                  selectedItem.image ||
                  "https://via.placeholder.com/100?text=No+Image"
                }
                alt={selectedItem.name}
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-blue-900 mb-2">
                {selectedItem.name}
              </h3>
              <p className="text-sm text-blue-700 mb-3">{selectedItem.brand}</p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="font-semibold text-blue-900">Tipo:</span>
                  <p className="text-blue-700">{selectedItem.type}</p>
                </div>
                <div>
                  <span className="font-semibold text-blue-900">Tamanho:</span>
                  <p className="text-blue-700">{selectedItem.size}</p>
                </div>
                <div>
                  <span className="font-semibold text-blue-900">
                    Temperatura:
                  </span>
                  <p className="text-blue-700">
                    {selectedItem.tempMin}°C - {selectedItem.tempMax}°C
                  </p>
                </div>
                <div>
                  <span className="font-semibold text-blue-900">Material:</span>
                  <p className="text-blue-700">
                    {selectedItem.materials.join(", ")}
                  </p>
                </div>
              </div>
              {(selectedItem.waterproof || selectedItem.windproof) && (
                <div className="mt-3 flex gap-2">
                  {selectedItem.waterproof && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      💧 Impermeável
                    </span>
                  )}
                  {selectedItem.windproof && (
                    <span className="text-xs bg-cyan-100 text-cyan-800 px-2 py-1 rounded">
                      💨 Resistente ao Vento
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
