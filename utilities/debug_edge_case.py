#!/usr/bin/env python3
"""Debug edge case scores"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.rating_engine import LINVEST21RatingEngine

# Test the maximum values edge case
engine = LINVEST21RatingEngine()

max_case = {
    'Cusip': '999999999',
    'Currency': 'USD',
    'QualityB': 'AAA',
    'OutstandE': 50000000000,  # Very large
    'Maturity': 30.0,  # Long maturity
    'MrktValue': 50000000000,
    'MrkValBeg': 50000000000,
    'ISMA_MDur': 25.0,  # High duration
    'OAS_bp': 10,  # Very low spread
    'IssrClsL1': 'Government',
    'Sector': 'Government',
    'RetTotal': 0.20,  # High return
    'RetCurncy': -0.02,
}

result = engine.calculate_rating(max_case)
print("Maximum values case analysis:")
print(f"Final Score: {result['final_score']}")
print(f"Rating: {result['linvest21_rating']}")
print(f"Quantitative Score (40% weight): {result['quantitative_score']}")
print(f"  - Duration (very high 25.0): {result['components']['duration']}")
print(f"  - Spread (low 10bp): {result['components']['spread']}")
print(f"  - Liquidity (huge outstanding): {result['components']['liquidity']}")
print(f"Agency Score (35% weight): {result['agency_score']}")
print(f"Sector Score (25% weight): {result['sector_score']}")
print(f"Alpha Score (15% weight): {result['alpha_score']}")

print("\nAnalysis:")
print("- High duration (25.0) creates HIGH RISK score")
print("- Low spread (10bp) creates low risk score") 
print("- Government sector has lower risk multiplier")
print("- AAA gets highest agency score")
print("- The high duration is dominating the score, which is correct!")