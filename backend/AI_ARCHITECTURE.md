# AI-Powered Outfit Recommendation System - Phase 1 Architecture

## Overview

This document describes the architectural changes made to the My Closet backend to support AI-powered outfit recommendations using Visual Language Models (VLMs), specifically targeting LLaVA as the primary model.

**Phase 1 Status**: Architecture design and foundational implementation  
**Phase 2 (Future)**: Full LLaVA integration and VLM implementation  
**Current VLM**: Mock service for testing and development

---

## 1. Executive Summary

### What Changed
- **New Service Layer**: Introduced modular, abstraction-based services for wardrobe, weather, usage tracking, prompt building, VLM integration, and response parsing
- **New API Routes**: Added `/ai-outfit/today`, `/ai-outfit/travel`, and `/ai-outfit/alternative` endpoints
- **New Schemas**: Defined request/response models for AI recommendations
- **Backward Compatible**: Existing functionality remains untouched; old recommendation system can coexist

### Key Architectural Principles
1. **Modularity**: Each responsibility is isolated in its own service
2. **Abstraction**: VLM provider can be swapped without changing the recommendation pipeline
3. **Testability**: Services can be mocked and tested independently
4. **Fallback Safety**: Rule-based recommendations available if VLM fails
5. **Scalability**: Services designed to scale horizontally

---

## 2. Project Structure

### New Directory: `/backend/services/`
```
backend/services/
├── __init__.py                      # Service exports
├── wardrobe_service.py              # Fetch and format wardrobe items
├── weather_service.py               # Weather data management
├── usage_service.py                 # Item usage frequency tracking
├── prompt_service.py                # Build VLM prompts
├── vlm_service.py                   # VLM interface and implementations
├── recommendation_service.py         # Orchestrator service
└── response_parser.py               # Parse and normalize VLM responses
```

### New Directory: `/backend/schemas/`
```
backend/schemas/
├── __init__.py                      # Schema exports
└── ai_outfit.py                     # AI recommendation request/response models
```

### New Router: `/backend/routers/ai_outfit.py`
Three main endpoints for AI-based outfit recommendations.

---

## 3. Service Architecture

### 3.1 Wardrobe Service (`wardrobe_service.py`)

**Purpose**: Fetches user wardrobe items from the database and formats them for VLM consumption.

**Responsibilities**:
- Fetch all user wardrobe items
- Filter by status (clean/dirty)
- Filter by type (shirt, pants, jacket, etc.)
- Filter by temperature range
- Get favorite items
- Format items with complete metadata (images, colors, materials, etc.)

**Key Methods**:
```python
async def get_user_wardrobe(
    user_id: str,
    only_clean: bool = True,
    exclude_item_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]

async def get_items_by_type(user_id: str, item_type: str) -> List[Dict[str, Any]]

async def get_favorite_items(user_id: str) -> List[Dict[str, Any]]

async def get_items_by_temperature_range(
    user_id: str,
    temp_min: float,
    temp_max: float
) -> List[Dict[str, Any]]
```

**Phase 2 Considerations**:
- Will integrate with image preprocessing pipeline
- May cache wardrobe data for performance

---

### 3.2 Weather Service (`weather_service.py`)

**Purpose**: Manages weather data for outfit recommendations.

**Responsibilities**:
- Fetch current weather conditions
- Retrieve weather forecasts
- Cache weather data to reduce API calls
- Format weather data for VLM consumption

**Key Methods**:
```python
async def get_current_weather(
    location: str,
    use_cache: bool = True
) -> Dict[str, Any]

async def get_weather_forecast(
    location: str,
    num_days: int = 5
) -> List[Dict[str, Any]]

async def get_temperature_range_forecast(
    location: str,
    num_days: int = 5
) -> List[Dict[str, float]]
```

**Phase 1 Mock Data**:
- Returns hardcoded weather for testing
- Temperature range: -10°C to 30°C
- Conditions: sunny, cloudy, rainy, snowy, windy, etc.

**Phase 2 Integration**:
- OpenWeatherMap API
- Real-time weather data
- Accurate forecasts by location

---

### 3.3 Usage Service (`usage_service.py`)

**Purpose**: Tracks and computes clothing item usage frequency.

**Responsibilities**:
- Record when items are worn
- Compute usage frequency scores (0.0 to 1.0)
- Identify frequently-worn vs. unused items
- Support historical queries by date range

**Key Methods**:
```python
async def get_item_usage_count(
    user_id: str,
    item_id: str,
    days: Optional[int] = None
) -> int

async def get_user_item_usage_frequency(
    user_id: str,
    days: Optional[int] = 30
) -> Dict[str, float]

async def record_outfit_usage(
    user_id: str,
    item_ids: List[str],
    occasion: Optional[str] = None
) -> bool

async def get_most_used_items(
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]

async def get_unused_items(
    user_id: str,
    days: int = 90
) -> List[Dict[str, Any]]
```

**Phase 1 Implementation**:
- Placeholder methods returning empty/default data
- Ready for integration with `usage_history` database table

**Phase 2 Integration**:
- Track outfit selections in database
- Compute actual usage frequencies
- Use data to bias recommendations toward less-worn items

---

### 3.4 Prompt Service (`prompt_service.py`)

**Purpose**: Builds structured prompts for the VLM.

**Responsibilities**:
- Format wardrobe items as text for VLM consumption
- Include weather context in prompts
- Incorporate user preferences
- Create system prompts for different recommendation types

**Key Methods**:
```python
def build_daily_outfit_prompt(
    wardrobe_items: List[Dict[str, Any]],
    weather_data: Dict[str, Any],
    user_preferences: Optional[Dict[str, Any]] = None,
    occasion: Optional[str] = None
) -> str

def build_travel_outfit_prompt(
    wardrobe_items: List[Dict[str, Any]],
    weather_forecast: List[Dict[str, Any]],
    num_days: int,
    user_preferences: Optional[Dict[str, Any]] = None,
    luggage_limit: int = 10
) -> str

def build_alternative_outfit_prompt(
    current_outfit_items: List[Dict[str, Any]],
    all_wardrobe_items: List[Dict[str, Any]],
    weather_data: Dict[str, Any],
    num_alternatives: int = 3,
    user_preferences: Optional[Dict[str, Any]] = None
) -> str
```

**Prompt Engineering**:
- Clear task description
- Structured data presentation
- Expected response format (JSON)
- Constraints and guidelines

**Example Prompt Structure**:
```
You are an expert fashion stylist...

WARDROBE ITEMS AVAILABLE:
[Item details with ID, name, type, materials, temperature range, etc.]

WEATHER CONDITIONS:
[Temperature, condition, humidity, wind speed]

USER PREFERENCES:
[Style, comfort level, occasion, etc.]

TASK:
[Specific request for outfit recommendation]

RESPONSE FORMAT:
[Expected JSON structure for the VLM to follow]
```

---

### 3.5 VLM Service (`vlm_service.py`)

**Purpose**: Abstract interface for VLM integration with multiple implementations.

**Architecture Pattern**: Strategy Pattern + Abstract Factory

**Base Class: `VLMServiceInterface`**

Defines the contract that all VLM implementations must follow:

```python
class VLMServiceInterface(ABC):
    def recommend_outfit(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None
    ) -> VLMResponse

    def recommend_travel_outfits(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None
    ) -> List[VLMResponse]

    def recommend_alternatives(
        self,
        current_outfit_items: List[Dict[str, Any]],
        all_wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        num_alternatives: int = 3,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None
    ) -> List[VLMResponse]

    def health_check(self) -> bool
```

**Implementations**:

1. **MockVLMService** (Phase 1)
   - Returns placeholder recommendations
   - Used for testing and frontend development
   - Always available for testing
   
2. **LLaVAService** (Phase 2)
   - Actual LLaVA integration
   - Processes images and text
   - Analyzes wardrobe items visually
   - Generates intelligent recommendations

**Why This Design?**

- **Swappable**: Easily replace Mock with LLaVA or other VLMs
- **Testable**: Mock implementation for unit tests
- **Extensible**: Add GPT-4V, Claude Vision, or other models
- **Consistent**: All VLMs follow the same interface

---

### 3.6 Response Parser Service (`response_parser.py`)

**Purpose**: Parses and normalizes VLM outputs into consistent formats.

**Responsibilities**:
- Extract outfit item IDs from VLM responses
- Validate items exist in user's wardrobe
- Analyze weather compatibility
- Format responses for frontend consumption
- Handle malformed or incomplete responses

**Key Methods**:
```python
def parse_outfit_recommendation(
    vlm_response: Dict[str, Any],
    wardrobe: List[Dict[str, Any]],
    weather_context: Dict[str, Any]
) -> Dict[str, Any]

def parse_travel_recommendations(
    vlm_responses: List[Dict[str, Any]],
    wardrobe: List[Dict[str, Any]],
    weather_forecast: List[Dict[str, Any]],
    num_days: int
) -> Dict[str, Any]

def parse_alternative_recommendations(
    vlm_responses: List[Dict[str, Any]],
    current_outfit: List[Dict[str, Any]],
    wardrobe: List[Dict[str, Any]],
    weather_context: Dict[str, Any]
) -> List[Dict[str, Any]]

def parse_json_response(response_text: str) -> Dict[str, Any]
```

**Error Handling**:
- Validates item IDs against wardrobe
- Handles incomplete or malformed responses
- Computes weather compatibility scores
- Falls back to empty/default values when needed

---

### 3.7 Recommendation Service (`recommendation_service.py`)

**Purpose**: Orchestrates the entire recommendation pipeline.

**Responsibilities**:
- Coordinates between all services
- Manages recommendation workflow
- Handles fallback to rule-based recommendations
- Formats final responses

**Architecture Flow**:

```
User Request
    ↓
[Authenticate User]
    ↓
[Fetch Wardrobe] ← WardrobeService
    ↓
[Get Weather] ← WeatherService
    ↓
[Get Usage Frequency] ← UsageService
    ↓
[Build Prompt] ← PromptService
    ↓
[Call VLM] ← VLMService
    ↓
    ├─ Success → [Parse Response] ← ResponseParser
    │               ↓
    │           [Return to User]
    │
    └─ Failure → [Apply Rule-Based Fallback]
                     ↓
                 [Return to User]
```

**Key Methods**:

```python
async def recommend_daily_outfit(
    user_id: str,
    temperature: float,
    weather_condition: str,
    humidity: Optional[float] = None,
    wind_speed: Optional[float] = None,
    occasion: Optional[str] = None,
    preferences: Optional[Dict[str, Any]] = None,
    exclude_items: Optional[List[str]] = None
) -> Dict[str, Any]

async def recommend_travel_outfits(
    user_id: str,
    destination: str,
    start_date: datetime,
    end_date: datetime,
    weather_forecast: Optional[List[Dict[str, Any]]] = None,
    luggage_limit: int = 10,
    preferences: Optional[Dict[str, Any]] = None,
    exclude_items: Optional[List[str]] = None
) -> Dict[str, Any]

async def recommend_alternatives(
    user_id: str,
    current_outfit_item_ids: List[str],
    temperature: float,
    weather_condition: str,
    humidity: Optional[float] = None,
    wind_speed: Optional[float] = None,
    num_alternatives: int = 3,
    preferences: Optional[Dict[str, Any]] = None,
    exclude_items: Optional[List[str]] = None
) -> Dict[str, Any]
```

---

## 4. API Routes

### New Router: `routers/ai_outfit.py`

#### Endpoint 1: Daily Outfit Recommendation

**Route**: `POST /ai-outfit/today`

**Request**:
```json
{
  "weather_data": {
    "temperature": 18,
    "condition": "cloudy",
    "humidity": 65,
    "wind_speed": 12
  },
  "preferences": {
    "style": ["casual"],
    "comfort_level": "high"
  },
  "exclude_items": ["item_id_1", "item_id_2"]
}
```

**Response**:
```json
{
  "success": true,
  "outfit": {
    "items": [...],
    "reasoning": "Selected these items because...",
    "confidence": 0.85,
    "weather_compatibility": {...}
  },
  "model_used": "vlm",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Endpoint 2: Travel Outfit Recommendations

**Route**: `POST /ai-outfit/travel`

**Request**:
```json
{
  "start_date": "2024-03-15",
  "end_date": "2024-03-20",
  "destination": "Paris",
  "luggage_limit": 12,
  "preferences": {
    "style": ["elegant"]
  }
}
```

**Response**:
```json
{
  "success": true,
  "daily_outfits": [
    {
      "day": 1,
      "items": [...],
      "reasoning": "..."
    },
    ...
  ],
  "packing_list": [...],
  "packing_summary": {
    "total_items": 12,
    "notes": "Items can be mixed and matched..."
  },
  "model_used": "vlm",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Endpoint 3: Alternative Outfit Suggestions

**Route**: `POST /ai-outfit/alternative`

**Request**:
```json
{
  "current_outfit_items": ["item_id_1", "item_id_2", "item_id_3"],
  "weather_data": {
    "temperature": 18,
    "condition": "sunny",
    "humidity": 50,
    "wind_speed": 10
  },
  "num_alternatives": 3
}
```

**Response**:
```json
{
  "success": true,
  "primary_outfit": {...},
  "alternative_outfits": [
    {
      "items": [...],
      "reasoning": "...",
      "confidence": 0.8
    },
    ...
  ],
  "model_used": "vlm",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Endpoint 4: Health Check

**Route**: `GET /ai-outfit/health`

**Response**:
```json
{
  "status": "operational",
  "services": {
    "vlm_service": "available",
    "wardrobe_service": "available",
    "weather_service": "available",
    "usage_service": "available",
    "prompt_service": "available",
    "response_parser": "available"
  },
  "recommendation_types": ["daily", "travel", "alternative"],
  "phase": "1"
}
```

---

## 5. Data Models (Schemas)

### Request Models

**Common Base**:
- `weather_temp`: Current temperature (Celsius)
- `weather_condition`: Weather description
- `weather_humidity`: Optional humidity (%)
- `weather_wind_speed`: Optional wind speed (km/h)
- `occasion`: Optional occasion/activity
- `user_preferences`: Optional style preferences
- `excluded_items`: Optional items to exclude

**Specialized Requests**:
- `DailyOutfitRequest`: Single day recommendation
- `TravelOutfitRequest`: Multi-day trip planning
- `AlternativeOutfitRequest`: Alternative suggestions

### Response Models

**Base Outfit Structure**:
```python
class OutfitSuggestion:
    outfit_id: str
    items: List[ClothingItemInfo]
    reasoning: str
    weather_compatibility: dict
    style_score: float
    comfort_score: float
    versatility_score: float
```

**Response Envelopes**:
- `DailyOutfitResponse`: Single outfit + alternatives
- `TravelOutfitResponse`: Multiple daily outfits + packing list
- `AlternativeOutfitResponse`: Multiple alternative suggestions

---

## 6. Fallback System (Rule-Based Recommendations)

When the VLM fails, the system automatically falls back to rule-based recommendations.

### Rule-Based Logic

1. **Temperature Filtering**: Select items suitable for the temperature range
2. **Weather Adaptation**: Include waterproof items if rainy
3. **Favorite Prioritization**: Prefer user's favorite items
4. **Usage Balancing**: Encourage wearing less-used items
5. **Layering**: Suggest appropriate layering for weather

**Example Rules**:
```
IF temperature < 10°C
  THEN require jacket or sweater
  
IF condition = "rainy"
  THEN include waterproof item
  
IF condition = "windy"
  THEN include windproof item

PREFER items with:
  - favorite = true
  - status = "clean"
  - low usage frequency
```

### Phase 2 Enhancement

Replace simple rules with ML-based fallback using:
- Historical outfit patterns
- User behavior analysis
- Seasonal trends
- Style clustering

---

## 7. Database Integration

### Existing Tables Used

- `clothes`: Wardrobe items
- `auth`: User authentication (via Supabase)
- `profiles`: User profile data
- `usage_history` (Phase 2): Track outfit selections

### New Tables (Phase 2)

**Table: `usage_history`**
```sql
CREATE TABLE usage_history (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  item_id UUID REFERENCES clothes(id),
  used_at TIMESTAMP DEFAULT now(),
  occasion VARCHAR(255),
  created_at TIMESTAMP DEFAULT now()
);
```

**Table: `outfit_recommendations` (Optional)**
```sql
CREATE TABLE outfit_recommendations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  outfit_items UUID[] (array of item IDs),
  recommendation_type VARCHAR(50),
  model_used VARCHAR(50),
  feedback_rating INT, -- 1-5 stars
  created_at TIMESTAMP DEFAULT now()
);
```

---

## 8. Dependencies & Requirements

### New Python Packages (Phase 1)

- Already included: `fastapi`, `pydantic`, `supabase-py`, `python-dotenv`

### Phase 2 Dependencies

For LLaVA integration:
- `transformers` - HuggingFace models
- `torch` - PyTorch for model inference
- `pillow` - Image processing
- `numpy` - Numerical operations

Optional:
- `redis` - Caching layer
- `celery` - Background task processing
- `prometheus-client` - Monitoring

---

## 9. Configuration & Environment Variables

### Phase 1 Configuration

No additional environment variables required. Existing configuration:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_KEY`

### Phase 2 Configuration

```bash
# VLM Configuration
LLAVA_API_ENDPOINT=http://localhost:8000
LLAVA_MODEL_NAME=liuhaotian/llava-v1.5-7b
LLAVA_TIMEOUT=30

# Weather API (optional)
OPENWEATHERMAP_API_KEY=xxx
WEATHER_API_PROVIDER=openweathermap

# Cache Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL_MINUTES=30

# Feature Flags
ENABLE_VLM_RECOMMENDATIONS=true
ENABLE_RULE_BASED_FALLBACK=true
DEBUG_VLM_REQUESTS=false
```

---

## 10. Testing Strategy

### Phase 1 Testing

1. **Unit Tests**: Test each service independently with mocks
2. **Integration Tests**: Test service chains (e.g., Wardrobe → Prompt → VLM)
3. **Route Tests**: Test API endpoints with mock data
4. **Mock Data**: Use `MockVLMService` for consistent testing

### Phase 2 Testing

1. **VLM Response Tests**: Verify LLaVA outputs are properly parsed
2. **Image Processing Tests**: Test wardrobe image handling
3. **Performance Tests**: Benchmark VLM inference time
4. **User Acceptance Tests**: Real users test recommendations

---

## 11. Performance Considerations

### Phase 1

- **Latency**: Mock VLM responds instantly (~50ms)
- **Throughput**: No limitations in Phase 1
- **Caching**: Weather service caches data for 30 minutes

### Phase 2 Optimization

1. **Model Inference**:
   - Cache wardrobe embeddings for faster matching
   - Use quantized models for faster inference
   - GPU acceleration if available

2. **API Caching**:
   - Cache wardrobe data (TTL: 1 hour)
   - Cache weather data (TTL: 30 minutes)
   - Cache VLM responses (TTL: 2 hours)

3. **Async Processing**:
   - Use Celery for background VLM calls
   - Return cached results while computing new ones
   - Batch process multiple users

4. **Database Optimization**:
   - Index on `user_id` in clothes table
   - Index on `user_id, status` for quick filtering
   - Materialized views for usage statistics

---

## 12. Security Considerations

### Phase 1

- Authentication via Supabase JWT
- Authorization checks on all endpoints
- Input validation via Pydantic schemas
- No sensitive data in logs

### Phase 2

- Rate limiting on VLM endpoints
- VLM request/response logging (audit trail)
- Image storage security (encrypted, access-controlled)
- API key management for external services
- CORS configuration for frontend domain

---

## 13. Monitoring & Logging

### Phase 1

Basic logging:
```python
print(f"Error in recommendation service: {e}")
```

### Phase 2

Production logging:
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Metrics: request latency, error rates, VLM inference time
- Tracing: Request IDs, service chains
- Tools: Prometheus, ELK Stack, or Datadog

---

## 14. Migration Path: Rule-Based to AI-Powered

### Current State (Before Phase 1)

```
User Request → Rule-Based Logic → Recommendation
```

### Phase 1 (This Deliverable)

```
User Request → VLM Service (Mock) → Recommendation
              ↘ Fallback to Rule-Based (Optional)
```

### Phase 2 (Future)

```
User Request → VLM Service (LLaVA) → Parse → Recommendation
              ↘ Usage History ↙
              ↘ Rule-Based Fallback (if VLM fails)
```

### Phase 3+ (Advanced)

```
User Request → Ensemble:
              ├─ VLM (LLaVA)
              ├─ ML Model (trained on user history)
              ├─ Rule-Based System
              └─ Collaborative Filtering
              → Aggregate Scores → Recommendation
```

---

## 15. What's Included (Phase 1)

✅ **Implemented**:
- Service layer architecture with clear separation of concerns
- VLM interface with Mock implementation
- Weather, wardrobe, usage, and prompt services
- Response parser for normalizing outputs
- Recommendation orchestrator service
- Three new API endpoints
- Request/response schemas
- Basic error handling and fallback logic
- Health check endpoint
- Comprehensive documentation

⏳ **Not Yet Implemented** (Phase 2+):
- Actual LLaVA integration
- Real VLM model inference
- Image processing pipeline
- Usage history tracking
- Advanced prompt engineering
- Performance optimization
- Production monitoring
- User feedback collection

---

## 16. What Remains for Phase 2

### Critical Path

1. **LLaVA Model Setup**
   - Choose deployment method (local, API, cloud)
   - Set up model serving (vLLM, TensorRT, etc.)
   - Implement actual `LLaVAService.recommend_outfit()`

2. **Image Processing**
   - Fetch images from Supabase storage
   - Resize/normalize for VLM consumption
   - Create image embeddings

3. **Prompt Engineering**
   - Refine prompts based on VLM feedback
   - Test different prompt templates
   - Optimize for better recommendations

4. **Testing & Validation**
   - Collect user feedback
   - A/B test VLM vs rule-based
   - Iterate on recommendations

5. **Performance & Scale**
   - Load testing
   - Latency optimization
   - Multi-GPU support

---

## 17. How to Extend in Phase 2

### Adding a New VLM Provider

1. Create a new service class inheriting from `VLMServiceInterface`:

```python
class GPT4VService(VLMServiceInterface):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(VLMProviderEnum.GPT4V, config)
    
    def recommend_outfit(self, wardrobe_items, weather_context, ...):
        # Call OpenAI GPT-4V API
        # Return VLMResponse
        pass
```

2. Update `main.py` to use the new service:

```python
if VLM_PROVIDER == "gpt4v":
    vlm_service = GPT4VService(config)
elif VLM_PROVIDER == "llava":
    vlm_service = LLaVAService(config)
else:
    vlm_service = MockVLMService()

recommendation_service = RecommendationService(vlm_service=vlm_service)
```

3. Test with the new provider without changing any other code

---

## 18. Summary

This Phase 1 implementation provides:

1. **Clean Architecture**: Modular, testable, extensible design
2. **VLM-Agnostic**: Easy to swap different VLM providers
3. **Functional Pipeline**: Complete recommendation workflow
4. **Fallback Safety**: Rule-based recommendations as backup
5. **API-Ready**: Three new endpoints for outfit recommendations
6. **Well-Documented**: Clear structure for Phase 2 implementation

The system is ready for LLaVA integration in Phase 2 while remaining fully functional with the mock service in Phase 1.

---

## 19. Quick Start (Phase 1)

### Installation

```bash
cd backend
pip install -r requirements.txt  # No new packages required
```

### Running the Server

```bash
uvicorn main:app --reload
```

### Testing the AI Endpoints

```bash
# Daily outfit recommendation
curl -X POST http://localhost:8000/ai-outfit/today \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "weather_data": {
      "temperature": 18,
      "condition": "cloudy",
      "humidity": 65,
      "wind_speed": 12
    }
  }'

# Health check
curl http://localhost:8000/ai-outfit/health
```

### Next Steps

1. Test with the frontend (React app)
2. Gather feedback on recommendations
3. Design LLaVA integration for Phase 2
4. Begin Phase 2 implementation