# TimeSense Recommendation Engine Build Spec

Claude, rebuild the TimeSense recommendation engine properly.

The current recommendation engine is producing poor results because it is likely relying too much on generic AI prompting instead of a structured decision engine.

Build a deterministic recommendation engine first, then use the LLM only to explain the selected recommendation.

The engine must factor in:

- Current time
- User timezone
- Calendar availability
- Health data
- Notion/tasks
- Current location
- Preferred places
- Nearby places
- Driving distance
- Estimated travel time
- Travel feasibility
- User routines
- User preferences
- Past recommendation feedback

The engine should answer:

> “What is the best thing for the user to do right now?”

Do not build this as a generic chatbot prompt. Build it as a scored recommendation engine.

---

# Critical Requirement: Maps API Skill

The recommendation engine must use a maps API skill/tool for location-aware recommendations.

Use the maps API skill/tool for:

- Geocoding addresses
- Searching nearby places
- Resolving preferred places
- Finding the closest relevant location
- Calculating driving distance
- Calculating estimated travel time
- Checking whether a place is open, if supported
- Determining whether a task or errand fits into the user’s calendar window

Examples:

- Task: “Go to Walmart”
- Task: “Pick up medicine”
- Task: “Stop by the gym”
- Task: “Buy groceries”
- Event: “Dentist appointment at 3 PM”
- Event: “Meeting at office location”
- Reminder: “Pick up dry cleaning”

For any task or event that requires travel, the engine must not guess distance or time. It must use the maps API skill/tool when location data is available.

If the maps API skill/tool is unavailable, failing, or missing required inputs, the engine should skip the location-based recommendation or mark it as low-confidence. It should not confidently recommend location-based actions without travel feasibility.

---

# Core Architecture

The recommendation flow should be:

1. Collect raw context
2. Get current time using a centralized time service
3. Get current location using a centralized location service
4. Normalize raw inputs into a typed `UserContext`
5. Generate candidate actions across multiple domains
6. For location-based candidates, use the maps API skill/tool to resolve places and travel time
7. Score each candidate
8. Apply hard rules and penalties
9. Rank the candidates
10. Select the best recommendation
11. Use the LLM only to generate human-readable text
12. Store user feedback for future scoring adjustments

The LLM must not be the primary decision-maker.

---

# Required Recommendation Domains

The engine must support these domains:

1. Calendar and schedule
2. Task and productivity
3. Health and recovery
4. Location and proximity
5. Routine and habit
6. Planning and reflection
7. Context switching
8. Social and communication
9. Errands and life admin
10. Safety and practical awareness
11. Fallback/no urgent action

---

# Required File Structure

Create or update the recommendation engine with this structure:

```txt
src/recommendation-engine/
  types.ts
  normalizeContext.ts

  services/
    timeService.ts
    locationService.ts
    mapsSkillService.ts
    travelFeasibilityService.ts

  candidate-generators/
    calendarCandidates.ts
    taskCandidates.ts
    healthCandidates.ts
    locationCandidates.ts
    routineCandidates.ts
    planningCandidates.ts
    contextSwitchCandidates.ts
    socialCandidates.ts
    lifeAdminCandidates.ts
    fallbackCandidates.ts

  scoring/
    scoreCandidate.ts
    scoreCalendarFit.ts
    scoreTaskFit.ts
    scoreHealthFit.ts
    scoreLocationFit.ts
    scoreRoutineFit.ts
    penalties.ts

  selection/
    rankCandidates.ts
    selectRecommendation.ts
    notificationPolicy.ts

  llm/
    generateRecommendationText.ts
    fallbackRecommendationText.ts

  feedback/
    feedbackTypes.ts
    applyFeedbackAdjustments.ts

  tests/
    calendar.test.ts
    tasks.test.ts
    health.test.ts
    location.test.ts
    mapsSkill.test.ts
    travelFeasibility.test.ts
    routines.test.ts
    selection.test.ts
```

---

# MVP Action Types

Implement these action types:

```ts
export type ActionType =
  // Calendar and schedule
  | "prepare_for_meeting"
  | "join_meeting"
  | "leave_for_event"
  | "review_upcoming_day"
  | "review_tomorrow"
  | "protect_focus_block"
  | "reschedule_conflict"
  | "fill_calendar_gap"

  // Task and productivity
  | "deep_work"
  | "quick_task"
  | "admin_task"
  | "notion_task"
  | "follow_up_task"
  | "deadline_task"
  | "resume_paused_task"
  | "batch_small_tasks"
  | "defer_low_priority_task"

  // Health and recovery
  | "take_break"
  | "walk"
  | "exercise"
  | "stretch"
  | "hydrate"
  | "eat_meal"
  | "rest"
  | "wind_down"
  | "sleep"
  | "recover_after_poor_sleep"

  // Location and proximity
  | "run_nearby_errand"
  | "stop_at_grocery_store"
  | "stop_at_pharmacy"
  | "stop_at_gym"
  | "pick_up_item"
  | "commute_now"
  | "avoid_trip"
  | "combine_errands"
  | "location_based_reminder"

  // Routine and habit
  | "morning_routine"
  | "evening_routine"
  | "work_start_routine"
  | "work_shutdown_routine"
  | "weekly_review"
  | "habit_check_in"
  | "family_routine"
  | "personal_development"

  // Planning and reflection
  | "plan_day"
  | "prioritize_tasks"
  | "review_goals"
  | "capture_notes"
  | "reflect"
  | "update_notion"
  | "organize_workspace"
  | "clear_inbox"

  // Context switching
  | "transition_to_work"
  | "transition_to_home"
  | "transition_to_meeting"
  | "transition_to_focus"
  | "transition_to_family_time"
  | "transition_to_sleep"

  // Social and communication
  | "reply_to_message"
  | "send_follow_up"
  | "check_in_with_person"
  | "prepare_social_event"
  | "birthday_or_event_reminder"

  // Life admin
  | "pay_bill"
  | "review_finances"
  | "household_task"
  | "maintenance_task"
  | "appointment_task"
  | "document_task"

  // Fallback
  | "continue_current_activity"
  | "no_urgent_action";
```

---

# Core Types

Create all types in:

```txt
src/recommendation-engine/types.ts
```

Do not use `any`.

---

## Time Types

```ts
export type PartOfDay =
  | "early_morning"
  | "morning"
  | "midday"
  | "afternoon"
  | "evening"
  | "night";

export type TimeSnapshot = {
  now: string;
  timezone: string;
  localTime: string;
  dayOfWeek: string;
  partOfDay: PartOfDay;
  isWeekend: boolean;
  isWorkHours: boolean;
};
```

---

## Location Types

```ts
export type Coordinates = {
  latitude: number;
  longitude: number;
};

export type LocationCategory =
  | "home"
  | "work"
  | "gym"
  | "school"
  | "store"
  | "commuting"
  | "errand"
  | "unknown";

export type UserLocationSnapshot = {
  coordinates?: Coordinates;
  locationCategory: LocationCategory;
  isMoving?: boolean;
  lastUpdatedAt: string;
  confidence: number;
};
```

---

## Maps API Skill Types

The app should use a maps API skill/tool through a wrapper service called `mapsSkillService`.

This wrapper lets the engine remain independent of whether the underlying implementation uses Google Maps, Mapbox, Apple Maps, or another provider.

```ts
export type TravelMode = "driving" | "walking" | "transit" | "bicycling";

export type PlaceType =
  | "grocery_store"
  | "pharmacy"
  | "gym"
  | "school"
  | "office"
  | "restaurant"
  | "store"
  | "gas_station"
  | "walmart"
  | "target"
  | "costco"
  | "custom";

export type Place = {
  id: string;
  name: string;
  type: PlaceType;
  address?: string;
  coordinates: Coordinates;
  isPreferred?: boolean;
  source: "user_saved" | "maps_api" | "calendar" | "task";
  openNow?: boolean;
  confidence: number;
};

export type PlaceLookupRequest = {
  query: string;
  placeType?: PlaceType;
  userLocation?: Coordinates;
  preferredPlaces?: Place[];
  preferredOnly?: boolean;
  maxResults?: number;
};

export type TravelEstimateRequest = {
  origin: Coordinates;
  destination: Coordinates;
  mode: TravelMode;
  departureTime?: string;
};

export type TravelEstimate = {
  distanceMeters: number;
  distanceMiles: number;
  durationSeconds: number;
  durationMinutes: number;
  mode: TravelMode;
  source: "maps_api" | "cached" | "fallback";
  confidence: number;
};

export type TravelFeasibility = {
  destinationPlace: Place;
  travelEstimate: TravelEstimate;
  travelTimeToDestinationMinutes: number;
  estimatedOnSiteMinutes: number;
  travelTimeAfterTaskMinutes?: number;
  bufferMinutes: number;
  totalRequiredMinutes: number;
  freeBlockMinutes?: number;
  fitsInCurrentFreeBlock: boolean;
  confidence: number;
};
```

---

## Calendar Types

```ts
export type CalendarEvent = {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
  location?: string;
  coordinates?: Coordinates;
  isOptional?: boolean;
  requiresPrep?: boolean;
  prepMinutes?: number;
  source: "calendar";
};
```

---

## Task Types

Tasks must support location intent.

```ts
export type TaskItem = {
  id: string;
  title: string;
  description?: string;
  source: "notion" | "reminder" | "calendar" | "manual";
  dueDate?: string;
  priority: "low" | "medium" | "high";
  estimatedMinutes?: number;
  status: "not_started" | "in_progress" | "completed";

  locationIntent?: {
    query: string;
    placeType?: PlaceType;
    preferredPlaceId?: string;
    requiresTravel: boolean;
    estimatedOnSiteMinutes?: number;
  };
};
```

Example:

```ts
const task: TaskItem = {
  id: "task_123",
  title: "Go to Walmart",
  source: "notion",
  priority: "medium",
  status: "not_started",
  estimatedMinutes: 45,
  locationIntent: {
    query: "Walmart",
    placeType: "walmart",
    requiresTravel: true,
    estimatedOnSiteMinutes: 25,
  },
};
```

---

## Health Types

```ts
export type HealthContext = {
  sleepHours?: number;
  sleepQuality?: "poor" | "okay" | "good";
  stepsToday?: number;
  stepGoal?: number;
  workoutCompletedToday?: boolean;
  sedentaryMinutes?: number;
  energyEstimate?: "low" | "medium" | "high";
};
```

---

## User Context

```ts
export type UserContext = {
  timestamp: string;
  timezone: string;

  timeContext: TimeSnapshot;

  locationContext?: UserLocationSnapshot;

  calendarContext: {
    currentEvent?: CalendarEvent;
    nextEvent?: CalendarEvent;
    minutesUntilNextEvent?: number;
    freeBlockMinutes?: number;
    hasHardDeadlineToday: boolean;
    meetingDensityToday: "low" | "medium" | "high";
  };

  taskContext: {
    overdueTasks: TaskItem[];
    dueTodayTasks: TaskItem[];
    highPriorityTasks: TaskItem[];
    quickTasks: TaskItem[];
    deepWorkTasks: TaskItem[];
    locationLinkedTasks: TaskItem[];
  };

  travelContext?: {
    nearbyRelevantPlaces: Place[];
    activeTravelEstimates: TravelEstimate[];
  };

  healthContext?: HealthContext;

  userPreferences: {
    workHours?: {
      start: string;
      end: string;
    };
    preferredWorkoutTime?: string;
    avoidDeepWorkAfter?: string;
    notificationFrequency: "low" | "medium" | "high";
    preferredTone: "direct" | "coaching" | "calm";
    preferredPlaces?: Place[];
    defaultTravelMode: TravelMode;
  };
};
```

---

## Reason Codes

```ts
export type ReasonCode =
  // Calendar
  | "NEXT_MEETING_SOON"
  | "MEETING_STARTING_NOW"
  | "ENOUGH_TIME_BEFORE_MEETING"
  | "SHORT_FREE_BLOCK"
  | "LONG_FREE_BLOCK"
  | "CALENDAR_CONFLICT"
  | "EVENT_HAS_LOCATION"
  | "TRAVEL_TIME_REQUIRED"
  | "MEETING_HEAVY_DAY"

  // Tasks
  | "TASK_OVERDUE"
  | "TASK_DUE_TODAY"
  | "HIGH_PRIORITY_TASK"
  | "QUICK_TASK_AVAILABLE"
  | "DEEP_WORK_TASK_AVAILABLE"
  | "TASK_LINKED_TO_LOCATION"
  | "TASK_RECENTLY_STARTED"
  | "MANY_SMALL_TASKS"

  // Health
  | "LOW_ENERGY"
  | "HIGH_ENERGY"
  | "POOR_SLEEP"
  | "GOOD_SLEEP"
  | "LOW_STEP_COUNT"
  | "SEDENTARY_TOO_LONG"
  | "WORKOUT_NOT_COMPLETED"
  | "MEAL_WINDOW"
  | "HYDRATION_REMINDER"
  | "RECOVERY_NEEDED"

  // Location and maps
  | "USER_AT_HOME"
  | "USER_AT_WORK"
  | "USER_NEAR_GYM"
  | "USER_NEAR_GROCERY_STORE"
  | "USER_NEAR_PHARMACY"
  | "USER_NEAR_ERRAND_LOCATION"
  | "USER_COMMUTING"
  | "LOCATION_MATCHES_TASK"
  | "CAN_COMBINE_ERRANDS"
  | "AVOID_UNNECESSARY_TRIP"
  | "PREFERRED_PLACE_FOUND"
  | "CLOSEST_PLACE_FOUND"
  | "DRIVING_TIME_CALCULATED"
  | "TRIP_FITS_FREE_BLOCK"
  | "TRIP_DOES_NOT_FIT_FREE_BLOCK"
  | "PLACE_OPEN_NOW"
  | "PLACE_CLOSED_NOW"
  | "MAPS_API_UNAVAILABLE"
  | "LOCATION_DATA_MISSING"

  // Routine
  | "MORNING_ROUTINE_WINDOW"
  | "EVENING_ROUTINE_WINDOW"
  | "WORK_START_WINDOW"
  | "WORK_SHUTDOWN_WINDOW"
  | "WEEKLY_REVIEW_WINDOW"
  | "HABIT_DUE"

  // Planning
  | "MORNING_PLANNING_WINDOW"
  | "END_OF_DAY"
  | "NO_CLEAR_PRIORITY"
  | "NOTION_NEEDS_UPDATE"
  | "GOALS_REVIEW_DUE"

  // Context switching
  | "ARRIVED_AT_WORK"
  | "ARRIVED_HOME"
  | "LEAVING_HOME"
  | "LEAVING_WORK"
  | "FOCUS_MODE_AVAILABLE"
  | "FAMILY_TIME_WINDOW"

  // Feedback
  | "RECENTLY_DISMISSED_SIMILAR_ACTION"
  | "USER_OFTEN_ACCEPTS_THIS_ACTION"
  | "USER_OFTEN_REJECTS_THIS_ACTION"

  // Fallback
  | "NO_URGENT_ACTION"
  | "LOW_CONFIDENCE_CONTEXT";
```

---

## Candidate Action

```ts
export type CandidateDomain =
  | "calendar"
  | "task"
  | "health"
  | "location"
  | "routine"
  | "planning"
  | "context_switch"
  | "social"
  | "life_admin"
  | "safety"
  | "fallback";

export type CandidateAction = {
  id: string;
  type: ActionType;
  domain: CandidateDomain;

  title: string;
  description: string;
  estimatedMinutes: number;

  urgency: number;
  importance: number;
  contextFit: number;
  timeFit: number;
  energyFit: number;
  locationFit: number;
  routineFit: number;
  userPreferenceFit: number;
  confidence: number;

  requiresLocation?: boolean;
  relevantLocationId?: string;
  distanceMinutes?: number;

  destinationPlace?: Place;
  travelEstimate?: TravelEstimate;
  travelFeasibility?: TravelFeasibility;
  totalRequiredMinutes?: number;
  fitsInCurrentFreeBlock?: boolean;

  requiredEnergy: "low" | "medium" | "high";
  interruptionLevel: "low" | "medium" | "high";

  reasonCodes: ReasonCode[];
  relatedEntityIds?: string[];

  expiresAt?: string;
};
```

---

## Scored Candidate

```ts
export type ScoredCandidateAction = CandidateAction & {
  score: number;
  penaltyScore: number;
};
```

---

## Recommendation Output

```ts
export type Recommendation = {
  id: string;
  timestamp: string;
  title: string;
  message: string;
  actionType: ActionType;
  domain: CandidateDomain;
  confidence: number;
  score: number;
  estimatedMinutes: number;
  urgency: "low" | "medium" | "high";
  reasonCodes: ReasonCode[];
  explanation: string;
  suggestedStartTime?: string;
  expiresAt?: string;
  alternatives: CandidateAction[];
  eligibleForPush: boolean;

  destinationPlace?: Place;
  travelEstimate?: TravelEstimate;
  travelFeasibility?: TravelFeasibility;
};
```

---

# Required Services

## 1. Time Service

Create:

```txt
src/recommendation-engine/services/timeService.ts
```

All current-time logic must go through this service.

Do not scatter `new Date()` calls throughout the recommendation engine.

```ts
export function getTimeSnapshot(timezone: string, now?: Date): TimeSnapshot;
```

Requirements:

- Accept optional `now` parameter for testing.
- Return timezone-aware values.
- Use the user’s configured timezone.
- Support calendar comparison.
- Support free-block calculation.
- Support notification cooldowns.
- Support routine windows.
- Support travel departure timing.

---

## 2. Location Service

Create:

```txt
src/recommendation-engine/services/locationService.ts
```

```ts
export async function getUserLocationSnapshot(): Promise<UserLocationSnapshot>;
```

Requirements:

- Return current coordinates when available.
- Return location category when available.
- Return confidence.
- Handle missing location safely.
- Never crash the recommendation engine when location is unavailable.

---

## 3. Maps Skill Service

Create:

```txt
src/recommendation-engine/services/mapsSkillService.ts
```

This service wraps the maps API skill/tool.

Do not call maps API functionality directly from candidate generators. All maps API skill/tool calls must go through this wrapper.

```ts
export type MapsSkillService = {
  geocodeAddress(address: string): Promise<Coordinates | null>;

  searchNearbyPlaces(request: PlaceLookupRequest): Promise<Place[]>;

  resolveRelevantPlace(request: PlaceLookupRequest): Promise<Place | null>;

  getTravelEstimate(
    request: TravelEstimateRequest,
  ): Promise<TravelEstimate | null>;
};
```

Resolution behavior for `resolveRelevantPlace`:

```txt
1. Check preferred places first.
2. If a preferred matching place exists, return it.
3. If no preferred place exists, use the maps API skill/tool to search nearby.
4. Rank nearby places by:
   - relevance
   - distance
   - open status
   - confidence
5. Return the best place.
```

Example:

```txt
Task: Go to Walmart

Behavior:
1. Check whether the user has a preferred Walmart.
2. If yes, use that Walmart.
3. If no, search for nearby Walmart locations.
4. Select the closest relevant Walmart.
5. Calculate driving time using the maps API skill/tool.
6. Use the result in recommendation scoring.
```

---

## 4. Travel Feasibility Service

Create:

```txt
src/recommendation-engine/services/travelFeasibilityService.ts
```

This service determines whether a location-based recommendation fits into the user’s schedule.

```ts
export type TravelFeasibilityRequest = {
  origin: Coordinates;
  destinationPlace: Place;
  estimatedOnSiteMinutes: number;
  freeBlockMinutes?: number;
  nextRelevantLocation?: Coordinates;
  mode: TravelMode;
  departureTime: string;
  bufferMinutes?: number;
};

export async function calculateTravelFeasibility(
  request: TravelFeasibilityRequest,
): Promise<TravelFeasibility | null>;
```

Use this formula:

```txt
totalRequiredMinutes =
  travelTimeToDestinationMinutes +
  estimatedOnSiteMinutes +
  travelTimeAfterTaskMinutes +
  bufferMinutes
```

Default values:

```txt
bufferMinutes = 10
travelTimeAfterTaskMinutes = 0 unless nextRelevantLocation exists
```

If `totalRequiredMinutes > freeBlockMinutes`, then the recommendation does not fit and should be heavily penalized or rejected.

---

# Candidate Generation Requirements

## Calendar Candidates

Generate candidates for:

- `prepare_for_meeting`
- `join_meeting`
- `leave_for_event`
- `commute_now`
- `review_upcoming_day`
- `review_tomorrow`
- `protect_focus_block`
- `fill_calendar_gap`

For calendar events with physical locations:

1. Resolve event coordinates.
2. Use maps API skill/tool to calculate travel time.
3. Determine whether the user needs to leave now.
4. Generate `leave_for_event` or `commute_now` when appropriate.

---

## Task Candidates

Generate candidates for:

- `deep_work`
- `quick_task`
- `admin_task`
- `notion_task`
- `follow_up_task`
- `deadline_task`
- `resume_paused_task`
- `batch_small_tasks`

For tasks with `locationIntent`, do not handle them as normal tasks only. Pass them into location candidate generation.

---

## Location Candidates

Generate candidates for:

- `run_nearby_errand`
- `stop_at_grocery_store`
- `stop_at_pharmacy`
- `stop_at_gym`
- `pick_up_item`
- `combine_errands`
- `location_based_reminder`

For each task with `locationIntent`:

```txt
1. Get user current location.
2. Resolve preferred place or closest relevant place using mapsSkillService.
3. Calculate driving distance and travel time using mapsSkillService.
4. Calculate travel feasibility using travelFeasibilityService.
5. Compare total required time against free calendar block.
6. Generate candidate only if there is enough reliable information.
7. Attach destinationPlace, travelEstimate, and travelFeasibility to the candidate.
8. Score candidate using urgency, importance, locationFit, timeFit, calendar fit, and confidence.
```

Example:

```txt
Task: Go to Walmart
Current location: user’s current GPS location
Preferred Walmart: exists

Expected:
- Use preferred Walmart.
- Calculate driving time.
- Calculate total trip time.
- Compare against calendar free block.
- Recommend only if feasible.
```

Example:

```txt
Task: Go to Walmart
Preferred Walmart: none

Expected:
- Search nearby Walmart locations using maps API skill/tool.
- Select closest relevant Walmart.
- Calculate driving time.
- Calculate total trip time.
- Recommend only if feasible.
```

---

## Health Candidates

Generate candidates for:

- `take_break`
- `walk`
- `exercise`
- `stretch`
- `hydrate`
- `eat_meal`
- `rest`
- `wind_down`
- `sleep`
- `recover_after_poor_sleep`

If the recommendation involves going somewhere, like the gym, use maps API skill/tool and travel feasibility.

---

## Routine Candidates

Generate candidates for:

- `morning_routine`
- `evening_routine`
- `work_start_routine`
- `work_shutdown_routine`
- `weekly_review`
- `habit_check_in`
- `family_routine`
- `personal_development`

---

## Planning Candidates

Generate candidates for:

- `plan_day`
- `prioritize_tasks`
- `review_goals`
- `capture_notes`
- `reflect`
- `update_notion`
- `organize_workspace`
- `clear_inbox`

---

## Context Switch Candidates

Generate candidates for:

- `transition_to_work`
- `transition_to_home`
- `transition_to_meeting`
- `transition_to_focus`
- `transition_to_family_time`
- `transition_to_sleep`

These should use:

- Current time
- Calendar
- Current location category
- User routine
- Work hours

---

# Scoring Formula

Use this formula:

```ts
finalScore =
  urgencyScore * 0.2 +
  importanceScore * 0.2 +
  contextFitScore * 0.15 +
  timeFitScore * 0.12 +
  energyFitScore * 0.1 +
  locationFitScore * 0.1 +
  routineFitScore * 0.08 +
  userPreferenceScore * 0.05 -
  penaltyScore;
```

Clamp final scores between 0 and 100.

---

# Travel and Maps Scoring Rules

## Preferred Place Rule

If a user has a preferred place matching the task, boost the candidate.

Reason code:

```txt
PREFERRED_PLACE_FOUND
```

Example:

```txt
Task: Go to Walmart
Preferred Walmart exists
Use preferred Walmart even if another Walmart is slightly closer.
```

Exception:

If the preferred place does not fit the schedule but a closer location does, the engine may recommend the closer location.

Example explanation:

```txt
Your usual Walmart is 24 minutes away, but there is another Walmart 8 minutes away. Since you only have 45 minutes before your next event, the closer one fits better.
```

---

## Closest Relevant Place Rule

If no preferred place exists, use the maps API skill/tool to find the closest relevant place.

Reason code:

```txt
CLOSEST_PLACE_FOUND
```

---

## Driving Time Rule

If driving time is calculated successfully, include it in the candidate and recommendation.

Reason code:

```txt
DRIVING_TIME_CALCULATED
```

The recommendation should be able to say things like:

```txt
Walmart is about 9 minutes away, and the full trip should fit before your next event.
```

---

## Calendar Fit Rule

Location-based recommendations should only win if the full trip fits into the user’s available calendar block.

Use:

```txt
totalRequiredMinutes =
  travelTimeToDestinationMinutes +
  estimatedOnSiteMinutes +
  travelTimeAfterTaskMinutes +
  bufferMinutes
```

If it fits:

```txt
TRIP_FITS_FREE_BLOCK
```

If it does not fit:

```txt
TRIP_DOES_NOT_FIT_FREE_BLOCK
```

If it does not fit, apply a heavy penalty or reject the candidate.

---

## Open Business Rule

If open/closed data is available:

- Boost places open now.
- Penalize closed places.
- Do not recommend a closed location unless the task is planning-only.

Reason codes:

```txt
PLACE_OPEN_NOW
PLACE_CLOSED_NOW
```

---

## Leave Now Rule

If an event has a location and travel time plus buffer means the user must leave now, travel recommendations override most other recommendations.

Example:

```txt
Event starts in 35 minutes
Drive time is 25 minutes
Buffer is 10 minutes
Recommendation: Leave now
```

---

## Maps API Failure Rule

If the maps API skill/tool fails:

- Do not crash.
- Do not invent travel time.
- Skip the candidate or mark it low-confidence.
- Add reason code:

```txt
MAPS_API_UNAVAILABLE
```

---

## Missing Location Rule

If user location is missing:

- Skip location-based recommendations or mark them low-confidence.
- Add reason code:

```txt
LOCATION_DATA_MISSING
```

---

# Hard Rules

## Meeting Soon

If the next meeting starts within 15 minutes, recommend either:

- `prepare_for_meeting`
- `join_meeting`

Do not recommend deep work.

---

## Travel Required

If the next event has a physical location and travel time plus buffer means the user should leave now, recommend:

- `leave_for_event`
- or `commute_now`

---

## Short Free Block

If the user has less than 25 minutes available, do not recommend deep work.

Prefer:

- `quick_task`
- `take_break`
- `prepare_for_meeting`
- `review_upcoming_day`

---

## Long Free Block

If the user has 60+ minutes free and a high-priority task exists, recommend:

- `deep_work`
- `protect_focus_block`

---

## Poor Sleep or Low Energy

If sleep is poor or energy is low, reduce deep work recommendations unless there is a hard deadline.

Prefer:

- `recover_after_poor_sleep`
- `take_break`
- `walk`
- `plan_day`
- `prioritize_tasks`

---

## Strong Location Opportunity

If the user is near a relevant location and there is a matching task, boost that recommendation only after confirming travel feasibility.

Examples:

- Near grocery store + grocery task = `stop_at_grocery_store`
- Near pharmacy + pharmacy task = `stop_at_pharmacy`
- Near gym + workout not completed = `stop_at_gym`
- Near errand location + matching task = `run_nearby_errand`

---

## End of Workday

Near the end of workday, prefer:

- `work_shutdown_routine`
- `review_tomorrow`
- `update_notion`
- `clear_inbox`

---

## Night / Wind Down

At night, prefer:

- `wind_down`
- `sleep`
- `transition_to_sleep`

Avoid errands and normal work unless urgent.

---

## No Strong Recommendation

If no candidate has a strong score, return:

- `continue_current_activity`
- or `no_urgent_action`

---

# Notification Policy

Do not notify the user for every recommendation.

Use this rule:

```ts
if (score >= 75 && confidence >= 0.75) {
  eligibleForPush = true;
}

if (score < 75 || confidence < 0.75) {
  eligibleForPush = false;
}
```

Also apply cooldown:

- Default notification cooldown: 45 minutes
- Do not repeat the same recommendation type during cooldown
- Urgent calendar/travel recommendations may override cooldown

---

# Required Functions

Build these core functions:

```ts
normalizeContext(rawInputs: RawContextInputs): UserContext
```

```ts
generateCandidateActions(context: UserContext): Promise<CandidateAction[]>
```

```ts
scoreCandidate(candidate: CandidateAction, context: UserContext): ScoredCandidateAction
```

```ts
rankCandidates(candidates: CandidateAction[], context: UserContext): ScoredCandidateAction[]
```

```ts
selectRecommendation(scoredCandidates: ScoredCandidateAction[], context: UserContext): Recommendation
```

```ts
generateRecommendationText(recommendation: Recommendation, context: UserContext): Promise<LLMRecommendationText>
```

```ts
applyFeedbackAdjustments(candidate: CandidateAction, context: UserContext): number
```

Because maps API calls are asynchronous, candidate generation should support async behavior.

---

# LLM Rules

The LLM should only be used after the deterministic system has selected the recommendation.

The LLM receives:

- Selected recommendation
- Reason codes
- Context summary
- Travel estimate, if relevant
- Destination place, if relevant
- User tone preference

The LLM returns:

```ts
type LLMRecommendationText = {
  notificationTitle: string;
  notificationBody: string;
  explanation: string;
};
```

If the LLM fails, use deterministic fallback text.

The LLM must not:

- Choose a different recommendation
- Invent distances
- Invent travel times
- Invent open/closed status
- Invent calendar conflicts
- Invent user preferences

---

# Required Test Scenarios

Create test cases for at least these scenarios:

1. Meeting starts in 10 minutes
2. Meeting starts now
3. User needs to leave for an event based on maps API travel time
4. User has a 90-minute free block
5. User has only 15 minutes free
6. User has overdue Notion tasks
7. User has many small tasks
8. User has no clear task priority
9. User slept poorly
10. User has low step count
11. User has been sedentary too long
12. User has not worked out and is near the gym
13. User has not worked out and the gym requires driving time
14. User is near grocery store with grocery task open
15. User is near pharmacy with pharmacy task open
16. User can combine two errands nearby
17. User is leaving home and needs to bring an item
18. User arrived at work
19. User arrived home
20. User is near end of workday
21. User is in evening wind-down window
22. User has no calendar events and no urgent tasks
23. User repeatedly dismissed the same recommendation
24. Health data is missing
25. Location data is missing
26. Notion data is missing
27. Calendar data is missing
28. Multiple domains compete for the top recommendation
29. Low-confidence recommendation should not notify
30. High-confidence location recommendation should notify
31. Task says “Go to Walmart” and preferred Walmart exists
32. Task says “Go to Walmart” and no preferred Walmart exists, so closest Walmart is selected
33. Preferred Walmart is farther away but still fits in schedule
34. Preferred Walmart is too far, closer Walmart fits, and engine recommends closer Walmart
35. User is near Walmart, task is open, and calendar has enough time
36. User is near Walmart, but calendar does not have enough time
37. Maps API skill/tool fails
38. Place is closed
39. Place is open
40. Current time changes recommendation behavior
41. Nighttime suppresses errands unless urgent
42. Free block calculation changes after calendar event ends
43. Travel time plus on-site time plus buffer exceeds free block
44. Travel time plus on-site time plus buffer fits free block
45. Event location requires leaving now
46. Event location does not require leaving yet

---

# Acceptance Criteria

The recommendation engine is complete when:

- It generates candidates from multiple domains.
- It scores candidates deterministically.
- It ranks recommendations consistently.
- It handles missing data gracefully.
- It supports calendar, health, location, Notion, routines, and proximity-based recommendations.
- It uses a maps API skill/tool for place search, driving distance, and travel time.
- It does not invent distance or travel time.
- It calculates whether errands fit into calendar free blocks.
- It supports preferred places and closest-place fallback.
- It supports current-time-aware scoring.
- It does not rely on the LLM to choose the recommendation.
- Every recommendation includes reason codes.
- Every recommendation has a confidence score.
- Push notification eligibility is calculated.
- Tests exist for the required scenarios.
- No `any` types are used.
- The engine can be extended with new action types without rewriting the entire system.

---

# Implementation Order

Build in this order:

1. Types
2. Time service
3. Location service
4. Maps skill service wrapper
5. Travel feasibility service
6. Context normalization
7. Candidate generation
8. Scoring
9. Ranking and selection
10. Notification policy
11. Tests
12. LLM explanation layer

Do not start with the LLM layer.
