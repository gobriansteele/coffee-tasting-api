# Neo4j-Only Implementation Plan

## Overview

Simplify the coffee-tasting-api from a dual-database architecture (Postgres + Neo4j) to Neo4j-only. This reduces complexity, eliminates sync drift, and aligns the data model with the relationship-centric use cases.

## Target Data Model

### Nodes

| Node | Properties |
|------|------------|
| `CoffeeDrinker` | id (auth user id), email, name |
| `Roaster` | id, name, location, website, description, created_at |
| `Coffee` | id, name, origin_country, origin_region, processing_method, variety, roast_level, description, created_at |
| `Flavor` | id, name, category |
| `Tasting` | id, brew_method, grind_size, water_amount, water_temp, brew_time, notes, created_at |
| `Rating` | id, score (1-5), would_buy_again, notes, created_at |

### Relationships

```
(Roaster)-[:ROASTS]->(Coffee)
(Coffee)-[:HAS_FLAVOR]->(Flavor)
(CoffeeDrinker)-[:LOGGED]->(Tasting)
(Tasting)-[:OF]->(Coffee)
(Tasting)-[:DETECTED {intensity: 1-10}]->(Flavor)
(Tasting)-[:HAS]->(Rating)
```

### Ownership/Audit

```
(CoffeeDrinker)-[:CREATED]->(Roaster)
(CoffeeDrinker)-[:CREATED]->(Coffee)
```

---

## Phase 1: Remove Postgres Infrastructure

### Files to Delete

```
# SQLAlchemy models
app/models/base.py
app/models/coffee.py
app/models/tasting.py
app/models/__init__.py

# SQL repositories
app/repositories/sql/base.py
app/repositories/sql/coffee.py
app/repositories/sql/roaster.py
app/repositories/sql/flavor_tag.py
app/repositories/sql/tasting.py
app/repositories/sql/__init__.py

# Postgres database connection
app/db/database.py

# Database dependency
app/api/deps/database.py

# Alembic migrations (entire directory)
alembic/
alembic.ini

# Background sync tasks (no longer needed)
app/tasks/graph_sync.py
app/tasks/__init__.py

# Embedding services (evaluate if still needed)
app/services/embeddings.py
app/services/embedding_trueup.py
```

### Files to Update

```
# Remove postgres dependencies
pyproject.toml          # Remove: sqlalchemy, asyncpg, alembic, psycopg2-binary
docker-compose.yml      # Remove: postgres service
.env.example            # Remove: DATABASE_URL
app/core/config.py      # Remove: database_url setting
app/main.py             # Remove: postgres startup/shutdown
```

---

## Phase 2: New Neo4j Repository Layer

### New Repository Structure

```
app/repositories/
├── __init__.py
├── base.py              # Neo4j session management
├── coffee_drinker.py    # User/CoffeeDrinker operations
├── roaster.py           # Roaster CRUD
├── coffee.py            # Coffee CRUD + flavor relationships
├── flavor.py            # Flavor CRUD
├── tasting.py           # Tasting + Rating + detected flavors
└── recommendations.py   # Similarity queries for use cases
```

### Key Repository Methods

**RoasterRepository**
- `create(user_id, data)` - Create roaster + CREATED relationship
- `get_by_id(user_id, roaster_id)` - Get roaster owned by user
- `list_all(user_id)` - List user's roasters
- `update(user_id, roaster_id, data)` - Update roaster
- `delete(user_id, roaster_id)` - Delete roaster (DETACH DELETE)

**CoffeeRepository**
- `create(user_id, data)` - Create coffee + link to roaster + flavors
- `get_by_id(user_id, coffee_id)` - Get with roaster and flavors
- `list_all(user_id, filters)` - List with optional roaster filter
- `update(user_id, coffee_id, data)` - Update coffee + flavor links
- `delete(user_id, coffee_id)` - Delete coffee

**FlavorRepository**
- `get_or_create(name, category)` - Idempotent flavor creation
- `list_all()` - All available flavors
- `search(query)` - Search flavors by name

**TastingRepository**
- `create(user_id, coffee_id, tasting_data, rating_data, detected_flavors)` - Full tasting creation
- `get_by_id(user_id, tasting_id)` - Get with coffee, rating, detected flavors
- `list_for_user(user_id)` - All user's tastings
- `list_for_coffee(user_id, coffee_id)` - Tastings of specific coffee
- `delete(user_id, tasting_id)` - Delete tasting + rating

**RecommendationRepository**
- `similar_coffees(coffee_id, limit)` - Coffees with shared flavors
- `coffees_by_flavor(user_id, flavor_ids, exclude_tasted)` - Find coffees by flavor, optionally exclude tried
- `user_flavor_profile(user_id)` - Aggregate of user's detected flavors

---

## Phase 3: Update Pydantic Schemas

### New Schema Structure

```
app/schemas/
├── __init__.py
├── coffee_drinker.py    # User representation
├── roaster.py           # Roaster create/update/response
├── coffee.py            # Coffee create/update/response
├── flavor.py            # Flavor schemas
├── tasting.py           # Tasting + Rating + detected flavors
└── recommendations.py   # Recommendation responses
```

### Key Schema Changes

**TastingCreate** - Single request creates tasting + rating + detected flavors:
```python
class TastingCreate(BaseModel):
    coffee_id: str

    # Brew parameters
    brew_method: BrewMethod
    grind_size: GrindSize | None = None
    water_amount: float | None = None
    water_temp: float | None = None
    brew_time: int | None = None  # seconds
    notes: str | None = None

    # Rating (creates Rating node)
    rating: RatingCreate

    # Detected flavors (creates DETECTED relationships)
    detected_flavors: list[DetectedFlavorCreate] = []

class RatingCreate(BaseModel):
    score: int  # 1-5
    would_buy_again: bool
    notes: str | None = None

class DetectedFlavorCreate(BaseModel):
    flavor_id: str
    intensity: int  # 1-10
```

---

## Phase 4: Update API Endpoints

### Full Endpoint List

#### Roasters
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/roasters` | Create a roaster |
| `GET` | `/roasters` | List user's roasters |
| `GET` | `/roasters/{id}` | Get roaster by ID |
| `PATCH` | `/roasters/{id}` | Update a roaster |
| `DELETE` | `/roasters/{id}` | Delete a roaster |

#### Coffees
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/coffees` | Create a coffee (links to roaster, sets expected flavors) |
| `GET` | `/coffees` | List user's coffees |
| `GET` | `/coffees/{id}` | Get coffee by ID (includes roaster, flavors) |
| `PATCH` | `/coffees/{id}` | Update a coffee |
| `DELETE` | `/coffees/{id}` | Delete a coffee |

#### Flavors
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/flavors` | Create a flavor |
| `GET` | `/flavors` | List all flavors (optionally filter by category) |
| `GET` | `/flavors/{id}` | Get flavor by ID |

#### Tastings
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tastings` | Create a tasting for a coffee (with detected flavors) |
| `GET` | `/tastings` | List user's tastings |
| `GET` | `/tastings/{id}` | Get tasting by ID (includes coffee, detected flavors, rating) |
| `PATCH` | `/tastings/{id}` | Update a tasting |
| `DELETE` | `/tastings/{id}` | Delete a tasting |

#### Ratings
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tastings/{tasting_id}/rating` | Create rating for a tasting |
| `GET` | `/tastings/{tasting_id}/rating` | Get rating for a tasting |
| `PATCH` | `/tastings/{tasting_id}/rating` | Update rating |
| `DELETE` | `/tastings/{tasting_id}/rating` | Delete rating |

#### Recommendations
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recommendations/similar/{coffee_id}` | Coffees with similar flavor profiles |
| `GET` | `/recommendations/by-flavor` | Coffees matching flavors (`?flavor_ids=x,y&exclude_tasted=true`) |

#### User Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/me` | Current user info |
| `GET` | `/me/flavor-profile` | User's detected flavor tendencies |

### Endpoint Changes from Current API

**Remove:**
- `POST /admin/graph/sync` - No longer needed
- `GET /admin/embeddings/status` - Remove or keep if embeddings stay
- `POST /admin/embeddings/trueup` - Remove or keep if embeddings stay

**Update:**
- All endpoints now use Neo4j repositories directly
- Remove `BackgroundTasks` dependency from all endpoints
- Simplify response models (no more dual-source data)

### Example Endpoint Flow

**POST /tastings** (simplified):
```python
@router.post("/", response_model=TastingResponse)
async def create_tasting(
    data: TastingCreate,
    user_id: str = Depends(get_current_user),
    repo: TastingRepository = Depends(get_tasting_repo),
):
    # Single transaction: creates Tasting + Rating + DETECTED relationships
    return await repo.create(
        user_id=user_id,
        coffee_id=data.coffee_id,
        tasting_data=data,
        rating_data=data.rating,
        detected_flavors=data.detected_flavors,
    )
```

---

## Phase 5: Neo4j Schema Setup

### Constraints (run once on startup or via script)

```cypher
// Unique constraints
CREATE CONSTRAINT coffee_drinker_id IF NOT EXISTS FOR (u:CoffeeDrinker) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT roaster_id IF NOT EXISTS FOR (r:Roaster) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT coffee_id IF NOT EXISTS FOR (c:Coffee) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT flavor_id IF NOT EXISTS FOR (f:Flavor) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT flavor_name IF NOT EXISTS FOR (f:Flavor) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT tasting_id IF NOT EXISTS FOR (t:Tasting) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT rating_id IF NOT EXISTS FOR (r:Rating) REQUIRE r.id IS UNIQUE;

// Indexes for common queries
CREATE INDEX coffee_origin IF NOT EXISTS FOR (c:Coffee) ON (c.origin_country);
CREATE INDEX coffee_roast IF NOT EXISTS FOR (c:Coffee) ON (c.roast_level);
CREATE INDEX flavor_category IF NOT EXISTS FOR (f:Flavor) ON (f.category);
```

---

## Phase 6: Frontend Updates (Separate Repo)

### API Changes Frontend Needs to Handle

1. **Tasting creation is now a single call** - Send tasting + rating + detected flavors together
2. **Response shapes may change** - Update TypeScript types
3. **New recommendation endpoints** - Add UI for similar coffees, flavor search

### New Frontend Features

1. **Add Coffee Flow**
   - Select or create roaster
   - Enter coffee details
   - Select expected flavor profile (HAS_FLAVOR)

2. **Tasting Flow**
   - Select coffee to taste
   - Enter brew parameters
   - Rate the tasting (score, would_buy_again)
   - Select detected flavors with intensity sliders

3. **Discovery Flow**
   - View similar coffees based on flavor profiles
   - Search by flavor, filter out already-tried coffees
   - See personal flavor profile (what flavors you detect most)

---

## Implementation Order

### Iteration 1: Core Infrastructure
- [ ] Remove Postgres files and dependencies
- [ ] Update config to remove database_url
- [ ] Create Neo4j constraint setup script
- [ ] Implement base Neo4j repository

### Iteration 2: Roaster & Flavor
- [ ] FlavorRepository + schemas + endpoints
- [ ] RoasterRepository + schemas + endpoints
- [ ] Seed common flavors (fruity, nutty, chocolate, etc.)

### Iteration 3: Coffee
- [ ] CoffeeRepository with roaster + flavor relationships
- [ ] Coffee schemas + endpoints
- [ ] Test coffee CRUD with flavors

### Iteration 4: Tasting & Rating
- [ ] TastingRepository with full transaction (tasting + rating + detected)
- [ ] Tasting schemas + endpoints
- [ ] Test complete tasting flow

### Iteration 5: Recommendations
- [ ] RecommendationRepository with similarity queries
- [ ] Recommendation endpoints
- [ ] Test use cases end-to-end

### Iteration 6: Cleanup & Frontend
- [ ] Remove any remaining dead code
- [ ] Update README and documentation
- [ ] Frontend updates (separate repo)

---

## Files Changed Summary

### Deleted (~20 files)
- `app/models/*` (4 files)
- `app/repositories/sql/*` (6 files)
- `app/db/database.py`
- `app/api/deps/database.py`
- `app/tasks/*` (2 files)
- `app/services/*` (2 files)
- `alembic/*` (all)

### New (~10 files)
- `app/repositories/base.py` (new Neo4j base)
- `app/repositories/coffee_drinker.py`
- `app/repositories/roaster.py`
- `app/repositories/coffee.py`
- `app/repositories/flavor.py`
- `app/repositories/tasting.py`
- `app/repositories/recommendations.py`
- `app/schemas/recommendations.py`
- `app/api/v1/endpoints/recommendations.py`
- `scripts/setup_neo4j_constraints.py`

### Modified (~10 files)
- `pyproject.toml`
- `docker-compose.yml`
- `.env.example`
- `app/core/config.py`
- `app/main.py`
- `app/schemas/*.py`
- `app/api/v1/endpoints/*.py`
- `app/api/v1/api.py`

---

## Risk Considerations

1. **No migration path** - This is a clean rebuild, existing data won't transfer (acceptable for personal project)
2. **Neo4j learning curve** - Cypher queries are different from SQL
3. **Transaction handling** - Neo4j transactions work differently; ensure proper session management
4. **Testing** - Need to set up Neo4j test fixtures

---

## Questions to Resolve

1. **Keep embeddings?** - Vector search for semantic flavor similarity could be valuable. Decide whether to keep OpenAI integration.
2. **Flavor seeding** - Pre-populate common coffee flavors or let users create all?
3. **Multi-tenancy** - Current model uses `created_by`. New model uses `CREATED` relationship. Same effect, confirm this is desired.
