import { ClothingItem } from "../types";

/**
 * Extended weather data interface that includes all relevant weather information
 * for outfit recommendations.
 */
export interface WeatherData {
  temperature: number; // in Celsius
  rain: boolean; // whether it's currently raining or rain is expected
  windSpeed?: number; // wind speed in m/s (optional, defaults to 0 if not provided)
  humidity?: number; // humidity percentage (optional)
  season?: string; // season identifier (optional)
}

/**
 * Represents a recommendation for a single item within a layer.
 */
export interface ItemRecommendation {
  item: ClothingItem;
  reasoning: string; // Human-readable explanation for why this item was selected
  category?: "jacket" | "shoes" | "accessories"; // Category of item for layer 3
}

/**
 * Represents a recommendation for a single layer of clothing.
 * Now supports multiple items per layer (e.g., jacket + shoes + hat for layer 3).
 */
export interface LayerRecommendation {
  items: ItemRecommendation[]; // Array of recommended items for this layer
  reasoning: string; // Overall reasoning for the layer
  isMissing: boolean; // True if no suitable items could be found for this layer
}

/**
 * Complete outfit recommendation containing recommendations for all three layers.
 */
export interface OutfitRecommendation {
  baseLayer: LayerRecommendation; // Layer 1: Base layer (e.g., t-shirt, tank top)
  insulationLayer: LayerRecommendation; // Layer 2: Insulation layer (e.g., sweater, cardigan)
  outerLayer: LayerRecommendation; // Layer 3: Outer protection layer (e.g., jacket, coat)
  weatherContext: WeatherData; // The weather data used for this recommendation
}

/**
 * Configuration thresholds for weather-based recommendations.
 * These can be adjusted to fine-tune the recommendation algorithm.
 */
const RECOMMENDATION_THRESHOLDS = {
  LOW_TEMPERATURE: 10, // °C - below this, consider additional layers
  VERY_LOW_TEMPERATURE: 5, // °C - below this, prioritize insulation
  STRONG_WIND: 10, // m/s - above this, prioritize windproof items
  MODERATE_TEMPERATURE: 15, // °C - above this, insulation layer may not be needed
} as const;

/**
 * Travel Planner mode configuration
 */
const TRAVEL_MODE_CONFIG = {
  baseLayersPerDay: 2, // Recommend 2 base layer items for a trip
  insulationLayersPerTrip: 2, // 1-2 insulation items depending on weather
  outerLayersPerTrip: 1, // At least 1 outer layer for protection
  accessoriesPerTrip: 3, // 2-3 accessories depending on conditions
} as const;

/**
 * Scoring function to evaluate how well an item matches the current weather conditions.
 * Higher scores indicate better matches.
 *
 * @param item - The clothing item to score
 * @param weather - Current weather conditions
 * @param layer - The layer number (1, 2, or 3)
 * @returns A numerical score representing how suitable the item is
 */
function scoreItem(
  item: ClothingItem,
  weather: WeatherData,
  layer: 1 | 2 | 3,
): number {
  let score = 0;

  // Base score: Temperature compatibility
  // Items whose temperature range includes the current temperature get the highest score
  if (
    weather.temperature >= item.tempMin &&
    weather.temperature <= item.tempMax
  ) {
    score += 100; // Perfect temperature match
  } else {
    // Partial credit for items close to the temperature range
    const rangeCenter = (item.tempMin + item.tempMax) / 2;
    const distance = Math.abs(weather.temperature - rangeCenter);
    const rangeWidth = item.tempMax - item.tempMin;
    score += Math.max(0, 100 - (distance / rangeWidth) * 50);
  }

  // Layer-specific scoring
  if (layer === 3) {
    // Outer layer: Prioritize protection features
    if (weather.rain && item.waterproof) {
      score += 50; // Strong preference for waterproof items in rain
    }
    if (
      weather.windSpeed &&
      weather.windSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND &&
      item.windproof
    ) {
      score += 40; // Strong preference for windproof items in strong wind
    }
    if (
      weather.temperature < RECOMMENDATION_THRESHOLDS.LOW_TEMPERATURE &&
      item.windproof
    ) {
      score += 30; // Prefer windproof items in cold conditions
    }
  } else if (layer === 2) {
    // Insulation layer: Prioritize items suitable for colder temperatures
    if (weather.temperature < RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE) {
      // Prefer items with lower tempMin (warmer items) in cold weather
      const insulationScore = Math.max(
        0,
        RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE - item.tempMin,
      );
      score += insulationScore * 2;
    }
  }

  // Bonus for favorite items (user preference)
  if (item.favorite) {
    score += 30;
  }

  return score;
}

/**
 * Generates a reasoning string explaining why a particular item was selected.
 *
 * @param item - The selected clothing item
 * @param weather - Current weather conditions
 * @param layer - The layer number
 * @returns A human-readable explanation
 */
function generateItemReasoning(
  item: ClothingItem,
  weather: WeatherData,
  layer: 1 | 2 | 3,
): string {
  const reasons: string[] = [];

  // Temperature-based reasoning
  if (
    weather.temperature >= item.tempMin &&
    weather.temperature <= item.tempMax
  ) {
    reasons.push(
      `Intervalo de temperatura perfeito (${item.tempMin}°C - ${item.tempMax}°C) para os ${weather.temperature}°C atuais`,
    );
  } else {
    reasons.push(
      `Intervalo de temperatura (${item.tempMin}°C - ${item.tempMax}°C) adequado para ${weather.temperature}°C`,
    );
  }

  // Layer-specific reasoning
  if (layer === 3) {
    if (weather.rain && item.waterproof) {
      reasons.push("proteção impermeável para a chuva");
    }
    if (
      weather.windSpeed &&
      weather.windSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND &&
      item.windproof
    ) {
      reasons.push("proteção contra ventos fortes");
    }
  } else if (layer === 2) {
    if (weather.temperature < RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE) {
      reasons.push("fornece isolamento para o tempo mais fresco");
    }
  }

  // Favorite item
  if (item.favorite) {
    reasons.push("marcado como favorito");
  }

  return reasons.length > 0
    ? `${reasons.join(", ")}`
    : "selecionado com base na disponibilidade e adequação básica";
}

/**
 * Valid item types for each layer. This ensures we recommend appropriate items
 * for each layer (e.g., T-shirts for base layer, not pants or shoes).
 * Layer 3 now includes jackets, shoes, and accessories.
 */
const LAYER_ITEM_TYPES: Record<number, string[]> = {
  1: ["t-shirt", "camiseta", "regata", "top", "tank top", "tshirt", "t shirt"], // Base layer: tops only
  2: [
    "camisola",
    "camisa",
    "sweater",
    "cardigan",
    "pullover",
    "hoodie",
    "shirt",
    "calças",
    "calções",
    "pants",
    "trousers",
    "jeans",
  ], // Insulation: sweaters, shirts, pants
  3: [
    "casaco",
    "jacket",
    "blusão",
    "coat",
    "parka",
    "blazer",
    "calçado",
    "sapatilhas",
    "sapatos",
    "sneakers",
    "shoes",
    "boots",
    "chapéu",
    "hat",
    "boné",
    "cap",
    "gorro",
    "beanie",
    "luvas",
    "gloves",
  ], // Outer layer: jackets, shoes, accessories
};

/**
 * Categories for layer 3 items to organize recommendations
 */
const LAYER3_CATEGORIES = {
  jacket: ["casaco", "jacket", "blusão", "coat", "parka", "blazer"],
  shoes: ["calçado", "sapatilhas", "sapatos", "sneakers", "shoes", "boots"],
  accessories: [
    "chapéu",
    "hat",
    "boné",
    "cap",
    "gorro",
    "beanie",
    "luvas",
    "gloves",
  ],
};

/**
 * Categories for layer 2 items to ensure we recommend both tops and bottoms
 */
const LAYER2_CATEGORIES = {
  legs: ["calça", "calças", "calções", "pants", "trousers", "jeans", "shorts"],
  torso: [
    "camisola",
    "camisa",
    "sweater",
    "cardigan",
    "pullover",
    "hoodie",
    "shirt",
  ],
};

/**
 * Determines the category of an item for layer 3
 */
function getLayer3Category(
  itemType: string,
): "jacket" | "shoes" | "accessories" | undefined {
  const normalized = itemType.toLowerCase().trim().replace(/[-\s]/g, "");
  for (const [category, types] of Object.entries(LAYER3_CATEGORIES)) {
    if (
      types.some(
        (type) =>
          normalized.includes(type.toLowerCase()) ||
          type.toLowerCase().includes(normalized),
      )
    ) {
      return category as "jacket" | "shoes" | "accessories";
    }
  }
  return undefined;
}

/**
 * Determines the category of an item for layer 2
 */
function getLayer2Category(itemType: string): "legs" | "torso" | undefined {
  const normalized = itemType.toLowerCase().trim().replace(/[-\s]/g, "");
  for (const [category, types] of Object.entries(LAYER2_CATEGORIES)) {
    if (
      types.some(
        (type) =>
          normalized.includes(type.toLowerCase()) ||
          type.toLowerCase().includes(normalized),
      )
    ) {
      return category as "legs" | "torso";
    }
  }
  return undefined;
}

/**
 * Checks if an item type is valid for a given layer.
 * Uses flexible matching to handle variations in naming.
 */
function isValidItemTypeForLayer(itemType: string, layer: 1 | 2 | 3): boolean {
  const validTypes = LAYER_ITEM_TYPES[layer] || [];
  // Normalize for comparison (case-insensitive, remove hyphens/spaces)
  const normalizedType = itemType.toLowerCase().trim().replace(/[-\s]/g, "");
  return validTypes.some((type) => {
    const normalizedValidType = type.toLowerCase().replace(/[-\s]/g, "");
    return (
      normalizedType.includes(normalizedValidType) ||
      normalizedValidType.includes(normalizedType)
    );
  });
}

/**
 * Recommends clothing items for a specific layer based on weather conditions.
 * For layer 3, recommends multiple items (jacket, shoes, accessories).
 *
 * @param items - Array of all available clothing items
 * @param weather - Current weather conditions
 * @param layer - The layer number (1, 2, or 3)
 * @returns A LayerRecommendation object with potentially multiple items
 */
function recommendLayer(
  items: ClothingItem[],
  weather: WeatherData,
  layer: 1 | 2 | 3,
  variant: number = 0,
): LayerRecommendation {
  // Filter items: only clean items of the correct layer AND valid item type
  const eligibleItems = items.filter(
    (item) =>
      item.status === "clean" &&
      item.layer === layer &&
      isValidItemTypeForLayer(item.type, layer),
  );

  if (eligibleItems.length === 0) {
    return {
      items: [],
      reasoning: `Sem itens limpos disponíveis para a camada ${layer}.`,
      isMissing: true,
    };
  }

  // Filter by temperature compatibility
  const tempCompatibleItems = eligibleItems.filter(
    (item) =>
      weather.temperature >= item.tempMin &&
      weather.temperature <= item.tempMax,
  );

  // Use temperature-compatible items if available, otherwise use all eligible items
  const candidateItems =
    tempCompatibleItems.length > 0 ? tempCompatibleItems : eligibleItems;

  // Score all candidate items
  const scoredItems = candidateItems.map((item) => ({
    item,
    score: scoreItem(item, weather, layer),
  }));

  // Sort by score (highest first), then by favorite status, then alphabetically for determinism
  scoredItems.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score; // Higher score first
    }
    if (a.item.favorite !== b.item.favorite) {
      return b.item.favorite ? 1 : -1; // Favorites first
    }
    return a.item.name.localeCompare(b.item.name); // Alphabetical for determinism
  });

  // For layer 3, recommend multiple items (one per category: jacket, shoes, accessories)
  if (layer === 3) {
    const recommendations: ItemRecommendation[] = [];
    const categoriesFound = new Set<string>();

    // Always try to get one jacket
    const jacketCandidates = scoredItems.filter(
      (item) => getLayer3Category(item.item.type) === "jacket",
    );
    if (jacketCandidates.length > 0) {
      const index = variant % jacketCandidates.length;
      const jacket = jacketCandidates[index];

      recommendations.push({
        item: jacket.item,
        reasoning: generateItemReasoning(jacket.item, weather, layer),
        category: "jacket",
      });
      categoriesFound.add("jacket");
    }

    // Try to get shoes
    const shoeCandidates = scoredItems.filter(
      (item) => getLayer3Category(item.item.type) === "shoes",
    );
    if (shoeCandidates.length > 0) {
      const index = variant % shoeCandidates.length;
      const shoes = shoeCandidates[index]; // Select based on variant

      recommendations.push({
        item: shoes.item,
        reasoning: generateItemReasoning(shoes.item, weather, layer),
        category: "shoes",
      });
      categoriesFound.add("shoes");
    }

    // Try to get accessories (hat, gloves, etc.) - especially for cold weather
    if (
      weather.temperature < RECOMMENDATION_THRESHOLDS.LOW_TEMPERATURE ||
      (weather.windSpeed &&
        weather.windSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND)
    ) {
      const accessoryCandidates = scoredItems.filter(
        (item) => getLayer3Category(item.item.type) === "accessories",
      );

      if (accessoryCandidates.length > 0) {
        const index = variant % accessoryCandidates.length;
        const accessory = accessoryCandidates[index];

        recommendations.push({
          item: accessory.item,
          reasoning: generateItemReasoning(accessory.item, weather, layer),
          category: "accessories",
        });
        categoriesFound.add("accessories");
      }
    }

    // If no specific categories found, at least recommend the top item
    if (recommendations.length === 0 && scoredItems.length > 0) {
      recommendations.push({
        item: scoredItems[0].item,
        reasoning: generateItemReasoning(scoredItems[0].item, weather, layer),
        category: getLayer3Category(scoredItems[0].item.type),
      });
    }

    return {
      items: recommendations,
      reasoning:
        recommendations.length > 0
          ? `Recomendado(s) ${recommendations.length} item(s) para camada de proteção`
          : "Nenhum item adequado encontrado",
      isMissing: recommendations.length === 0,
    };
  }

  // --- NEW LOGIC FOR LAYER 2 (Insulation) ---
  // Ensure we recommend ONE bottom (legs) AND ONE top (torso) if needed
  if (layer === 2) {
    const recommendations: ItemRecommendation[] = [];

    // 1. Always try to find a Bottom (Legs)
    // Pants are essential unless it's a dress (not handled here yet) or similar
    const legCandidates = scoredItems.filter(
      (item) => getLayer2Category(item.item.type) === "legs",
    );

    if (legCandidates.length > 0) {
      // Pick based on variant
      const index = variant % legCandidates.length;
      const legs = legCandidates[index];
      recommendations.push({
        item: legs.item,
        reasoning: generateItemReasoning(legs.item, weather, layer),
        // treating legs specially
      });
    }

    // 2. Try to find a Top (Torso/Insulation)
    // Only strictly needed if cold, but user might want one anyway or if it's their style
    // If it's warm (> 20C), maybe we don't strictly *need* a layer 2 top if they have a layer 1 top
    // But let's follow the standard logic: if it scores well (meaning temp is appropriate), suggest it.
    const torsoCandidates = scoredItems.filter(
      (item) => getLayer2Category(item.item.type) === "torso",
    );

    // Only recommend torso layer if weather actually calls for it (positive score or cold enough)
    // OR if we have no other options
    const needsInsulation =
      weather.temperature < RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE;
    // We filter torso candidates to those that trigger the "insulation needed" threshold
    // or simply the best one if we have nothing else.
    // Let's use the 'scoredItems' order. If the top item has a high score, it's good.

    if (torsoCandidates.length > 0) {
      // Pick based on variant
      const index = variant % torsoCandidates.length;
      const torsoItem = torsoCandidates[index];

      // Recommend if it's needed OR if it has a good score (meaning it fits the temp)
      if (needsInsulation || torsoItem.score > 50) {
        recommendations.push({
          item: torsoItem.item,
          reasoning: generateItemReasoning(torsoItem.item, weather, layer),
        });
      }
    }

    // If we found specific category items, return them
    if (recommendations.length > 0) {
      return {
        items: recommendations,
        reasoning: `Recomendado(s) ${recommendations.length} item(s) para a Camada 2`,
        isMissing: recommendations.length === 0,
      };
    }
    // Fallback if categorization failed but we have items (should act like before)
    // ... fall through to default single item picker logic below
  }

  // For layer 1, recommend single best item based on variant
  // ... (existing logic) ...
  const validCandidates = scoredItems.filter((s) => s.score > 0);

  // If no positive scores, fall back to all items
  const pool = validCandidates.length > 0 ? validCandidates : scoredItems;

  let selectedItem = null;
  if (pool.length > 0) {
    // Determine which index to pick based on the variant
    // variant 0 -> index 0 (best)
    // variant 1 -> index 1 (second best)
    // ... wrapping around
    const index = variant % pool.length;
    selectedItem = pool[index].item;
  }

  return {
    items: selectedItem
      ? [
        {
          item: selectedItem,
          reasoning: generateItemReasoning(selectedItem, weather, layer),
        },
      ]
      : [],
    reasoning: selectedItem
      ? generateItemReasoning(selectedItem, weather, layer)
      : `Nenhum item adequado encontrado para a camada ${layer}`,
    isMissing: selectedItem === null,
  };
}

/**
 * Generates a complete outfit recommendation based on weather conditions and available clothing items.
 *
 * The algorithm considers:
 * - Only clean items (dirty items are excluded)
 * - Temperature compatibility (items must be suitable for current temperature)
 * - Weather conditions (rain, wind)
 * - Layer requirements (base, insulation, outer protection)
 * - User preferences (favorite items are prioritized)
 *
 * @param items - Array of all available clothing items
 * @param weather - Current weather conditions
 * @returns A complete OutfitRecommendation object
 */
export function recommendOutfit(
  items: ClothingItem[],
  weather: WeatherData,
  variant: number = 0,
): OutfitRecommendation {
  // Normalize wind speed (default to 0 if not provided)
  const normalizedWeather: WeatherData = {
    ...weather,
    windSpeed: weather.windSpeed ?? 0,
  };

  // Generate recommendations for each layer
  const baseLayer = recommendLayer(items, normalizedWeather, 1, variant);
  const insulationLayer = recommendLayer(items, normalizedWeather, 2, variant);
  const outerLayer = recommendLayer(items, normalizedWeather, 3, variant);



  // Note: Layer 3 recommendations already handle multiple items (jacket, shoes, accessories)
  // in the recommendLayer function, so no additional logic needed here

  return {
    baseLayer,
    insulationLayer,
    outerLayer,
    weatherContext: normalizedWeather,
  };
}

/**
 * Determines if an insulation layer (layer 2) is needed based on temperature.
 *
 * @param temperature - Current temperature in Celsius
 * @returns true if an insulation layer is recommended
 */
export function isInsulationNeeded(temperature: number): boolean {
  return temperature < RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE;
}

/**
 * Determines if an outer layer (layer 3) is recommended based on weather conditions.
 *
 * @param weather - Current weather conditions
 * @returns true if an outer layer is recommended
 */
export function isOuterLayerRecommended(weather: WeatherData): boolean {
  if (weather.rain) {
    return true; // Always recommend outer layer in rain
  }
  if (weather.temperature < RECOMMENDATION_THRESHOLDS.LOW_TEMPERATURE) {
    return true; // Recommend in cold weather
  }
  if (
    weather.windSpeed &&
    weather.windSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND
  ) {
    return true; // Recommend in strong wind
  }
  return false;
}

/**
 * Travel Planner recommendation mode
 * Returns a capsule wardrobe for a trip based on expected weather conditions
 */
export interface TravelOutfitRecommendation extends OutfitRecommendation {
  tripContext: {
    destination: string;
    startDate?: string;
    endDate?: string;
    weatherForecast: WeatherData[];
  };
  packingNotes: string[];
}

/**
 * Generates a capsule wardrobe recommendation for a trip
 * Considers the full range of expected weather conditions during the trip
 *
 * @param items - Array of all available clothing items
 * @param tripContext - Trip information (destination, dates, weather forecast)
 * @returns A TravelOutfitRecommendation with multiple items per layer
 */
export function recommendTravelOutfit(
  items: ClothingItem[],
  tripContext: {
    destination: string;
    startDate?: string;
    endDate?: string;
    weatherForecast: WeatherData[];
  },
): TravelOutfitRecommendation {
  if (
    !tripContext.weatherForecast ||
    tripContext.weatherForecast.length === 0
  ) {
    throw new Error(
      "Travel outfit recommendation requires weather forecast data",
    );
  }

  // Calculate average and extreme weather conditions across the trip
  const temperatures = tripContext.weatherForecast.map((w) => w.temperature);
  const avgTemp = temperatures.reduce((a, b) => a + b, 0) / temperatures.length;
  const minTemp = Math.min(...temperatures);
  const maxTemp = Math.max(...temperatures);
  const willRain = tripContext.weatherForecast.some((w) => w.rain);
  const maxWindSpeed = Math.max(
    ...tripContext.weatherForecast.map((w) => w.windSpeed || 0),
  );

  // Create a synthetic "average weather" for capsule wardrobe generation
  const averageWeather: WeatherData = {
    temperature: avgTemp,
    rain: willRain,
    windSpeed: maxWindSpeed,
  };

  // Filter clean items only
  const cleanItems = items.filter((item) => item.status === "clean");

  // Build capsule wardrobe with multiple items per layer
  const baseLayer = recommendTravelLayer(cleanItems, averageWeather, 1, 2);
  const insulationLayer = recommendTravelLayer(
    cleanItems,
    averageWeather,
    2,
    minTemp < RECOMMENDATION_THRESHOLDS.MODERATE_TEMPERATURE ? 2 : 0,
  );
  const outerLayer = recommendTravelLayer(
    cleanItems,
    averageWeather,
    3,
    minTemp < RECOMMENDATION_THRESHOLDS.LOW_TEMPERATURE ||
      willRain ||
      maxWindSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND
      ? 2
      : 1,
  );

  // Generate packing notes based on trip weather
  const packingNotes: string[] = [];

  if (willRain) {
    packingNotes.push(
      "📍 Rain expected during trip - pack waterproof jackets or umbrellas",
    );
  }

  if (minTemp < RECOMMENDATION_THRESHOLDS.LOW_TEMPERATURE) {
    packingNotes.push(
      `🧥 Cold weather expected (min: ${minTemp}°C) - bring insulation layers and accessories`,
    );
  }

  if (maxWindSpeed >= RECOMMENDATION_THRESHOLDS.STRONG_WIND) {
    packingNotes.push(
      `💨 Strong winds expected (${maxWindSpeed} m/s) - pack windproof items and secure accessories`,
    );
  }

  if (maxTemp > 25) {
    packingNotes.push(
      `☀️ Warm weather expected (up to ${maxTemp}°C) - bring light fabrics and sun protection`,
    );
  }

  packingNotes.push(
    `📋 Temperature range during trip: ${minTemp}°C to ${maxTemp}°C (average: ${avgTemp.toFixed(1)}°C)`,
  );

  return {
    baseLayer,
    insulationLayer,
    outerLayer,
    weatherContext: averageWeather,
    tripContext,
    packingNotes,
  };
}

/**
 * Recommends multiple items for a specific layer for travel mode
 * More items are recommended compared to daily mode to build a versatile capsule wardrobe
 *
 * @param items - Array of all available clothing items
 * @param weather - Average weather conditions
 * @param layer - The layer number (1, 2, or 3)
 * @param maxItems - Maximum number of items to recommend for this layer
 * @returns A LayerRecommendation with multiple items
 */
function recommendTravelLayer(
  items: ClothingItem[],
  weather: WeatherData,
  layer: 1 | 2 | 3,
  maxItems: number,
): LayerRecommendation {
  // Filter items for this layer
  const eligibleItems = items.filter(
    (item) => item.layer === layer && isValidItemTypeForLayer(item.type, layer),
  );

  if (eligibleItems.length === 0 || maxItems === 0) {
    return {
      items: [],
      reasoning:
        maxItems === 0
          ? `Not needed for this trip's weather conditions`
          : `No items available for layer ${layer}`,
      isMissing: maxItems > 0,
    };
  }

  // Score all items
  const scoredItems = eligibleItems.map((item) => ({
    item,
    score: scoreItem(item, weather, layer),
  }));

  // Sort by score
  scoredItems.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.item.favorite !== b.item.favorite) return b.item.favorite ? 1 : -1;
    return a.item.name.localeCompare(b.item.name);
  });

  // For layer 3, prioritize by category first
  if (layer === 3) {
    const recommendations: ItemRecommendation[] = [];
    const categoryOrder = ["jacket", "shoes", "accessories"];

    for (const category of categoryOrder) {
      const categoryItems = scoredItems.filter(
        (item) => getLayer3Category(item.item.type) === category,
      );
      const itemsToAdd = Math.min(
        1,
        maxItems - recommendations.length,
        categoryItems.length,
      );

      for (let i = 0; i < itemsToAdd; i++) {
        recommendations.push({
          item: categoryItems[i].item,
          reasoning: generateItemReasoning(
            categoryItems[i].item,
            weather,
            layer,
          ),
          category: category as "jacket" | "shoes" | "accessories",
        });
      }
    }

    return {
      items: recommendations,
      reasoning: `Recommended ${recommendations.length} protective item${recommendations.length !== 1 ? "s" : ""} for trip`,
      isMissing: recommendations.length === 0,
    };
  }

  // For layers 1 and 2, recommend top N items
  const topItems = scoredItems.slice(0, maxItems);

  return {
    items: topItems.map((scored) => ({
      item: scored.item,
      reasoning: generateItemReasoning(scored.item, weather, layer),
    })),
    reasoning: `Recommended ${topItems.length} item${topItems.length !== 1 ? "s" : ""} for layer ${layer}`,
    isMissing: topItems.length === 0,
  };
}

/**
 * Utility function to estimate weather for a destination
 * Used as fallback if detailed forecast is not available
 *
 * @param destination - City name or location
 * @param daysOfTrip - Number of days
 * @returns Array of estimated WeatherData for each day
 */
export function estimateTravelWeather(
  destination: string,
  daysOfTrip: number = 7,
): WeatherData[] {
  // This is a fallback estimation. In production, this would call a real weather API
  // For now, return a reasonable default range
  const forecast: WeatherData[] = [];

  for (let i = 0; i < daysOfTrip; i++) {
    forecast.push({
      temperature: 15 + Math.random() * 10, // 15-25°C range
      rain: Math.random() > 0.7, // 30% chance of rain
      windSpeed: 5 + Math.random() * 10, // 5-15 m/s
    });
  }

  return forecast;
}

/**
 * Generates a travel outfit recommendation with minimal input
 * Useful for quick trip planning without detailed weather data
 *
 * @param items - Array of all available clothing items
 * @param destination - Trip destination
 * @param estimatedTemp - Estimated temperature range in Celsius
 * @param estimatedRain - Whether rain is expected
 * @returns A TravelOutfitRecommendation
 */
export function quickTravelRecommendation(
  items: ClothingItem[],
  destination: string,
  estimatedTemp: { min: number; max: number },
  estimatedRain: boolean = false,
): TravelOutfitRecommendation {
  const daysOfTrip = 3; // Default to 3-day trip
  const avgTemp = (estimatedTemp.min + estimatedTemp.max) / 2;

  // Create a forecast based on estimated conditions
  const weatherForecast = Array(daysOfTrip)
    .fill(null)
    .map(() => ({
      temperature: avgTemp,
      rain: estimatedRain,
      windSpeed: 8,
    }));

  return recommendTravelOutfit(items, {
    destination,
    weatherForecast,
  });
}
