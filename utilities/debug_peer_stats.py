#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
from src.validation.quality_control import ValidationFramework

def debug_peer_group_analysis():
    """Debug the peer group analysis that's failing"""
    
    vf = ValidationFramework()
    
    # Exact test data from failing test
    rating_data = {
        'final_score': 88.5,
        'quantitative_score': 35.0,
        'sector_score': 20.5
    }
    
    peer_data = pd.DataFrame({
        'final_score': [85.0, 87.0, 89.0, 91.0, 86.5],
        'quantitative_score': [33.0, 34.0, 36.0, 37.0, 35.5],
        'sector_score': [19.0, 20.0, 21.0, 22.0, 20.5]
    })
    
    print("Input data:")
    print(f"  rating_data: {rating_data}")
    print(f"  peer_data shape: {peer_data.shape}")
    print(f"  peer final_scores: {peer_data['final_score'].tolist()}")
    
    # Step by step debugging
    peer_scores = peer_data['final_score'].dropna().tolist()
    print(f"\nAfter dropna: {peer_scores}")
    print(f"Length check (< 5): {len(peer_scores) < 5}")
    
    # Call the method
    result = vf.validate_peer_group_analysis(rating_data, peer_data)
    
    print(f"\nResult:")
    print(f"  Keys: {list(result.keys())}")
    print(f"  Full result: {result}")
    
    # Check the specific assertion
    has_peer_statistics = 'peer_statistics' in result
    print(f"\nAssertion checks:")
    print(f"  'peer_statistics' in result: {has_peer_statistics}")
    
    if has_peer_statistics:
        print(f"  peer_statistics content: {result['peer_statistics']}")
    else:
        print("  peer_statistics is missing!")
        
    # Manual calculation for comparison
    peer_series = pd.Series(peer_scores)
    expected_mean = peer_series.mean()
    expected_std = peer_series.std()
    expected_z = abs(rating_data['final_score'] - expected_mean) / expected_std
    
    print(f"\nManual calculation:")
    print(f"  Mean: {expected_mean}")
    print(f"  Std: {expected_std}")  
    print(f"  Z-score: {expected_z}")

if __name__ == "__main__":
    debug_peer_group_analysis()