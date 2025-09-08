"""
LINVEST21 Credit Rating System Constants and Configuration
Official rating definitions and scoring thresholds
Version: 1.0.0
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class RatingDefinition:
    """Official LINVEST21 rating definition"""
    rating: str
    score_min: float
    score_max: float
    grade: str
    sp_equivalent: str
    moodys_equivalent: str
    default_prob_min: float
    default_prob_max: float
    description: str
    investment_grade: bool
    risk_level: str


# Official LINVEST21 19-notch rating scale
LINVEST21_RATINGS = {
    'LIN-AAA': RatingDefinition(
        rating='LIN-AAA',
        score_min=95, score_max=100,
        grade='Prime',
        sp_equivalent='AAA', moodys_equivalent='Aaa',
        default_prob_min=0.00, default_prob_max=0.01,
        description='Exceptional credit quality, virtually no default risk',
        investment_grade=True,
        risk_level='Minimal'
    ),
    'LIN-AA+': RatingDefinition(
        rating='LIN-AA+',
        score_min=90, score_max=94,
        grade='High Grade',
        sp_equivalent='AA+', moodys_equivalent='Aa1',
        default_prob_min=0.01, default_prob_max=0.02,
        description='Superior credit quality, minimal risk',
        investment_grade=True,
        risk_level='Very Low'
    ),
    'LIN-AA': RatingDefinition(
        rating='LIN-AA',
        score_min=87, score_max=89,
        grade='High Grade',
        sp_equivalent='AA', moodys_equivalent='Aa2',
        default_prob_min=0.02, default_prob_max=0.03,
        description='Excellent credit quality, very low risk',
        investment_grade=True,
        risk_level='Very Low'
    ),
    'LIN-AA-': RatingDefinition(
        rating='LIN-AA-',
        score_min=84, score_max=86,
        grade='High Grade',
        sp_equivalent='AA-', moodys_equivalent='Aa3',
        default_prob_min=0.03, default_prob_max=0.05,
        description='Very strong credit quality',
        investment_grade=True,
        risk_level='Low'
    ),
    'LIN-A+': RatingDefinition(
        rating='LIN-A+',
        score_min=81, score_max=83,
        grade='Upper Medium Grade',
        sp_equivalent='A+', moodys_equivalent='A1',
        default_prob_min=0.05, default_prob_max=0.08,
        description='Strong credit quality, low risk',
        investment_grade=True,
        risk_level='Low'
    ),
    'LIN-A': RatingDefinition(
        rating='LIN-A',
        score_min=78, score_max=80,
        grade='Upper Medium Grade',
        sp_equivalent='A', moodys_equivalent='A2',
        default_prob_min=0.08, default_prob_max=0.12,
        description='Good credit quality, susceptible to economic conditions',
        investment_grade=True,
        risk_level='Low-Medium'
    ),
    'LIN-A-': RatingDefinition(
        rating='LIN-A-',
        score_min=75, score_max=77,
        grade='Upper Medium Grade',
        sp_equivalent='A-', moodys_equivalent='A3',
        default_prob_min=0.12, default_prob_max=0.20,
        description='Good credit quality, more susceptible to changes',
        investment_grade=True,
        risk_level='Medium'
    ),
    'LIN-BBB+': RatingDefinition(
        rating='LIN-BBB+',
        score_min=72, score_max=74,
        grade='Lower Medium Grade',
        sp_equivalent='BBB+', moodys_equivalent='Baa1',
        default_prob_min=0.20, default_prob_max=0.35,
        description='Adequate credit quality, moderate risk',
        investment_grade=True,
        risk_level='Medium'
    ),
    'LIN-BBB': RatingDefinition(
        rating='LIN-BBB',
        score_min=68, score_max=71,
        grade='Lower Medium Grade',
        sp_equivalent='BBB', moodys_equivalent='Baa2',
        default_prob_min=0.35, default_prob_max=0.60,
        description='Adequate payment capacity, adverse conditions possible',
        investment_grade=True,
        risk_level='Medium'
    ),
    'LIN-BBB-': RatingDefinition(
        rating='LIN-BBB-',
        score_min=65, score_max=67,
        grade='Lower Medium Grade',
        sp_equivalent='BBB-', moodys_equivalent='Baa3',
        default_prob_min=0.60, default_prob_max=1.00,
        description='Lowest investment grade, vulnerable to adverse conditions',
        investment_grade=True,
        risk_level='Medium-High'
    ),
    'LIN-BB+': RatingDefinition(
        rating='LIN-BB+',
        score_min=55, score_max=64,
        grade='Non-Investment Grade',
        sp_equivalent='BB+', moodys_equivalent='Ba1',
        default_prob_min=1.00, default_prob_max=2.00,
        description='Speculative, substantial credit risk',
        investment_grade=False,
        risk_level='High'
    ),
    'LIN-BB': RatingDefinition(
        rating='LIN-BB',
        score_min=50, score_max=54,
        grade='Non-Investment Grade',
        sp_equivalent='BB', moodys_equivalent='Ba2',
        default_prob_min=2.00, default_prob_max=4.00,
        description='Speculative, significant ongoing uncertainty',
        investment_grade=False,
        risk_level='High'
    ),
    'LIN-BB-': RatingDefinition(
        rating='LIN-BB-',
        score_min=45, score_max=49,
        grade='Non-Investment Grade',
        sp_equivalent='BB-', moodys_equivalent='Ba3',
        default_prob_min=4.00, default_prob_max=6.00,
        description='Speculative, high credit risk',
        investment_grade=False,
        risk_level='High'
    ),
    'LIN-B+': RatingDefinition(
        rating='LIN-B+',
        score_min=35, score_max=44,
        grade='Highly Speculative',
        sp_equivalent='B+', moodys_equivalent='B1',
        default_prob_min=6.00, default_prob_max=8.00,
        description='Highly speculative, likely to fulfill obligations',
        investment_grade=False,
        risk_level='Very High'
    ),
    'LIN-B': RatingDefinition(
        rating='LIN-B',
        score_min=30, score_max=34,
        grade='Highly Speculative',
        sp_equivalent='B', moodys_equivalent='B2',
        default_prob_min=8.00, default_prob_max=12.00,
        description='Highly speculative, high credit risk',
        investment_grade=False,
        risk_level='Very High'
    ),
    'LIN-B-': RatingDefinition(
        rating='LIN-B-',
        score_min=25, score_max=29,
        grade='Highly Speculative',
        sp_equivalent='B-', moodys_equivalent='B3',
        default_prob_min=12.00, default_prob_max=18.00,
        description='Very high credit risk, vulnerable',
        investment_grade=False,
        risk_level='Very High'
    ),
    'LIN-CCC+': RatingDefinition(
        rating='LIN-CCC+',
        score_min=15, score_max=24,
        grade='Substantial Risk',
        sp_equivalent='CCC+', moodys_equivalent='Caa1',
        default_prob_min=18.00, default_prob_max=25.00,
        description='Substantial credit risk, vulnerable to default',
        investment_grade=False,
        risk_level='Extreme'
    ),
    'LIN-CCC': RatingDefinition(
        rating='LIN-CCC',
        score_min=10, score_max=14,
        grade='Extremely Speculative',
        sp_equivalent='CCC', moodys_equivalent='Caa2',
        default_prob_min=25.00, default_prob_max=35.00,
        description='Very high levels of credit risk',
        investment_grade=False,
        risk_level='Extreme'
    ),
    'LIN-CCC-': RatingDefinition(
        rating='LIN-CCC-',
        score_min=0, score_max=9,
        grade='Default Imminent',
        sp_equivalent='CCC-', moodys_equivalent='Caa3',
        default_prob_min=35.00, default_prob_max=100.00,
        description='Near default with little recovery prospect',
        investment_grade=False,
        risk_level='Default Imminent'
    )
}


# Rating order for sorting
RATING_ORDER = [
    'LIN-AAA', 'LIN-AA+', 'LIN-AA', 'LIN-AA-',
    'LIN-A+', 'LIN-A', 'LIN-A-',
    'LIN-BBB+', 'LIN-BBB', 'LIN-BBB-',
    'LIN-BB+', 'LIN-BB', 'LIN-BB-',
    'LIN-B+', 'LIN-B', 'LIN-B-',
    'LIN-CCC+', 'LIN-CCC', 'LIN-CCC-'
]


# Score thresholds for quick lookup
SCORE_THRESHOLDS = [
    (95, 'LIN-AAA'),
    (90, 'LIN-AA+'),
    (87, 'LIN-AA'),
    (84, 'LIN-AA-'),
    (81, 'LIN-A+'),
    (78, 'LIN-A'),
    (75, 'LIN-A-'),
    (72, 'LIN-BBB+'),
    (68, 'LIN-BBB'),
    (65, 'LIN-BBB-'),
    (55, 'LIN-BB+'),
    (50, 'LIN-BB'),
    (45, 'LIN-BB-'),
    (35, 'LIN-B+'),
    (30, 'LIN-B'),
    (25, 'LIN-B-'),
    (15, 'LIN-CCC+'),
    (10, 'LIN-CCC'),
    (0, 'LIN-CCC-')
]


# Investment grade cutoff
INVESTMENT_GRADE_CUTOFF = 65  # LIN-BBB- and above


# Component weights for scoring
COMPONENT_WEIGHTS = {
    'quantitative': 0.40,
    'agency_rating': 0.35,
    'sector_dynamics': 0.25,
    'alpha_factors': 0.15
}


def get_rating_from_score(score: float) -> str:
    """
    Convert a numeric score to LINVEST21 rating
    
    Args:
        score: Numeric score (0-100)
        
    Returns:
        LINVEST21 rating string
    """
    for threshold, rating in SCORE_THRESHOLDS:
        if score >= threshold:
            return rating
    return 'LIN-CCC-'


def is_investment_grade(rating: str) -> bool:
    """
    Check if a rating is investment grade
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        True if investment grade, False otherwise
    """
    if rating in LINVEST21_RATINGS:
        return LINVEST21_RATINGS[rating].investment_grade
    return False


def get_rating_details(rating: str) -> RatingDefinition:
    """
    Get full details for a rating
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        RatingDefinition object with all details
    """
    return LINVEST21_RATINGS.get(rating, None)


def get_sp_equivalent(rating: str) -> str:
    """
    Get S&P equivalent for LINVEST21 rating
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        S&P rating equivalent
    """
    if rating in LINVEST21_RATINGS:
        return LINVEST21_RATINGS[rating].sp_equivalent
    return 'NR'


def get_moodys_equivalent(rating: str) -> str:
    """
    Get Moody's equivalent for LINVEST21 rating
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        Moody's rating equivalent
    """
    if rating in LINVEST21_RATINGS:
        return LINVEST21_RATINGS[rating].moodys_equivalent
    return 'NR'


def get_default_probability(rating: str) -> Tuple[float, float]:
    """
    Get default probability range for a rating
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        Tuple of (min_probability, max_probability) in percentage
    """
    if rating in LINVEST21_RATINGS:
        details = LINVEST21_RATINGS[rating]
        return (details.default_prob_min, details.default_prob_max)
    return (0.0, 100.0)


def get_risk_level(rating: str) -> str:
    """
    Get risk level description for a rating
    
    Args:
        rating: LINVEST21 rating string
        
    Returns:
        Risk level description
    """
    if rating in LINVEST21_RATINGS:
        return LINVEST21_RATINGS[rating].risk_level
    return 'Unknown'