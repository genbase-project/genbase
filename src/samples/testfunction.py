# sample_functions.py
from typing import List, Dict, Optional
from pydantic import BaseModel

class UserData(BaseModel):
    name: str
    age: int
    skills: List[str]

def calculate_sum(a: int, b: int) -> int:
    """
    Add two numbers together
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of the two numbers
    """
    return a + b

def process_user_data(user: UserData) -> Dict[str, any]:
    """
    Process user data and return enriched information
    
    Args:
        user: UserData object containing user information
        
    Returns:
        Processed user information
    """
    return {
        "name": user.name.upper(),
        "is_adult": user.age >= 18,
        "skill_count": len(user.skills),
        "skills_summary": ", ".join(user.skills)
    }

def analyze_text(text: str, word_count: bool = False, unique_words: bool = False) -> Dict[str, any]:
    """
    Analyze text and return statistics
    
    Args:
        text: Input text to analyze
        word_count: Whether to count words
        unique_words: Whether to count unique words
        
    Returns:
        Text analysis results
    """
    results = {
        "length": len(text),
        "characters_no_spaces": len(text.replace(" ", ""))
    }
    
    if word_count:
        results["word_count"] = len(text.split())
        
    if unique_words:
        results["unique_words"] = len(set(text.lower().split()))
        
    return results