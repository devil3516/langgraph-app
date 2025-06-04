from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional, TypedDict, Any, Dict
import json
import re
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage


class UserInput(TypedDict):
    destination: str
    start_date: str
    end_date: str
    budget: Any
    travel_style: str
    interests: List[str]
    accommodation_preference: str
    transportation_preference: str
    dietary_restrictions: Optional[List[str]]
    special_requirements: Optional[str]


class AgentState(TypedDict, total=False):
    user_input: UserInput
    destination: str
    start_date: datetime
    end_date: datetime
    budget: float
    travel_style: str
    interests: List[str]
    accommodation_preference: str
    transportation_preference: str
    dietary_restrictions: Optional[List[str]]
    special_requirements: Optional[str]
    error: Optional[str]
    destination_insights: Optional[Dict[str, Any]]
    personalized_recommendations: Optional[Dict[str, Any]]


@dataclass
class TripPreferences:
    destination: str
    start_date: datetime
    end_date: datetime
    budget: float
    travel_style: str
    interests: List[str]
    accommodation_preference: str
    transportation_preference: str
    dietary_restrictions: Optional[List[str]] = None
    special_requirements: Optional[str] = None
    destination_insights: Optional[Dict[str, Any]] = None
    personalized_recommendations: Optional[Dict[str, Any]] = None


class LLMTripPreferencesParser:
    def __init__(self, llm_client: ChatGroq):
        self.llm_client = llm_client
    
    def parse_natural_language_input(self, user_text: str) -> Dict[str, Any]:
        """Parse natural language input into structured preferences using LLM"""
        
        system_prompt = """You are a travel planning expert. Parse the user's natural language input into structured travel preferences.

Extract the following information and return as JSON:
{
    "destination": "city/country name",
    "start_date": "YYYY-MM-DD (if mentioned, otherwise null)",
    "end_date": "YYYY-MM-DD (if mentioned, otherwise null)",
    "budget": "number (if mentioned, otherwise null)",
    "travel_style": "budget/moderate/luxury (infer from context)",
    "interests": ["list of interests inferred from description"],
    "accommodation_preference": "hotel/hostel/apartment/resort (infer from context)",
    "transportation_preference": "public/private/mixed (infer from context)",
    "dietary_restrictions": ["list if mentioned"],
    "special_requirements": "any special needs mentioned",
    "trip_duration_days": "number of days (calculate if dates given)"
}

If information is not explicitly mentioned, make reasonable inferences based on context clues.
Return only the JSON object, no additional text.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User input: {user_text}")
        ]
        
        response = self.llm_client.invoke(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback: extract JSON from response if wrapped in other text
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("Could not parse LLM response as JSON")
    
    def get_destination_insights(self, destination: str, interests: List[str]) -> Dict[str, Any]:
        """Get LLM-powered insights about the destination"""
        
        system_prompt = f"""You are a knowledgeable travel expert. Provide detailed insights about {destination} for a traveler interested in {', '.join(interests)}.

Return information as JSON with these keys:
{{
    "best_time_to_visit": "seasonal recommendations",
    "weather_overview": "what to expect weather-wise",
    "cultural_highlights": ["list of cultural aspects to know"],
    "local_customs": ["important customs and etiquette"],
    "must_try_foods": ["local dishes and specialties"],
    "hidden_gems": ["lesser-known attractions"],
    "safety_tips": ["important safety considerations"],
    "transportation_insights": "local transport recommendations",
    "budget_insights": {{
        "budget_range": "typical daily costs for budget/moderate/luxury",
        "money_saving_tips": ["cost-saving suggestions"],
        "expensive_items": ["what typically costs more"]
    }},
    "packing_suggestions": ["what to pack specifically for this destination"]
}}

Provide specific, actionable information based on the destination and interests.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Destination: {destination}, Interests: {', '.join(interests)}")
        ]
        
        response = self.llm_client.invoke(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not parse destination insights"}
    
    def generate_personalized_recommendations(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized recommendations based on user preferences"""
        
        system_prompt = """Based on the user's travel preferences, generate personalized recommendations.

Return JSON with these recommendations:
{
    "accommodation_recommendations": {
        "primary_suggestion": "detailed recommendation with reasoning",
        "alternatives": ["2-3 alternative options with brief explanations"],
        "areas_to_stay": ["recommended neighborhoods/areas"],
        "booking_tips": ["tips for getting better deals"]
    },
    "activity_recommendations": {
        "must_do": ["top activities based on interests"],
        "day_trip_ideas": ["possible day trips from the destination"],
        "evening_activities": ["nightlife/evening recommendations"],
        "unique_experiences": ["special experiences only available here"]
    },
    "dining_recommendations": {
        "restaurant_types": ["types of restaurants to try"],
        "food_experiences": ["cooking classes, food tours, etc."],
        "dietary_accommodations": "how to handle dietary restrictions locally"
    },
    "transportation_recommendations": {
        "getting_around": "best ways to move within the city",
        "day_pass_options": "transit passes or cards to consider",
        "alternative_transport": ["unique transport options like tuk-tuks, etc."]
    },
    "itinerary_structure": {
        "suggested_pace": "recommended daily activity level",
        "rest_day_suggestions": "when to take it easy",
        "flexibility_tips": "how to stay flexible with plans"
    }
}

Base recommendations on the user's travel style, interests, budget, and any special requirements.
"""
        
        prefs_summary = f"""
Destination: {preferences.get('destination')}
Travel Style: {preferences.get('travel_style')}
Budget: ${preferences.get('budget')}
Interests: {', '.join(preferences.get('interests', []))}
Duration: {preferences.get('trip_duration_days', 'unknown')} days
Dietary Restrictions: {', '.join(preferences.get('dietary_restrictions', []))}
Special Requirements: {preferences.get('special_requirements', 'none')}
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prefs_summary)
        ]
        
        response = self.llm_client.invoke(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not parse personalized recommendations"}


def parse_date(date_str: str) -> datetime:
    """Parse date string into datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format")


def validate_budget(budget: float) -> bool:
    """Validate if budget is a positive number."""
    return budget > 0


def parse_trip_preferences_with_llm(state: AgentState, llm_client: ChatGroq) -> AgentState:
    """
    Enhanced trip preferences parser with LLM integration.
    
    Args:
        state (AgentState): Agent state dictionary containing 'user_input'
        llm_client: LLM client for enhanced parsing
        
    Returns:
        AgentState: Updated state with parsed fields, insights, and recommendations
    """
    try:
        parser = LLMTripPreferencesParser(llm_client)
        user_input = state.get("user_input", {})
        
        # Check if we have a natural language input to parse first
        if "natural_language_input" in user_input:
            parsed_nl = parser.parse_natural_language_input(user_input["natural_language_input"])
            # Merge parsed natural language with structured input
            for key, value in parsed_nl.items():
                if value is not None and key not in user_input:
                    user_input[key] = value
        
        # Standard validation for required fields
        required_fields = [
            "destination", "start_date", "end_date", "budget", 
            "travel_style", "interests", "accommodation_preference", 
            "transportation_preference"
        ]
        
        for field in required_fields:
            if field not in user_input or user_input[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Parse and validate dates
        start_date = parse_date(user_input["start_date"])
        end_date = parse_date(user_input["end_date"])
        if start_date >= end_date:
            raise ValueError("End date must be after start date")
        
        # Validate budget
        try:
            budget = float(user_input["budget"])
            if not validate_budget(budget):
                raise ValueError("Budget must be a positive number")
        except (ValueError, TypeError):
            raise ValueError("Invalid budget value")
        
        # Get LLM-powered insights and recommendations
        destination_insights = parser.get_destination_insights(
            user_input["destination"], 
            user_input["interests"]
        )
        
        preferences_dict = {
            "destination": user_input["destination"],
            "travel_style": user_input["travel_style"],
            "budget": budget,
            "interests": user_input["interests"],
            "trip_duration_days": (end_date - start_date).days,
            "dietary_restrictions": user_input.get("dietary_restrictions"),
            "special_requirements": user_input.get("special_requirements")
        }
        
        personalized_recommendations = parser.generate_personalized_recommendations(preferences_dict)
        
        # Create enhanced TripPreferences object
        trip_prefs = TripPreferences(
            destination=user_input["destination"],
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            travel_style=user_input["travel_style"],
            interests=user_input["interests"],
            accommodation_preference=user_input["accommodation_preference"],
            transportation_preference=user_input["transportation_preference"],
            dietary_restrictions=user_input.get("dietary_restrictions"),
            special_requirements=user_input.get("special_requirements"),
            destination_insights=destination_insights,
            personalized_recommendations=personalized_recommendations
        )
        
        # Update state with parsed data
        state.update(asdict(trip_prefs))
        
        # Remove user_input now that it's parsed
        state.pop("user_input", None)
        
    except Exception as e:
        state["error"] = str(e)
    
    return state


# Backwards compatibility function
def parse_trip_preferences(state: AgentState) -> AgentState:
    """
    Original function for backwards compatibility.
    For enhanced LLM features, use parse_trip_preferences_with_llm instead.
    """
    try:
        user_input = state.get("user_input", {})
        required_fields = [
            "destination", "start_date", "end_date", "budget",
            "travel_style", "interests", "accommodation_preference",
            "transportation_preference"
        ]

        for field in required_fields:
            if field not in user_input:
                raise ValueError(f"Missing required field: {field}")

        # Parse and validate fields
        start_date = parse_date(user_input["start_date"])
        end_date = parse_date(user_input["end_date"])
        if start_date >= end_date:
            raise ValueError("End date must be after start date")

        try:
            budget = float(user_input["budget"])
            if not validate_budget(budget):
                raise ValueError("Budget must be a positive number")
        except (ValueError, TypeError):
            raise ValueError("Invalid budget value")

        # Create TripPreferences object
        trip_prefs = TripPreferences(
            destination=user_input["destination"],
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            travel_style=user_input["travel_style"],
            interests=user_input["interests"],
            accommodation_preference=user_input["accommodation_preference"],
            transportation_preference=user_input["transportation_preference"],
            dietary_restrictions=user_input.get("dietary_restrictions"),
            special_requirements=user_input.get("special_requirements"),
        )

        # Update state with parsed data
        state.update(asdict(trip_prefs))
        state.pop("user_input", None)

    except Exception as e:
        state["error"] = str(e)

    return state