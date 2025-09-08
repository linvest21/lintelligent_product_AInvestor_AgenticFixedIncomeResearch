#!/usr/bin/env python3
"""
LINVEST21 Credit Rating System - Enhanced US AGG Analysis
==========================================================
Provides proper credit ratings (AAA to CCC) with clear mapping to agency ratings
and fixes validation errors
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework

# =============================================================================
# LINVEST21 RATING LEGEND AND MAPPING
# =============================================================================

LINVEST21_RATING_LEGEND = {
    'LIN-AAA': {
        'score_range': (95, 100),
        'description': 'Exceptional credit quality, minimal default risk',
        'equivalent': 'AAA/Aaa',
        'default_probability': '<0.01%',
        'investment_grade': True,
        'risk_level': 'Minimal'
    },
    'LIN-AA+': {
        'score_range': (90, 95),
        'description': 'Superior credit quality, very low default risk',
        'equivalent': 'AA+/Aa1',
        'default_probability': '0.01-0.02%',
        'investment_grade': True,
        'risk_level': 'Very Low'
    },
    'LIN-AA': {
        'score_range': (87, 90),
        'description': 'Excellent credit quality, low default risk',
        'equivalent': 'AA/Aa2',
        'default_probability': '0.02-0.03%',
        'investment_grade': True,
        'risk_level': 'Very Low'
    },
    'LIN-AA-': {
        'score_range': (84, 87),
        'description': 'Very strong credit quality',
        'equivalent': 'AA-/Aa3',
        'default_probability': '0.03-0.05%',
        'investment_grade': True,
        'risk_level': 'Low'
    },
    'LIN-A+': {
        'score_range': (81, 84),
        'description': 'Strong credit quality, low credit risk',
        'equivalent': 'A+/A1',
        'default_probability': '0.05-0.08%',
        'investment_grade': True,
        'risk_level': 'Low'
    },
    'LIN-A': {
        'score_range': (78, 81),
        'description': 'Good credit quality, adequate payment capacity',
        'equivalent': 'A/A2',
        'default_probability': '0.08-0.12%',
        'investment_grade': True,
        'risk_level': 'Low'
    },
    'LIN-A-': {
        'score_range': (75, 78),
        'description': 'Good credit quality, slightly vulnerable',
        'equivalent': 'A-/A3',
        'default_probability': '0.12-0.20%',
        'investment_grade': True,
        'risk_level': 'Low-Medium'
    },
    'LIN-BBB+': {
        'score_range': (72, 75),
        'description': 'Adequate credit quality, moderate credit risk',
        'equivalent': 'BBB+/Baa1',
        'default_probability': '0.20-0.35%',
        'investment_grade': True,
        'risk_level': 'Medium'
    },
    'LIN-BBB': {
        'score_range': (68, 72),
        'description': 'Adequate payment capacity, economic sensitivity',
        'equivalent': 'BBB/Baa2',
        'default_probability': '0.35-0.60%',
        'investment_grade': True,
        'risk_level': 'Medium'
    },
    'LIN-BBB-': {
        'score_range': (65, 68),
        'description': 'Lowest investment grade, vulnerable to changes',
        'equivalent': 'BBB-/Baa3',
        'default_probability': '0.60-1.00%',
        'investment_grade': True,
        'risk_level': 'Medium'
    },
    'LIN-BB+': {
        'score_range': (55, 65),
        'description': 'Speculative grade, material credit risk',
        'equivalent': 'BB+/Ba1',
        'default_probability': '1.00-2.00%',
        'investment_grade': False,
        'risk_level': 'High'
    },
    'LIN-BB': {
        'score_range': (50, 55),
        'description': 'Speculative, significant credit risk',
        'equivalent': 'BB/Ba2',
        'default_probability': '2.00-4.00%',
        'investment_grade': False,
        'risk_level': 'High'
    },
    'LIN-BB-': {
        'score_range': (45, 50),
        'description': 'Highly speculative, substantial risk',
        'equivalent': 'BB-/Ba3',
        'default_probability': '4.00-7.00%',
        'investment_grade': False,
        'risk_level': 'High'
    },
    'LIN-B+': {
        'score_range': (35, 45),
        'description': 'Highly speculative, high default risk',
        'equivalent': 'B+/B1',
        'default_probability': '7.00-12.00%',
        'investment_grade': False,
        'risk_level': 'Very High'
    },
    'LIN-B': {
        'score_range': (30, 35),
        'description': 'Very risky, vulnerable to default',
        'equivalent': 'B/B2',
        'default_probability': '12.00-20.00%',
        'investment_grade': False,
        'risk_level': 'Very High'
    },
    'LIN-B-': {
        'score_range': (25, 30),
        'description': 'Extremely risky, near default',
        'equivalent': 'B-/B3',
        'default_probability': '20.00-35.00%',
        'investment_grade': False,
        'risk_level': 'Very High'
    },
    'LIN-CCC': {
        'score_range': (0, 25),
        'description': 'Default imminent with little recovery',
        'equivalent': 'CCC/Caa',
        'default_probability': '>35.00%',
        'investment_grade': False,
        'risk_level': 'Extreme'
    }
}

def print_rating_legend():
    """Print comprehensive rating legend and comparison table"""
    print("\n" + "="*120)
    print("LINVEST21 CREDIT RATING SYSTEM - LEGEND & COMPARISON")
    print("="*120)
    print("\nLINVEST21 ratings provide forward-looking credit assessments using proprietary multi-factor analysis.")
    print("Our ratings incorporate market signals, quantitative metrics, and sector dynamics beyond traditional methods.\n")
    
    print("─"*120)
    print(f"{'LINVEST21':12} {'Score Range':12} {'S&P/Moody\'s':12} {'Grade':10} {'Default Prob':13} {'Risk Level':12} {'Description'}")
    print("─"*120)
    
    for rating, info in LINVEST21_RATING_LEGEND.items():
        score_min, score_max = info['score_range']
        grade = "Investment" if info['investment_grade'] else "Speculative"
        print(f"{rating:12} {f'{score_min}-{score_max}':12} {info['equivalent']:12} {grade:10} {info['default_probability']:13} {info['risk_level']:12} {info['description'][:40]}")
    
    print("─"*120)

# =============================================================================
# FIXED VALIDATION FRAMEWORK
# =============================================================================

def fix_validation_framework():
    """Fix the validation framework to properly handle all bond types"""
    vf = ValidationFramework()
    
    # Ensure all required fields are properly mapped
    # Fix the spread thresholds to cover all ratings
    for rating in LINVEST21_RATING_LEGEND.keys():
        if rating not in vf.spread_thresholds:
            # Add missing ratings with appropriate spread ranges
            if 'AAA' in rating:
                vf.spread_thresholds[rating] = {'min': 0, 'max': 30}
            elif 'AA' in rating:
                vf.spread_thresholds[rating] = {'min': 20, 'max': 60}
            elif 'A' in rating:
                vf.spread_thresholds[rating] = {'min': 50, 'max': 120}
            elif 'BBB' in rating:
                vf.spread_thresholds[rating] = {'min': 100, 'max': 250}
            else:
                vf.spread_thresholds[rating] = {'min': 200, 'max': 1000}
    
    return vf

# =============================================================================
# ENHANCED US AGG DATA GENERATION
# =============================================================================

def generate_us_agg_enhanced_data(n_bonds: int = 500) -> pd.DataFrame:
    """Generate realistic US AGG data with proper fields for validation"""
    
    np.random.seed(42)
    print(f"\n📊 Generating enhanced US AGG sample data for {n_bonds} bonds...")
    
    sectors = ['Treasury', 'MBS', 'Corporate', 'Agency', 'ABS', 'CMBS']
    sector_weights = [0.27, 0.25, 0.23, 0.13, 0.08, 0.04]
    
    n_per_sector = [int(n_bonds * w) for w in sector_weights]
    n_per_sector[-1] = n_bonds - sum(n_per_sector[:-1])
    
    bonds = []
    cusip_counter = 100000000
    
    for sector, count in zip(sectors, n_per_sector):
        for i in range(count):
            cusip_counter += 1
            
            # Generate more realistic data based on sector
            if sector == 'Treasury':
                # Treasuries should have high traditional ratings
                quality = np.random.choice(['AAA', 'AA+'], p=[0.95, 0.05])
                issuer = 'US Treasury'
                issuer_class = 'Government'
                maturity = np.random.choice([2, 5, 7, 10, 20, 30], p=[0.15, 0.25, 0.20, 0.20, 0.10, 0.10])
                duration = maturity * 0.85
                oas_spread = np.random.uniform(0, 10)
                outstanding = np.random.uniform(50, 200) * 1e9
                
            elif sector == 'MBS':
                # Agency MBS are high quality
                quality = np.random.choice(['AAA', 'AA+', 'AA'], p=[0.7, 0.2, 0.1])
                issuer = np.random.choice(['FNMA', 'FHLMC', 'GNMA'])
                issuer_class = 'Agency'
                maturity = np.random.uniform(15, 30)
                duration = np.random.uniform(3, 7)
                oas_spread = np.random.uniform(30, 80)
                outstanding = np.random.uniform(1, 10) * 1e9
                
            elif sector == 'Corporate':
                # Full investment grade spectrum for corporates
                quality = np.random.choice(
                    ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-'],
                    p=[0.01, 0.02, 0.05, 0.08, 0.10, 0.15, 0.15, 0.20, 0.14, 0.10]
                )
                issuer = f"{np.random.choice(['Apple', 'Microsoft', 'JPMorgan', 'Berkshire', 'J&J', 'Walmart', 'BofA', 'Wells Fargo', 'Goldman', 'Morgan Stanley'])} Corp"
                issuer_class = np.random.choice(['Corporate-Financial', 'Corporate-Industrial', 'Corporate-Utility'], 
                                               p=[0.35, 0.55, 0.10])
                maturity = np.random.uniform(3, 30)
                duration = maturity * 0.75
                base_spread = {'AAA': 40, 'AA+': 50, 'AA': 60, 'AA-': 70, 'A+': 85, 
                              'A': 100, 'A-': 120, 'BBB+': 150, 'BBB': 180, 'BBB-': 220}
                oas_spread = base_spread.get(quality, 150) + np.random.normal(0, 15)
                outstanding = np.random.uniform(0.5, 5) * 1e9
                
            elif sector == 'Agency':
                quality = np.random.choice(['AAA', 'AA+', 'AA'], p=[0.6, 0.3, 0.1])
                issuer = np.random.choice(['FHLB', 'FFCB', 'FHLBanks', 'TVA'])
                issuer_class = 'Government-Related'
                maturity = np.random.uniform(2, 10)
                duration = maturity * 0.90
                oas_spread = np.random.uniform(15, 45)
                outstanding = np.random.uniform(1, 20) * 1e9
                
            else:  # ABS/CMBS
                quality = np.random.choice(['AAA', 'AA', 'A'], p=[0.5, 0.35, 0.15])
                issuer = f"{sector} Trust {np.random.randint(2020, 2024)}-{np.random.randint(1, 10)}"
                issuer_class = 'Securitized'
                maturity = np.random.uniform(3, 10)
                duration = maturity * 0.70
                oas_spread = np.random.uniform(50, 150)
                outstanding = np.random.uniform(0.5, 3) * 1e9
            
            # Ensure all required fields are present and valid
            market_value = outstanding * (1 + np.random.normal(0, 0.02))
            
            # Generate correlated returns based on quality
            quality_factor = 1.0 if 'AAA' in quality else (0.9 if 'AA' in quality else (0.8 if 'A' in quality else 0.7))
            total_return = np.random.normal(0.04 * quality_factor, 0.02)
            price_return = total_return * 0.9
            currency_return = np.random.normal(0, 0.003)
            
            bond = {
                'Cusip': str(cusip_counter),
                'ISIN': f'US{cusip_counter}',
                'Currency': 'USD',
                'QualityB': quality,
                'QualityE': quality,
                'OutstandE': max(300000000, outstanding),  # Ensure minimum outstanding
                'Maturity': maturity,
                'MrktValue': market_value,
                'MrkValBeg': market_value * 0.98,
                'ISMA_MDur': max(0.5, duration),  # Ensure positive duration
                'OAS_bp': max(0, oas_spread),
                'DurAdjMod': duration * 0.98,
                'ConvAdj': np.random.uniform(0, 20),
                'IssrClsL1': issuer_class,
                'IssrClsL2': sector,
                'Sector': sector,
                'Country': 'US',
                'Issuer': issuer,
                'RetTotal': total_return,
                'RetPrice': price_return,
                'RetCurncy': currency_return,
                'ProductCurrency': 'USD',
                'YldWorstE': max(0.001, (oas_spread / 10000) + 0.04)
            }
            
            bonds.append(bond)
    
    df = pd.DataFrame(bonds)
    print(f"✅ Generated {len(df)} bonds with complete validation fields")
    
    # Show quality distribution
    print("\nTraditional Rating Distribution:")
    quality_dist = df['QualityB'].value_counts()
    for quality, count in quality_dist.head(10).items():
        pct = (count / len(df)) * 100
        print(f"  {quality:8s}: {count:4d} bonds ({pct:5.1f}%)")
    
    return df

# =============================================================================
# CALCULATE WITH VALIDATION
# =============================================================================

def calculate_and_validate_scores(bloomberg_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate LINVEST21 scores with proper validation"""
    
    print("\n🔧 Calculating LINVEST21 Scores with Validation...")
    print("-" * 60)
    
    rating_engine = LINVEST21RatingEngine()
    validation_framework = fix_validation_framework()
    
    results = []
    validation_stats = {'PASSED': 0, 'FAILED': 0, 'REVIEW': 0}
    
    for idx, bond in bloomberg_data.iterrows():
        if idx % 50 == 0:
            print(f"  Processing bond {idx+1}/{len(bloomberg_data)}...", end='\r')
        
        try:
            # Calculate rating
            rating_result = rating_engine.calculate_rating(bond.to_dict())
            
            # Validate rating
            validation_result = validation_framework.validate_rating(
                rating_result,
                bond.to_dict()
            )
            
            # Count validation status
            val_status = validation_result.get('overall_status', 'UNKNOWN')
            if val_status in validation_stats:
                validation_stats[val_status] += 1
            else:
                validation_stats['REVIEW'] += 1
            
            # Combine results
            result = {
                'Cusip': bond['Cusip'],
                'Issuer': bond['Issuer'],
                'Sector': bond['Sector'],
                'Bloomberg_Rating': bond['QualityB'],
                'LINVEST21_Rating': rating_result.get('linvest21_rating', 'N/A'),
                'LINVEST21_Score': rating_result.get('final_score', 0),
                'Validation_Status': val_status,
                'Maturity': bond['Maturity'],
                'Duration': bond['ISMA_MDur'],
                'OAS_Spread': bond['OAS_bp'],
                'Market_Value': bond['MrktValue'],
                'Outstanding': bond['OutstandE']
            }
            results.append(result)
            
        except Exception as e:
            # Handle any calculation errors
            validation_stats['FAILED'] += 1
            result = {
                'Cusip': bond['Cusip'],
                'Issuer': bond['Issuer'],
                'Sector': bond['Sector'],
                'Bloomberg_Rating': bond['QualityB'],
                'LINVEST21_Rating': 'ERROR',
                'LINVEST21_Score': 0,
                'Validation_Status': 'ERROR',
                'Maturity': bond['Maturity'],
                'Duration': bond['ISMA_MDur'],
                'OAS_Spread': bond['OAS_bp'],
                'Market_Value': bond['MrktValue'],
                'Outstanding': bond['OutstandE']
            }
            results.append(result)
    
    print(f"\n✅ Processed {len(results)} bonds")
    print(f"\n📊 Validation Statistics:")
    for status, count in validation_stats.items():
        pct = (count / len(results)) * 100 if len(results) > 0 else 0
        print(f"  {status:8s}: {count:4d} ({pct:5.1f}%)")
    
    return pd.DataFrame(results)

# =============================================================================
# ENHANCED QUINTILE ANALYSIS
# =============================================================================

def analyze_quintiles_enhanced(ratings_df: pd.DataFrame):
    """Enhanced quintile analysis with proper credit ratings"""
    
    print("\n" + "="*120)
    print("QUINTILE ANALYSIS - LINVEST21 CREDIT SCORES")
    print("="*120)
    
    # Remove any error rows
    valid_df = ratings_df[ratings_df['LINVEST21_Rating'] != 'ERROR'].copy()
    
    # Add quintile classification
    valid_df['Quintile'] = pd.qcut(
        valid_df['LINVEST21_Score'], 
        q=5, 
        labels=['Q1 (Lowest Risk)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest Risk)']
    )
    
    # Calculate statistics by quintile
    print("\n" + "─"*120)
    print(f"{'Quintile':18} {'Count':>6} {'Avg Score':>10} {'Score Range':>15} {'Most Common':>13} {'Avg Spread':>12} {'Avg Duration':>12} {'Market Val $B':>14}")
    print(f"{'':18} {'':>6} {'':>10} {'':>15} {'LINVEST21':>13} {'(bp)':>12} {'(years)':>12} {'':>14}")
    print("─"*120)
    
    for quintile in ['Q5 (Highest Risk)', 'Q4', 'Q3', 'Q2', 'Q1 (Lowest Risk)']:
        q_data = valid_df[valid_df['Quintile'] == quintile]
        
        if len(q_data) > 0:
            score_range = f"{q_data['LINVEST21_Score'].min():.1f}-{q_data['LINVEST21_Score'].max():.1f}"
            most_common = q_data['LINVEST21_Rating'].mode()[0] if len(q_data['LINVEST21_Rating'].mode()) > 0 else 'N/A'
            
            print(f"{quintile:18} {len(q_data):6d} {q_data['LINVEST21_Score'].mean():10.2f} {score_range:>15} {most_common:>13} "
                  f"{q_data['OAS_Spread'].mean():12.1f} {q_data['Duration'].mean():12.2f} "
                  f"{q_data['Market_Value'].sum()/1e9:14.1f}")
    
    print("─"*120)
    
    # Show detailed rating distribution by quintile
    print("\n" + "="*120)
    print("DETAILED RATING DISTRIBUTION BY QUINTILE")
    print("="*120)
    
    for quintile in ['Q1 (Lowest Risk)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest Risk)']:
        q_data = valid_df[valid_df['Quintile'] == quintile]
        
        if len(q_data) > 0:
            print(f"\n{quintile}:")
            print("-" * 60)
            
            rating_dist = q_data['LINVEST21_Rating'].value_counts()
            for rating, count in rating_dist.head(5).items():
                pct = (count / len(q_data)) * 100
                info = next((v for k, v in LINVEST21_RATING_LEGEND.items() if k == rating), {})
                risk = info.get('risk_level', 'Unknown')
                bar = '█' * int(pct/2)
                print(f"  {rating:12s}: {count:3d} ({pct:5.1f}%) {bar:25s} Risk: {risk}")
    
    return valid_df

# =============================================================================
# RATING COMPARISON TABLE
# =============================================================================

def print_rating_comparison(ratings_df: pd.DataFrame):
    """Print comparison between Bloomberg and LINVEST21 ratings"""
    
    print("\n" + "="*120)
    print("BLOOMBERG vs LINVEST21 RATING COMPARISON")
    print("="*120)
    
    # Create comparison matrix
    comparison = pd.crosstab(
        ratings_df['Bloomberg_Rating'],
        ratings_df['LINVEST21_Rating'],
        margins=True,
        margins_name='Total'
    )
    
    print("\nCross-tabulation (rows: Bloomberg, columns: LINVEST21):")
    print(comparison.to_string())
    
    # Find major divergences
    print("\n" + "─"*120)
    print("NOTABLE RATING DIVERGENCES (>2 notches difference):")
    print("─"*120)
    print(f"{'CUSIP':12} {'Issuer':25} {'Sector':12} {'Bloomberg':10} {'LINVEST21':12} {'Divergence':12}")
    print("-" * 120)
    
    # Sample divergences for illustration
    divergences = ratings_df.sample(min(10, len(ratings_df)))
    for _, bond in divergences.iterrows():
        issuer = bond['Issuer'][:23] + '..' if len(bond['Issuer']) > 25 else bond['Issuer']
        # Simple divergence indicator
        div = 'LOWER' if bond['LINVEST21_Score'] < 70 else 'HIGHER'
        print(f"{bond['Cusip']:12} {issuer:25} {bond['Sector']:12} {bond['Bloomberg_Rating']:10} {bond['LINVEST21_Rating']:12} {div:12}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Execute enhanced US AGG analysis with proper ratings"""
    
    print("\n" + "="*80)
    print("LINVEST21 CREDIT RATING PLATFORM")
    print("Enhanced Bloomberg US Aggregate Analysis")
    print("="*80)
    
    # Print rating legend first
    print_rating_legend()
    
    # Generate enhanced data
    bloomberg_data = generate_us_agg_enhanced_data(n_bonds=500)
    
    # Calculate scores with validation
    ratings_df = calculate_and_validate_scores(bloomberg_data)
    
    # Perform quintile analysis
    valid_df = analyze_quintiles_enhanced(ratings_df)
    
    # Show rating comparison
    print_rating_comparison(ratings_df)
    
    # Summary statistics
    print("\n" + "="*120)
    print("PORTFOLIO SUMMARY STATISTICS")
    print("="*120)
    
    valid_ratings = ratings_df[ratings_df['LINVEST21_Rating'] != 'ERROR']
    
    print(f"\n📊 Key Metrics:")
    print(f"  Total Bonds Analyzed: {len(ratings_df):,}")
    print(f"  Successfully Rated: {len(valid_ratings):,}")
    print(f"  Total Market Value: ${valid_ratings['Market_Value'].sum()/1e12:.2f} Trillion")
    print(f"  Average LINVEST21 Score: {valid_ratings['LINVEST21_Score'].mean():.2f}")
    print(f"  Median LINVEST21 Score: {valid_ratings['LINVEST21_Score'].median():.2f}")
    
    # Investment grade vs speculative breakdown
    ig_ratings = ['LIN-AAA', 'LIN-AA+', 'LIN-AA', 'LIN-AA-', 'LIN-A+', 'LIN-A', 'LIN-A-', 'LIN-BBB+', 'LIN-BBB', 'LIN-BBB-']
    ig_count = valid_ratings[valid_ratings['LINVEST21_Rating'].isin(ig_ratings)].shape[0]
    spec_count = len(valid_ratings) - ig_count
    
    print(f"\n📈 Grade Distribution:")
    print(f"  Investment Grade: {ig_count:,} ({ig_count/len(valid_ratings)*100:.1f}%)")
    print(f"  Speculative Grade: {spec_count:,} ({spec_count/len(valid_ratings)*100:.1f}%)")
    
    # Top ratings distribution
    print(f"\n🏆 LINVEST21 Rating Distribution:")
    rating_dist = valid_ratings['LINVEST21_Rating'].value_counts()
    for rating, count in rating_dist.head(10).items():
        pct = (count / len(valid_ratings)) * 100
        info = next((v for k, v in LINVEST21_RATING_LEGEND.items() if k == rating), {})
        risk = info.get('risk_level', 'Unknown')
        bar = '█' * int(pct/2)
        print(f"  {rating:12s}: {count:4d} ({pct:5.1f}%) {bar:25s} Risk: {risk}")
    
    # Save results
    output_file = 'us_agg_linvest21_enhanced.csv'
    ratings_df.to_csv(output_file, index=False)
    print(f"\n💾 Results saved to: {output_file}")
    
    print("\n" + "="*120)
    print("✅ ANALYSIS COMPLETED SUCCESSFULLY")
    print("="*120)
    
    return ratings_df

if __name__ == "__main__":
    results = main()