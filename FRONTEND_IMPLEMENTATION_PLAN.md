# Frontend Implementation Plan

## Overview

### Why This Change

The backend is moving from a dual-database architecture (Postgres + Neo4j) to **Neo4j-only**. This simplifies the system and enables better recommendation features.

**What this means for the frontend:**
- Cleaner, more consistent API responses (single data source)
- New recommendation endpoints
- Simplified tasting flow (tasting + rating + detected flavors in fewer steps)
- Same authentication flow (Supabase)

### Goals

1. **Simplify the tasting experience** - Users can log a coffee, taste it, rate it, and note detected flavors with minimal friction
2. **Enable discovery** - Users can find new coffees based on flavor preferences and similarity to coffees they've enjoyed
3. **Track coffee journey** - Users can see their tasting history and flavor tendencies over time

---

## User Journeys

### Journey 1: New User - First Coffee

```
1. User signs up via Supabase
   └── Email/password registration

2. User lands on empty dashboard
   └── Prompt: "Add your first coffee"

3. User creates a roaster (or selects existing)
   └── POST /roasters
   └── Minimum: name

4. User creates a coffee
   └── POST /coffees
   └── Links to roaster
   └── Optionally sets expected flavors (HAS_FLAVOR)

5. User does a tasting
   └── POST /tastings
   └── Selects brew method, grind size
   └── Adds free-form notes

6. User rates the tasting
   └── POST /tastings/{id}/rating
   └── Score (1-5) + optional notes

7. User records detected flavors
   └── Included in tasting or via update
   └── Each flavor has intensity (1-10)

8. Dashboard now shows their first coffee + tasting
```

### Journey 2: Returning User - Log Another Tasting

```
1. User logs in via Supabase

2. User views their coffees
   └── GET /coffees
   └── Sees list with roaster info and flavor profiles

3. User selects a coffee to taste again
   └── GET /coffees/{id}

4. User creates new tasting for that coffee
   └── POST /tastings (coffee_id in body)

5. User rates and notes detected flavors
   └── POST /tastings/{id}/rating

6. User can compare this tasting to previous ones
   └── GET /tastings?coffee_id={id}
```

### Journey 3: Discovery - Find Similar Coffees

```
1. User views a coffee they enjoyed
   └── GET /coffees/{id}

2. User clicks "Find Similar"
   └── GET /recommendations/similar/{coffee_id}
   └── Returns coffees with overlapping flavor profiles

3. User explores results
   └── Can filter by roaster, origin, etc.
```

### Journey 4: Discovery - Search by Flavor

```
1. User browses available flavors
   └── GET /flavors
   └── Grouped by category (fruity, nutty, sweet, etc.)

2. User selects flavors they want to explore
   └── e.g., "blueberry" + "chocolate"

3. User searches for matching coffees
   └── GET /recommendations/by-flavor?flavor_ids=x,y&exclude_tasted=true
   └── Returns coffees they haven't tried with those flavors

4. User adds interesting coffee to try later
   └── Or creates tasting directly
```

### Journey 5: Profile - View Flavor Tendencies

```
1. User navigates to profile
   └── GET /me

2. User views their flavor profile
   └── GET /me/flavor-profile
   └── Aggregated view of flavors they commonly detect
   └── "You frequently taste: chocolate, berry, caramel"

3. User optionally updates profile info
   └── PATCH /me
   └── first_name, last_name, display_name
```

---

## API Reference

### Authentication

All endpoints except `/health` require authentication.

**Header:** `Authorization: Bearer <supabase_jwt>`

**Auth flow unchanged:**
1. User signs up/logs in via Supabase SDK
2. Supabase returns JWT
3. Frontend includes JWT in all API requests
4. Backend validates JWT and auto-creates user node on first request

No frontend changes required for auth.

---

### Roasters

#### Create Roaster
```
POST /roasters

Request:
{
  "name": "Blue Bottle Coffee",        // required
  "location": "Oakland, CA",           // optional
  "website": "https://bluebottle.com", // optional
  "description": "Specialty roaster"   // optional
}

Response:
{
  "id": "uuid",
  "name": "Blue Bottle Coffee",
  "location": "Oakland, CA",
  "website": "https://bluebottle.com",
  "description": "Specialty roaster",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List Roasters
```
GET /roasters

Response:
[
  {
    "id": "uuid",
    "name": "Blue Bottle Coffee",
    "location": "Oakland, CA",
    "website": "https://bluebottle.com",
    "description": "Specialty roaster",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Roaster
```
GET /roasters/{id}

Response: Same as single roaster object
```

#### Update Roaster
```
PATCH /roasters/{id}

Request:
{
  "name": "Updated Name",     // optional
  "location": "New Location", // optional
  "website": "https://...",   // optional
  "description": "..."        // optional
}

Response: Updated roaster object
```

#### Delete Roaster
```
DELETE /roasters/{id}

Response: 204 No Content
```

---

### Coffees

#### Create Coffee
```
POST /coffees

Request:
{
  "name": "Ethiopia Yirgacheffe",                  // required
  "roaster_id": "uuid",                            // required
  "origin_country": "Ethiopia",                    // optional
  "origin_region": "Yirgacheffe",                  // optional
  "processing_method": "washed",                   // optional, enum
  "variety": "heirloom",                           // optional
  "roast_level": "light",                          // optional, enum
  "description": "Bright and floral",              // optional
  "flavor_ids": ["uuid1", "uuid2"]                 // optional, expected flavors
}

Enums:
- processing_method: "washed", "natural", "honey", "anaerobic"
- roast_level: "light", "medium", "medium_dark", "dark"

Response:
{
  "id": "uuid",
  "name": "Ethiopia Yirgacheffe",
  "roaster": {
    "id": "uuid",
    "name": "Blue Bottle Coffee"
  },
  "origin_country": "Ethiopia",
  "origin_region": "Yirgacheffe",
  "processing_method": "washed",
  "variety": "heirloom",
  "roast_level": "light",
  "description": "Bright and floral",
  "flavors": [
    {"id": "uuid1", "name": "blueberry", "category": "fruity"},
    {"id": "uuid2", "name": "jasmine", "category": "floral"}
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List Coffees
```
GET /coffees
GET /coffees?roaster_id={uuid}

Response: Array of coffee objects (with roaster and flavors nested)
```

#### Get Coffee
```
GET /coffees/{id}

Response: Single coffee object with roaster and flavors
```

#### Update Coffee
```
PATCH /coffees/{id}

Request:
{
  "name": "Updated Name",          // optional
  "origin_country": "...",         // optional
  "flavor_ids": ["uuid1", "uuid2"] // optional, replaces existing
}

Response: Updated coffee object
```

#### Delete Coffee
```
DELETE /coffees/{id}

Response: 204 No Content
```

---

### Flavors

#### Create Flavor
```
POST /flavors

Request:
{
  "name": "blueberry",    // required, unique
  "category": "fruity"    // optional
}

Response:
{
  "id": "uuid",
  "name": "blueberry",
  "category": "fruity"
}
```

#### List Flavors
```
GET /flavors
GET /flavors?category=fruity

Response:
[
  {"id": "uuid", "name": "blueberry", "category": "fruity"},
  {"id": "uuid", "name": "strawberry", "category": "fruity"}
]
```

#### Get Flavor
```
GET /flavors/{id}

Response: Single flavor object
```

---

### Tastings

#### Create Tasting
```
POST /tastings

Request:
{
  "coffee_id": "uuid",                    // required
  "brew_method": "pourover",              // optional, enum
  "grind_size": "medium",                 // optional, enum
  "notes": "Bright acidity, clean cup",   // optional
  "detected_flavors": [                   // optional
    {"flavor_id": "uuid1", "intensity": 7},
    {"flavor_id": "uuid2", "intensity": 5}
  ]
}

Enums:
- brew_method: "pourover", "espresso", "french_press", "aeropress", "cold_brew", "drip"
- grind_size: "fine", "medium_fine", "medium", "medium_coarse", "coarse"

Response:
{
  "id": "uuid",
  "coffee": {
    "id": "uuid",
    "name": "Ethiopia Yirgacheffe"
  },
  "brew_method": "pourover",
  "grind_size": "medium",
  "notes": "Bright acidity, clean cup",
  "detected_flavors": [
    {"flavor": {"id": "uuid1", "name": "blueberry"}, "intensity": 7},
    {"flavor": {"id": "uuid2", "name": "citrus"}, "intensity": 5}
  ],
  "rating": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### List Tastings
```
GET /tastings
GET /tastings?coffee_id={uuid}

Response: Array of tasting objects (with coffee, detected_flavors, rating)
```

#### Get Tasting
```
GET /tastings/{id}

Response: Single tasting object with all nested data
```

#### Update Tasting
```
PATCH /tastings/{id}

Request:
{
  "brew_method": "espresso",
  "notes": "Updated notes",
  "detected_flavors": [...]  // replaces existing
}

Response: Updated tasting object
```

#### Delete Tasting
```
DELETE /tastings/{id}

Response: 204 No Content
```

---

### Ratings

#### Create Rating
```
POST /tastings/{tasting_id}/rating

Request:
{
  "score": 4,                        // required, 1-5
  "notes": "Would buy again"         // optional
}

Response:
{
  "id": "uuid",
  "score": 4,
  "notes": "Would buy again",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Get Rating
```
GET /tastings/{tasting_id}/rating

Response: Rating object (or 404 if no rating)
```

#### Update Rating
```
PATCH /tastings/{tasting_id}/rating

Request:
{
  "score": 5,
  "notes": "Even better the second time"
}

Response: Updated rating object
```

#### Delete Rating
```
DELETE /tastings/{tasting_id}/rating

Response: 204 No Content
```

---

### Recommendations

#### Similar Coffees
```
GET /recommendations/similar/{coffee_id}
GET /recommendations/similar/{coffee_id}?limit=10

Response:
{
  "source_coffee": {
    "id": "uuid",
    "name": "Ethiopia Yirgacheffe"
  },
  "similar": [
    {
      "coffee": {
        "id": "uuid",
        "name": "Kenya AA",
        "roaster": {"id": "uuid", "name": "..."}
      },
      "shared_flavors": ["blueberry", "citrus"],
      "similarity_score": 0.85
    }
  ]
}
```

#### Coffees by Flavor
```
GET /recommendations/by-flavor?flavor_ids=uuid1,uuid2&exclude_tasted=true

Query params:
- flavor_ids: comma-separated flavor UUIDs (required)
- exclude_tasted: boolean, exclude coffees user has tasted (default: false)

Response:
{
  "requested_flavors": [
    {"id": "uuid1", "name": "blueberry"},
    {"id": "uuid2", "name": "chocolate"}
  ],
  "coffees": [
    {
      "coffee": {
        "id": "uuid",
        "name": "Colombia Huila",
        "roaster": {"id": "uuid", "name": "..."}
      },
      "matching_flavors": ["blueberry", "chocolate"],
      "match_count": 2
    }
  ]
}
```

---

### User Profile

#### Get Profile
```
GET /me

Response:
{
  "id": "supabase-user-id",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "johndoe"
}
```

#### Update Profile
```
PATCH /me

Request:
{
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "johndoe"
}

Response: Updated profile object
```

#### Get Flavor Profile
```
GET /me/flavor-profile

Response:
{
  "total_tastings": 47,
  "top_flavors": [
    {"flavor": {"id": "uuid", "name": "chocolate"}, "count": 23, "avg_intensity": 6.5},
    {"flavor": {"id": "uuid", "name": "berry"}, "count": 18, "avg_intensity": 7.2},
    {"flavor": {"id": "uuid", "name": "caramel"}, "count": 15, "avg_intensity": 5.8}
  ],
  "flavor_categories": {
    "fruity": 35,
    "sweet": 28,
    "nutty": 12
  }
}
```

---

## UI Components to Build/Update

### New Components

1. **FlavorPicker** - Multi-select for flavors with intensity slider
2. **SimilarCoffeesList** - Display recommendations with similarity scores
3. **FlavorProfile** - Visualization of user's detected flavor tendencies
4. **FlavorSearch** - Search coffees by selecting desired flavors

### Updated Components

1. **TastingForm** - Add detected flavors section with intensity
2. **CoffeeForm** - Add expected flavors selection
3. **CoffeeCard** - Show flavor tags
4. **TastingCard** - Show detected flavors and rating

---

## Migration Notes

### Breaking Changes

1. **Tasting response shape** - Now includes `detected_flavors` array and `rating` object
2. **Coffee response shape** - Now includes `flavors` array (expected flavor profile)

### Removed Endpoints

- `POST /admin/graph/sync` - No longer needed
- `POST /admin/embeddings/trueup` - No longer needed

### New Endpoints

- `GET /recommendations/similar/{coffee_id}`
- `GET /recommendations/by-flavor`
- `GET /me/flavor-profile`
- `PATCH /me`
