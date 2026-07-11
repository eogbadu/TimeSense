"""Typed structures for the deterministic recommendation engine.

Python port of recommendation-engine-build-spec.md. No ``Any`` — everything is typed with
dataclasses and ``Literal`` unions so the engine stays explicit and testable. The LLM is never
involved in *choosing* a recommendation; it only explains the already-selected one (later phase).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# --------------------------------------------------------------------------------------
# Enumerated string unions (mirror the spec's TS unions)
# --------------------------------------------------------------------------------------

ActionType = Literal[
    # Calendar and schedule
    "prepare_for_meeting", "join_meeting", "leave_for_event", "review_upcoming_day",
    "review_tomorrow", "protect_focus_block", "reschedule_conflict", "fill_calendar_gap",
    # Task and productivity
    "deep_work", "quick_task", "admin_task", "notion_task", "follow_up_task",
    "deadline_task", "resume_paused_task", "batch_small_tasks", "defer_low_priority_task",
    # Health and recovery
    "take_break", "walk", "exercise", "stretch", "hydrate", "eat_meal", "rest",
    "wind_down", "sleep", "recover_after_poor_sleep",
    # Location and proximity
    "run_nearby_errand", "stop_at_grocery_store", "stop_at_pharmacy", "stop_at_gym",
    "pick_up_item", "commute_now", "avoid_trip", "combine_errands", "location_based_reminder",
    # Routine and habit
    "morning_routine", "evening_routine", "work_start_routine", "work_shutdown_routine",
    "weekly_review", "habit_check_in", "family_routine", "personal_development",
    # Planning and reflection
    "plan_day", "prioritize_tasks", "review_goals", "capture_notes", "reflect",
    "update_notion", "organize_workspace", "clear_inbox",
    # Context switching
    "transition_to_work", "transition_to_home", "transition_to_meeting", "transition_to_focus",
    "transition_to_family_time", "transition_to_sleep",
    # Social and communication
    "reply_to_message", "send_follow_up", "check_in_with_person", "prepare_social_event",
    "birthday_or_event_reminder",
    # Life admin
    "pay_bill", "review_finances", "household_task", "maintenance_task", "appointment_task",
    "document_task",
    # Fallback
    "continue_current_activity", "no_urgent_action",
]

CandidateDomain = Literal[
    "calendar", "task", "health", "location", "routine", "planning",
    "context_switch", "social", "life_admin", "safety", "fallback",
]

PartOfDay = Literal["early_morning", "morning", "midday", "afternoon", "evening", "night"]

LocationCategory = Literal[
    "home", "work", "gym", "school", "store", "commuting", "errand", "unknown",
]

TravelMode = Literal["driving", "walking", "transit", "bicycling"]

PlaceType = Literal[
    "grocery_store", "pharmacy", "gym", "school", "office", "restaurant", "store",
    "gas_station", "walmart", "target", "costco", "custom",
]

Priority = Literal["low", "medium", "high"]
Energy = Literal["low", "medium", "high"]
Level = Literal["low", "medium", "high"]
TaskStatus = Literal["not_started", "in_progress", "completed"]
PlaceSource = Literal["user_saved", "maps_api", "calendar", "task"]
EstimateSource = Literal["maps_api", "cached", "fallback"]

ReasonCode = Literal[
    # Calendar
    "NEXT_MEETING_SOON", "MEETING_STARTING_NOW", "ENOUGH_TIME_BEFORE_MEETING",
    "SHORT_FREE_BLOCK", "LONG_FREE_BLOCK", "CALENDAR_CONFLICT", "EVENT_HAS_LOCATION",
    "TRAVEL_TIME_REQUIRED", "MEETING_HEAVY_DAY",
    # Tasks
    "TASK_OVERDUE", "TASK_DUE_TODAY", "HIGH_PRIORITY_TASK", "QUICK_TASK_AVAILABLE",
    "DEEP_WORK_TASK_AVAILABLE", "TASK_LINKED_TO_LOCATION", "TASK_RECENTLY_STARTED",
    "MANY_SMALL_TASKS",
    # Health
    "LOW_ENERGY", "HIGH_ENERGY", "POOR_SLEEP", "GOOD_SLEEP", "LOW_STEP_COUNT",
    "SEDENTARY_TOO_LONG", "WORKOUT_NOT_COMPLETED", "MEAL_WINDOW", "HYDRATION_REMINDER",
    "RECOVERY_NEEDED",
    # Location and maps
    "USER_AT_HOME", "USER_AT_WORK", "USER_NEAR_GYM", "USER_NEAR_GROCERY_STORE",
    "USER_NEAR_PHARMACY", "USER_NEAR_ERRAND_LOCATION", "USER_COMMUTING",
    "LOCATION_MATCHES_TASK", "CAN_COMBINE_ERRANDS", "AVOID_UNNECESSARY_TRIP",
    "PREFERRED_PLACE_FOUND", "CLOSEST_PLACE_FOUND", "DRIVING_TIME_CALCULATED",
    "TRIP_FITS_FREE_BLOCK", "TRIP_DOES_NOT_FIT_FREE_BLOCK", "PLACE_OPEN_NOW",
    "PLACE_CLOSED_NOW", "MAPS_API_UNAVAILABLE", "LOCATION_DATA_MISSING",
    # Routine
    "MORNING_ROUTINE_WINDOW", "EVENING_ROUTINE_WINDOW", "WORK_START_WINDOW",
    "WORK_SHUTDOWN_WINDOW", "WEEKLY_REVIEW_WINDOW", "HABIT_DUE",
    # Planning
    "MORNING_PLANNING_WINDOW", "END_OF_DAY", "NO_CLEAR_PRIORITY", "NOTION_NEEDS_UPDATE",
    "GOALS_REVIEW_DUE",
    # Context switching
    "ARRIVED_AT_WORK", "ARRIVED_HOME", "LEAVING_HOME", "LEAVING_WORK",
    "FOCUS_MODE_AVAILABLE", "FAMILY_TIME_WINDOW",
    # Feedback
    "RECENTLY_DISMISSED_SIMILAR_ACTION", "USER_OFTEN_ACCEPTS_THIS_ACTION",
    "USER_OFTEN_REJECTS_THIS_ACTION", "RECENTLY_DISAGREED", "AVOIDED_AT_THIS_TIME",
    # Fallback
    "NO_URGENT_ACTION", "LOW_CONFIDENCE_CONTEXT",
]


# --------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeSnapshot:
    now: str                # ISO-8601 UTC
    timezone: str
    local_time: str         # ISO-8601 local
    day_of_week: str
    part_of_day: PartOfDay
    is_weekend: bool
    is_work_hours: bool
    hour: int               # local hour 0-23 (convenience for windows)


# --------------------------------------------------------------------------------------
# Location & maps
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class UserLocationSnapshot:
    location_category: LocationCategory
    last_updated_at: str
    confidence: float
    coordinates: Optional[Coordinates] = None
    is_moving: Optional[bool] = None
    place_name: Optional[str] = None   # our derived place name (Home/Work/…) when known


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    type: PlaceType
    coordinates: Coordinates
    source: PlaceSource
    confidence: float
    address: Optional[str] = None
    is_preferred: Optional[bool] = None
    open_now: Optional[bool] = None


@dataclass(frozen=True)
class PlaceLookupRequest:
    query: str
    place_type: Optional[PlaceType] = None
    user_location: Optional[Coordinates] = None
    preferred_places: list[Place] = field(default_factory=list)
    preferred_only: bool = False
    max_results: int = 5


@dataclass(frozen=True)
class TravelEstimateRequest:
    origin: Coordinates
    destination: Coordinates
    mode: TravelMode
    departure_time: Optional[str] = None


@dataclass(frozen=True)
class TravelEstimate:
    distance_meters: float
    distance_miles: float
    duration_seconds: float
    duration_minutes: float
    mode: TravelMode
    source: EstimateSource
    confidence: float


@dataclass(frozen=True)
class TravelFeasibility:
    destination_place: Place
    travel_estimate: TravelEstimate
    travel_time_to_destination_minutes: float
    estimated_on_site_minutes: float
    buffer_minutes: float
    total_required_minutes: float
    fits_in_current_free_block: bool
    confidence: float
    travel_time_after_task_minutes: Optional[float] = None
    free_block_minutes: Optional[float] = None


# --------------------------------------------------------------------------------------
# Calendar & tasks
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    start_time: str
    end_time: str
    source: Literal["calendar"] = "calendar"
    location: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    is_optional: Optional[bool] = None
    requires_prep: Optional[bool] = None
    prep_minutes: Optional[int] = None


@dataclass(frozen=True)
class LocationIntent:
    query: str
    requires_travel: bool
    place_type: Optional[PlaceType] = None
    preferred_place_id: Optional[str] = None
    estimated_on_site_minutes: Optional[int] = None
    # An exact place the user attached to the task (Capture errand) — used directly instead of
    # searching for a place by the task title.
    coordinates: Optional[Coordinates] = None


@dataclass(frozen=True)
class TaskItem:
    id: str
    title: str
    source: Literal["notion", "reminder", "calendar", "manual"]
    priority: Priority
    status: TaskStatus
    description: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    location_intent: Optional[LocationIntent] = None


# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class HealthContext:
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[Literal["poor", "okay", "good"]] = None
    steps_today: Optional[int] = None
    step_goal: Optional[int] = None
    workout_completed_today: Optional[bool] = None
    sedentary_minutes: Optional[int] = None
    energy_estimate: Optional[Energy] = None


# --------------------------------------------------------------------------------------
# User context (normalized)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkHours:
    start: str   # "HH:MM"
    end: str


@dataclass(frozen=True)
class CalendarContext:
    has_hard_deadline_today: bool
    meeting_density_today: Level
    current_event: Optional[CalendarEvent] = None
    next_event: Optional[CalendarEvent] = None
    minutes_until_next_event: Optional[int] = None
    free_block_minutes: Optional[int] = None


@dataclass(frozen=True)
class TaskContext:
    all_tasks: list[TaskItem] = field(default_factory=list)  # every active (non-completed) task
    overdue_tasks: list[TaskItem] = field(default_factory=list)
    due_today_tasks: list[TaskItem] = field(default_factory=list)
    high_priority_tasks: list[TaskItem] = field(default_factory=list)
    quick_tasks: list[TaskItem] = field(default_factory=list)
    deep_work_tasks: list[TaskItem] = field(default_factory=list)
    location_linked_tasks: list[TaskItem] = field(default_factory=list)


@dataclass(frozen=True)
class TravelContext:
    nearby_relevant_places: list[Place] = field(default_factory=list)
    active_travel_estimates: list[TravelEstimate] = field(default_factory=list)


@dataclass(frozen=True)
class UserPreferences:
    notification_frequency: Level = "medium"
    preferred_tone: Literal["direct", "coaching", "calm"] = "calm"
    default_travel_mode: TravelMode = "driving"
    work_hours: Optional[WorkHours] = None
    preferred_workout_time: Optional[str] = None
    avoid_deep_work_after: Optional[str] = None
    preferred_places: list[Place] = field(default_factory=list)


@dataclass(frozen=True)
class UserContext:
    timestamp: str
    timezone: str
    time_context: TimeSnapshot
    calendar_context: CalendarContext
    task_context: TaskContext
    user_preferences: UserPreferences
    location_context: Optional[UserLocationSnapshot] = None
    travel_context: Optional[TravelContext] = None
    health_context: Optional[HealthContext] = None
    # Task ids (as strings) the user recently "disagreed" with — demoted, not hidden.
    recently_disagreed_task_ids: frozenset = frozenset()


# --------------------------------------------------------------------------------------
# Candidates, scoring, output
# --------------------------------------------------------------------------------------

@dataclass
class CandidateAction:
    id: str
    type: ActionType
    domain: CandidateDomain
    title: str
    description: str
    estimated_minutes: int

    # 0..1 sub-scores
    urgency: float = 0.0
    importance: float = 0.0
    context_fit: float = 0.0
    time_fit: float = 0.0
    energy_fit: float = 0.0
    # Neutral by default: for an action that doesn't depend on location, where you are neither helps
    # nor hurts. Location-dependent candidates (errands) set this explicitly (low until a feasible
    # trip is confirmed, high when it fits).
    location_fit: float = 0.5
    routine_fit: float = 0.0
    user_preference_fit: float = 0.0
    confidence: float = 0.5

    required_energy: Energy = "medium"
    interruption_level: Level = "low"

    reason_codes: list[ReasonCode] = field(default_factory=list)
    related_entity_ids: list[str] = field(default_factory=list)

    requires_location: Optional[bool] = None
    relevant_location_id: Optional[str] = None
    distance_minutes: Optional[float] = None
    destination_place: Optional[Place] = None
    travel_estimate: Optional[TravelEstimate] = None
    travel_feasibility: Optional[TravelFeasibility] = None
    total_required_minutes: Optional[float] = None
    fits_in_current_free_block: Optional[bool] = None
    expires_at: Optional[str] = None


@dataclass
class ScoredCandidateAction:
    candidate: CandidateAction
    score: float
    penalty_score: float


@dataclass
class Recommendation:
    id: str
    timestamp: str
    title: str
    message: str
    action_type: ActionType
    domain: CandidateDomain
    confidence: float
    score: float
    estimated_minutes: int
    urgency: Priority
    reason_codes: list[ReasonCode]
    explanation: str
    alternatives: list[CandidateAction]
    eligible_for_push: bool
    related_entity_ids: list[str] = field(default_factory=list)
    suggested_start_time: Optional[str] = None
    expires_at: Optional[str] = None
    destination_place: Optional[Place] = None
    travel_estimate: Optional[TravelEstimate] = None
    travel_feasibility: Optional[TravelFeasibility] = None


@dataclass(frozen=True)
class LLMRecommendationText:
    notification_title: str
    notification_body: str
    explanation: str
