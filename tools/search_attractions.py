from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import requests
import re
from tools.parse_trip_prefs import TripPreferences
import os
from dotenv import load_dotenv
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


@dataclass
class Attraction:
    name: str
    description: str
    category: str  # e.g., "museum", "landmark", "park", "restaurant"
    rating: Optional[float]
    price_level: Optional[str]  # "$", "$$", "$$$", "$$$$"
    opening_hours: Optional[str]
    address: Optional[str]
    website: Optional[str]
    images: List[str]
    source: str
    popularity_score: Optional[float]  # 0-1 score based on mentions and ratings
    best_time_to_visit: Optional[str]
    visit_duration: Optional[str]  # e.g., "2-3 hours"

class AttractionSearchError(Exception):
    """Custom exception for attraction search errors"""
    pass

class AttractionSearcher:
    def __init__(self, tavily_api_key: Optional[str] = None):
        """
        Initialize the attraction searcher with API credentials
        
        Args:
            tavily_api_key (str, optional): API key for Tavily search
        """
        # Try to get API key from parameter, then environment variable
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        
        # Validate API key
        if not self.tavily_api_key:
            raise ValueError("Tavily API key is required. Please set TAVILY_API_KEY in your .env file or pass it to the constructor.")
        
        if not isinstance(self.tavily_api_key, str) or not self.tavily_api_key.strip():
            raise ValueError("Invalid Tavily API key format. The key must be a non-empty string.")
            
        self.tavily_url = "https://api.tavily.com/search"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.tavily_api_key.strip()}"
        }

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract rating from text using regex"""
        rating_pattern = r'(\d+(?:\.\d)?)\s*\/\s*5'
        match = re.search(rating_pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_price_level(self, text: str) -> Optional[str]:
        """Extract price level from text"""
        price_patterns = {
            r'\$\$+\s*expensive': '$$$$',
            r'\$\$\$\s*expensive': '$$$$',
            r'\$\$\s*moderate': '$$$',
            r'\$\s*cheap': '$$',
            r'free': '$'
        }
        
        for pattern, level in price_patterns.items():
            if re.search(pattern, text.lower()):
                return level
        return None

    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract typical visit duration from text"""
        duration_patterns = [
            r'(\d+)\s*-\s*(\d+)\s*hours?',
            r'(\d+)\s*hours?',
            r'(\d+)\s*-\s*(\d+)\s*days?',
            r'(\d+)\s*days?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if 'day' in pattern:
                    return f"{match.group(1)} days"
                return f"{match.group(1)} hours"
        return None

    def _calculate_popularity_score(self, result: Dict[str, Any]) -> float:
        """Calculate a popularity score based on mentions and ratings"""
        score = 0.0
        
        # Base score from rating if available
        rating = self._extract_rating(result.get("content", ""))
        if rating:
            score += rating / 5.0
        
        # Additional score from being mentioned in multiple sources
        sources = result.get("sources", [])
        score += min(len(sources) * 0.1, 0.5)  # Up to 0.5 points for multiple sources
        
        return min(score, 1.0)

    def _parse_attraction_from_search_result(self, result: Dict[str, Any]) -> Attraction:
        """Parse search result into Attraction object"""
        content = result.get("content", "")
        title = result.get("title", "").split(" - ")[0]
        
        # Determine category based on content and title
        categories = {
            "museum": ["museum", "gallery", "exhibition", "art center", "cultural center"],
            "landmark": ["landmark", "monument", "tower", "palace", "castle", "bridge", "statue"],
            "park": ["park", "garden", "nature reserve", "botanical garden", "zoo", "aquarium"],
            "restaurant": ["restaurant", "cafe", "dining", "food market", "culinary", "bistro"],
            "shopping": ["mall", "market", "shopping center", "boutique", "souvenir", "bazaar"],
            "entertainment": ["theater", "cinema", "amusement park", "concert hall", "stadium"],
            "religious": ["temple", "church", "mosque", "cathedral", "shrine", "monastery"],
            "historical": ["ruins", "historical site", "ancient", "archaeological", "heritage"],
            "outdoor": ["beach", "mountain", "hiking", "viewpoint", "scenic spot", "trail"],
            "nightlife": ["bar", "club", "night market", "entertainment district"],
            "transportation": ["station", "port", "airport", "terminal", "hub"],
            "education": ["university", "library", "school", "institute", "academy"]
        }
        
        category = "other"
        for cat, keywords in categories.items():
            if any(keyword in content.lower() or keyword in title.lower() for keyword in keywords):
                category = cat
                break
        
        # Extract best time to visit from content
        best_time = None
        time_patterns = [
            r'best time to visit.*?(\w+ to \w+)',
            r'peak season.*?(\w+ to \w+)',
            r'recommended time.*?(\w+ to \w+)',
            r'ideal time.*?(\w+ to \w+)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content.lower())
            if match:
                best_time = match.group(1)
                break
        
        return Attraction(
            name=title,
            description=content,
            category=category,
            rating=self._extract_rating(content),
            price_level=self._extract_price_level(content),
            opening_hours=None,  # Would need specific API for this
            address=None,  # Would need specific API for this
            website=result.get("url"),
            images=[],  # Would need specific API for images
            source=result.get("source", "Unknown"),
            popularity_score=self._calculate_popularity_score(result),
            best_time_to_visit=best_time,
            visit_duration=self._extract_duration(content)
        )

    def search_attractions(
        self,
        trip_prefs: TripPreferences,
        num_results: int = 10,
        categories: Optional[List[str]] = None
    ) -> List[Attraction]:
        """
        Search for attractions based on trip preferences
        
        Args:
            trip_prefs (TripPreferences): User's trip preferences
            num_results (int): Number of results to return
            categories (List[str], optional): Specific categories to search for
            
        Returns:
            List[Attraction]: List of matching attractions
            
        Raises:
            AttractionSearchError: If there is an error during the search
        """
        try:
            if not trip_prefs.destination:
                raise ValueError("Destination is required")
            
            # Construct search query
            query_parts = [
                f"top attractions in {trip_prefs.destination}",
                f"best places to visit in {trip_prefs.destination}"
            ]
            
            # Add interests to query
            if trip_prefs.interests:
                interests_query = " ".join(trip_prefs.interests)
                query_parts.append(f"{interests_query} in {trip_prefs.destination}")
            
            # Add specific categories if provided
            if categories:
                for category in categories:
                    query_parts.append(f"best {category} in {trip_prefs.destination}")
            
            # Combine queries
            query = " | ".join(query_parts)
            
            params = {
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_domains": [
                    "tripadvisor.com",
                    "lonelyplanet.com",
                    "wikitravel.org",
                    "timeout.com",
                    "viator.com",
                    "fodors.com",
                    "roughguides.com"
                ],
                "max_results": num_results,
                "include_raw_content": True
            }
            
            response = requests.post(self.tavily_url, headers=self.headers, json=params)
            response.raise_for_status()
            
            results = response.json().get("results", [])
            if not results:
                raise AttractionSearchError("No results found")
            
            attractions = [self._parse_attraction_from_search_result(r) for r in results]
            
            # Sort by popularity score
            attractions.sort(key=lambda x: x.popularity_score or 0, reverse=True)
            
            return attractions
            
        except requests.RequestException as e:
            raise AttractionSearchError(f"API request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise AttractionSearchError(f"Failed to parse attraction data: {e}")
        except Exception as e:
            raise AttractionSearchError(f"Unexpected error: {e}")

def format_attraction_results(attractions: List[Attraction]) -> str:
    """
    Format a list of Attraction objects into a readable string
    
    Args:
        attractions (List[Attraction]): List of attraction results
        
    Returns:
        str: Formatted string
    """
    if not attractions:
        return "No attractions found matching your criteria."
    
    lines = ["Found the following attractions:\n"]
    
    # Group attractions by category
    categories = {}
    for attraction in attractions:
        if attraction.category not in categories:
            categories[attraction.category] = []
        categories[attraction.category].append(attraction)
    
    # Print attractions by category
    for category, category_attractions in categories.items():
        lines.append(f"\n{category.upper()}:")
        for i, attraction in enumerate(category_attractions, start=1):
            lines.append(f"\n{i}. {attraction.name}")
            if attraction.rating is not None:
                lines.append(f"   Rating: {attraction.rating}/5.0")
            if attraction.price_level:
                lines.append(f"   Price Level: {attraction.price_level}")
            if attraction.visit_duration:
                lines.append(f"   Visit Duration: {attraction.visit_duration}")
            if attraction.website:
                lines.append(f"   Website: {attraction.website}")
            desc_preview = attraction.description[:200].replace('\n', ' ').strip()
            lines.append(f"   Description: {desc_preview}...")
    
    return "\n".join(lines)

# Example usage
if __name__ == "__main__":
    
    preferences = {
        "destination": "Paris",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "budget": 2000,
        "travel_style": "moderate",
        "interests": ["culture", "food", "art"],
        "accommodation_preference": "hotel",
        "transportation_preference": "mixed"
    }
    
    from tools.parse_trip_prefs import parse_trip_preferences, TripPreferences
    
    try:
        # Wrap preferences in agent state
        state = {"user_input": preferences}
        parsed_state = parse_trip_preferences(state)
        if "error" in parsed_state:
            raise Exception(parsed_state["error"])
        
        # Extract TripPreferences from parsed state
        trip_prefs = TripPreferences(
            destination=parsed_state["destination"],
            start_date=parsed_state["start_date"],
            end_date=parsed_state["end_date"],
            budget=parsed_state["budget"],
            travel_style=parsed_state["travel_style"],
            interests=parsed_state["interests"],
            accommodation_preference=parsed_state["accommodation_preference"],
            transportation_preference=parsed_state["transportation_preference"],
            dietary_restrictions=parsed_state.get("dietary_restrictions"),
            special_requirements=parsed_state.get("special_requirements")
        )
        
        searcher = AttractionSearcher(TAVILY_API_KEY)
        attractions = searcher.search_attractions(
            trip_prefs,
            categories=["museum", "landmark", "restaurant"]
        )
        
        print(format_attraction_results(attractions))
        
    except Exception as e:
        print(f"Error: {e}")