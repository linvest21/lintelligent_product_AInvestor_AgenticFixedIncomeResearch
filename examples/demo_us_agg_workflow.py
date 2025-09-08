#!/usr/bin/env python3
"""
LINVEST21 Credit Scoring Workflow for Bloomberg US Aggregate Benchmark
======================================================================

This demonstrates the complete workflow for:
1. Extracting US AGG benchmark constituents
2. Generating realistic sample data for US AGG bonds
3. Calculating LINVEST21 forward-looking credit scores
4. Analyzing results by quintiles
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, date, timezone
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

from src.core.rating_engine import LINVEST21RatingEngine
from src.data.bloomberg_connector import BloombergConnector
from src.validation.quality_control import ValidationFramework
# Skip daily_pipeline import to avoid sqlalchemy dependency

print("=" * 80)
print("LINVEST21 CREDIT SCORING PLATFORM")
print("Bloomberg US Aggregate Benchmark Analysis")
print("=" * 80)

# =============================================================================
# STEP 1: WORKFLOW OVERVIEW
# =============================================================================

print("\n📋 WORKFLOW OVERVIEW:")
print("-" * 40)
print("1. Connect to Bloomberg Terminal/API")
print("2. Extract US AGG benchmark constituents (~11,000 bonds)")
print("3. Filter for eligible securities (investment grade, USD)")
print("4. Calculate LINVEST21 scores using proprietary methodology")
print("5. Validate scores against market data")
print("6. Generate quintile analysis and reports")

# =============================================================================
# STEP 2: GENERATE REALISTIC US AGG SAMPLE DATA
# =============================================================================

def generate_us_agg_sample_data(n_bonds: int = 500) -> pd.DataFrame:
    """
    Generate realistic sample data representing US AGG benchmark constituents
    
    US AGG Composition (approximate):
    - 27% US Treasury
    - 25% MBS (Agency MBS)
    - 23% Corporate bonds
    - 13% Agency bonds
    - 12% Other (ABS, CMBS, etc.)
    """
    
    np.random.seed(42)  # For reproducibility
    
    print(f"\n📊 Generating sample data for {n_bonds} US AGG bonds...")
    
    # Define sector weights based on US AGG composition
    sectors = ['Treasury', 'MBS', 'Corporate', 'Agency', 'ABS', 'CMBS']
    sector_weights = [0.27, 0.25, 0.23, 0.13, 0.08, 0.04]
    
    # Generate sector assignments
    n_per_sector = [int(n_bonds * w) for w in sector_weights]
    n_per_sector[-1] = n_bonds - sum(n_per_sector[:-1])  # Adjust for rounding
    
    bonds = []
    cusip_counter = 100000000
    
    for sector, count in zip(sectors, n_per_sector):
        for i in range(count):
            cusip_counter += 1
            
            # Sector-specific characteristics
            if sector == 'Treasury':
                quality = 'AAA'
                issuer = 'US Treasury'
                issuer_class = 'Government'
                maturity = np.random.choice([2, 5, 7, 10, 20, 30], p=[0.15, 0.25, 0.20, 0.20, 0.10, 0.10])
                duration = maturity * 0.85
                oas_spread = np.random.uniform(0, 10)
                outstanding = np.random.uniform(20, 100) * 1e9
                
            elif sector == 'MBS':
                quality = 'AAA'
                issuer = np.random.choice(['FNMA', 'FHLMC', 'GNMA'])
                issuer_class = 'Agency'
                maturity = np.random.uniform(15, 30)
                duration = np.random.uniform(3, 7)  # MBS has lower duration due to prepayments
                oas_spread = np.random.uniform(30, 80)
                outstanding = np.random.uniform(1, 10) * 1e9
                
            elif sector == 'Corporate':
                # Investment grade corporate distribution
                quality = np.random.choice(
                    ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-'],
                    p=[0.01, 0.02, 0.03, 0.04, 0.08, 0.12, 0.15, 0.20, 0.20, 0.15]
                )
                issuer = f"{np.random.choice(['Apple', 'Microsoft', 'JPMorgan', 'Berkshire', 'Johnson', 'Walmart', 'Bank of America', 'Wells Fargo', 'Goldman', 'Morgan Stanley'])} Inc"
                issuer_class = np.random.choice(['Corporate-Financial', 'Corporate-Industrial', 'Corporate-Utility'], 
                                               p=[0.35, 0.55, 0.10])
                maturity = np.random.uniform(3, 30)
                duration = maturity * 0.75
                # Spread increases with lower rating
                base_spread = {'AAA': 40, 'AA+': 50, 'AA': 60, 'AA-': 70, 'A+': 85, 
                              'A': 100, 'A-': 120, 'BBB+': 150, 'BBB': 180, 'BBB-': 220}
                oas_spread = base_spread.get(quality, 150) + np.random.normal(0, 20)
                outstanding = np.random.uniform(0.5, 5) * 1e9
                
            elif sector == 'Agency':
                quality = np.random.choice(['AAA', 'AA+'], p=[0.7, 0.3])
                issuer = np.random.choice(['FHLB', 'FFCB', 'FHLBanks', 'TVA'])
                issuer_class = 'Government-Related'
                maturity = np.random.uniform(2, 10)
                duration = maturity * 0.90
                oas_spread = np.random.uniform(15, 45)
                outstanding = np.random.uniform(1, 20) * 1e9
                
            else:  # ABS/CMBS
                quality = np.random.choice(['AAA', 'AA', 'A'], p=[0.6, 0.3, 0.1])
                issuer = f"{sector} Trust {np.random.randint(2020, 2024)}-{np.random.randint(1, 10)}"
                issuer_class = 'Securitized'
                maturity = np.random.uniform(3, 10)
                duration = maturity * 0.70
                oas_spread = np.random.uniform(50, 150)
                outstanding = np.random.uniform(0.5, 3) * 1e9
            
            # Common fields with realistic correlations
            market_value = outstanding * (1 + np.random.normal(0, 0.05))
            
            # Generate return components (correlated with spread)
            spread_factor = oas_spread / 100
            total_return = np.random.normal(0.04 - spread_factor * 0.01, 0.02)
            price_return = total_return - (np.random.uniform(0.02, 0.05) if quality != 'AAA' else 0.01)
            currency_return = np.random.normal(0, 0.005)
            
            bond = {
                'Cusip': str(cusip_counter),
                'ISIN': f'US{cusip_counter}',
                'Currency': 'USD',
                'QualityB': quality,
                'QualityE': quality,  # Assume no rating change
                'OutstandE': outstanding,
                'Maturity': maturity,
                'MrktValue': market_value,
                'MrkValBeg': market_value * (1 - total_return/12),  # Beginning value
                'ISMA_MDur': duration,
                'OAS_bp': max(0, oas_spread),
                'DurAdjMod': duration * 0.98,
                'ConvAdj': np.random.uniform(0, 50),
                'IssrClsL1': issuer_class,
                'IssrClsL2': sector,
                'Sector': sector,
                'Country': 'US',
                'Issuer': issuer,
                'RetTotal': total_return,
                'RetPrice': price_return,
                'RetCurncy': currency_return,
                'ProductCurrency': 'USD',
                'YldWorstE': (oas_spread / 10000) + 0.04,  # Yield approximation
                'CouponRate': np.random.choice([2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]),
                'CallableFlag': np.random.choice(['Y', 'N'], p=[0.3, 0.7]) if sector == 'Corporate' else 'N'
            }
            
            bonds.append(bond)
    
    df = pd.DataFrame(bonds)
    print(f"✅ Generated {len(df)} bonds across {len(df['Sector'].unique())} sectors")
    
    # Show sector distribution
    print("\nSector Distribution:")
    sector_dist = df.groupby('Sector').size()
    for sector, count in sector_dist.items():
        pct = (count / len(df)) * 100
        print(f"  {sector:12s}: {count:4d} bonds ({pct:5.1f}%)")
    
    return df

# =============================================================================
# STEP 3: CALCULATE LINVEST21 SCORES
# =============================================================================

def calculate_linvest21_scores(bloomberg_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate LINVEST21 forward-looking credit scores for all bonds
    """
    print("\n🔧 Calculating LINVEST21 Credit Scores...")
    print("-" * 40)
    
    # Initialize rating engine
    rating_engine = LINVEST21RatingEngine()
    
    # Calculate ratings for all bonds
    results = []
    
    for idx, bond in bloomberg_data.iterrows():
        if idx % 100 == 0:
            print(f"  Processing bond {idx+1}/{len(bloomberg_data)}...", end='\r')
        
        # Calculate LINVEST21 rating
        rating_result = rating_engine.calculate_rating(bond.to_dict())
        
        # Combine with original data
        result = {
            'Cusip': bond['Cusip'],
            'Issuer': bond['Issuer'],
            'Sector': bond['Sector'],
            'Bloomberg_Rating': bond['QualityB'],
            'Maturity': bond['Maturity'],
            'Duration': bond['ISMA_MDur'],
            'OAS_Spread': bond['OAS_bp'],
            'Market_Value': bond['MrktValue'],
            **rating_result
        }
        results.append(result)
    
    print(f"\n✅ Calculated scores for {len(results)} bonds")
    
    return pd.DataFrame(results)

# =============================================================================
# STEP 4: VALIDATE SCORES
# =============================================================================

def validate_scores(ratings_df: pd.DataFrame, bloomberg_data: pd.DataFrame) -> pd.DataFrame:
    """
    Validate LINVEST21 scores against market data
    """
    print("\n🔍 Validating Scores...")
    print("-" * 40)
    
    validation_framework = ValidationFramework()
    
    # Sample validation for first 10 bonds
    sample_size = min(10, len(ratings_df))
    
    for i in range(sample_size):
        rating = ratings_df.iloc[i]
        bond = bloomberg_data.iloc[i]
        
        # Validate against Bloomberg data
        validation_result = validation_framework.validate_rating(
            rating.to_dict(),
            bond.to_dict()
        )
        
        # Add validation status to ratings
        ratings_df.loc[i, 'Validation_Status'] = validation_result.get('overall_status', 'UNKNOWN')
    
    # Show validation summary
    if 'Validation_Status' in ratings_df.columns:
        validation_summary = ratings_df['Validation_Status'].value_counts()
        print("\nValidation Summary (sample):")
        for status, count in validation_summary.items():
            print(f"  {status}: {count}")
    
    return ratings_df

# =============================================================================
# STEP 5: QUINTILE ANALYSIS
# =============================================================================

def analyze_by_quintiles(ratings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze LINVEST21 scores by quintiles
    """
    print("\n📈 QUINTILE ANALYSIS")
    print("=" * 80)
    
    # Add quintile classification
    ratings_df['Score_Quintile'] = pd.qcut(
        ratings_df['final_score'], 
        q=5, 
        labels=['Q1 (Lowest)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest)']
    )
    
    # Calculate quintile statistics
    quintile_stats = []
    
    for quintile in ['Q1 (Lowest)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest)']:
        q_data = ratings_df[ratings_df['Score_Quintile'] == quintile]
        
        stats = {
            'Quintile': quintile,
            'Count': len(q_data),
            'Avg_Score': q_data['final_score'].mean(),
            'Min_Score': q_data['final_score'].min(),
            'Max_Score': q_data['final_score'].max(),
            'Avg_Spread': q_data['OAS_Spread'].mean(),
            'Avg_Duration': q_data['Duration'].mean(),
            'Total_MV_$B': q_data['Market_Value'].sum() / 1e9,
            'Most_Common_Rating': q_data['linvest21_rating'].mode()[0] if len(q_data) > 0 else 'N/A',
            'Top_Sector': q_data['Sector'].value_counts().index[0] if len(q_data) > 0 else 'N/A'
        }
        quintile_stats.append(stats)
    
    quintile_df = pd.DataFrame(quintile_stats)
    
    # Print formatted table
    print("\n" + "─" * 120)
    print(f"{'Quintile':15} {'Count':>6} {'Avg Score':>10} {'Score Range':>20} {'Avg Spread':>12} {'Avg Duration':>12} {'Market Val $B':>14} {'Top Rating':>12} {'Top Sector':>12}")
    print("─" * 120)
    
    for _, row in quintile_df.iterrows():
        score_range = f"{row['Min_Score']:.1f}-{row['Max_Score']:.1f}"
        print(f"{row['Quintile']:15} {row['Count']:6d} {row['Avg_Score']:10.2f} {score_range:>20} {row['Avg_Spread']:12.1f} {row['Avg_Duration']:12.2f} {row['Total_MV_$B']:14.1f} {row['Most_Common_Rating']:>12} {row['Top_Sector']:>12}")
    
    print("─" * 120)
    
    return quintile_df

# =============================================================================
# STEP 6: DETAILED BOND LISTING BY QUINTILE
# =============================================================================

def print_detailed_quintile_report(ratings_df: pd.DataFrame):
    """
    Print detailed bond listings for each quintile
    """
    print("\n📊 DETAILED BOND LISTINGS BY QUINTILE")
    print("=" * 80)
    
    for quintile in ['Q5 (Highest)', 'Q4', 'Q3', 'Q2', 'Q1 (Lowest)']:
        q_data = ratings_df[ratings_df['Score_Quintile'] == quintile].sort_values('final_score', ascending=False)
        
        print(f"\n{'='*80}")
        print(f"{quintile} - Top 10 Bonds")
        print(f"{'='*80}")
        print(f"{'CUSIP':12} {'Issuer':25} {'Sector':12} {'LINVEST21':11} {'Score':>7} {'Bloomberg':10} {'Spread':>8} {'Duration':>9}")
        print("-" * 80)
        
        for idx, bond in q_data.head(10).iterrows():
            issuer = bond['Issuer'][:23] + '..' if len(bond['Issuer']) > 25 else bond['Issuer']
            print(f"{bond['Cusip']:12} {issuer:25} {bond['Sector']:12} {bond['linvest21_rating']:11} {bond['final_score']:7.2f} {bond['Bloomberg_Rating']:10} {bond['OAS_Spread']:8.1f} {bond['Duration']:9.2f}")

# =============================================================================
# STEP 7: RISK METRICS BY QUINTILE
# =============================================================================

def calculate_risk_metrics(ratings_df: pd.DataFrame):
    """
    Calculate forward-looking risk metrics by quintile
    """
    print("\n⚠️ FORWARD-LOOKING RISK METRICS BY QUINTILE")
    print("=" * 80)
    
    risk_metrics = []
    
    for quintile in ['Q1 (Lowest)', 'Q2', 'Q3', 'Q4', 'Q5 (Highest)']:
        q_data = ratings_df[ratings_df['Score_Quintile'] == quintile]
        
        # Calculate risk metrics
        metrics = {
            'Quintile': quintile,
            'Default_Risk': 'High' if 'Q1' in quintile else ('Medium' if 'Q2' in quintile or 'Q3' in quintile else 'Low'),
            'Spread_Risk_bp': q_data['OAS_Spread'].std() if len(q_data) > 1 else 0,
            'Duration_Risk': q_data['Duration'].std() if len(q_data) > 1 else 0,
            'Concentration_Risk': 1 - (q_data['Sector'].value_counts() / len(q_data)).pow(2).sum(),  # HHI
            'Liquidity_Score': 100 - int(quintile[1]) * 20 if quintile.startswith('Q') else 50,
            'Recommended_Action': 'Reduce/Avoid' if 'Q1' in quintile else ('Monitor' if 'Q2' in quintile else ('Hold' if 'Q3' in quintile else 'Overweight'))
        }
        risk_metrics.append(metrics)
    
    risk_df = pd.DataFrame(risk_metrics)
    
    print("\n" + "─" * 110)
    print(f"{'Quintile':15} {'Default Risk':>12} {'Spread Vol':>12} {'Duration Vol':>13} {'Concentration':>14} {'Liquidity':>11} {'Action':>15}")
    print("─" * 110)
    
    for _, row in risk_df.iterrows():
        print(f"{row['Quintile']:15} {row['Default_Risk']:>12} {row['Spread_Risk_bp']:12.1f} {row['Duration_Risk']:13.2f} {row['Concentration_Risk']:14.3f} {row['Liquidity_Score']:11.0f} {row['Recommended_Action']:>15}")
    
    print("─" * 110)

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Execute the complete US AGG credit scoring workflow
    """
    
    print("\n🚀 STARTING US AGG CREDIT SCORING WORKFLOW")
    print("=" * 80)
    
    # Step 1: Generate US AGG sample data
    bloomberg_data = generate_us_agg_sample_data(n_bonds=500)
    
    # Step 2: Calculate LINVEST21 scores
    ratings_df = calculate_linvest21_scores(bloomberg_data)
    
    # Step 3: Validate scores (sample)
    ratings_df = validate_scores(ratings_df, bloomberg_data)
    
    # Step 4: Quintile analysis
    quintile_stats = analyze_by_quintiles(ratings_df)
    
    # Step 5: Detailed listings
    print_detailed_quintile_report(ratings_df)
    
    # Step 6: Risk metrics
    calculate_risk_metrics(ratings_df)
    
    # Summary statistics
    print("\n📊 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Bonds Analyzed: {len(ratings_df):,}")
    print(f"Total Market Value: ${ratings_df['Market_Value'].sum()/1e12:.2f} Trillion")
    print(f"Average LINVEST21 Score: {ratings_df['final_score'].mean():.2f}")
    print(f"Score Standard Deviation: {ratings_df['final_score'].std():.2f}")
    print(f"Average OAS Spread: {ratings_df['OAS_Spread'].mean():.1f} bp")
    print(f"Average Duration: {ratings_df['Duration'].mean():.2f} years")
    
    # Rating distribution
    print("\nLINVEST21 Rating Distribution:")
    rating_dist = ratings_df['linvest21_rating'].value_counts().head(10)
    for rating, count in rating_dist.items():
        pct = (count / len(ratings_df)) * 100
        bar = '█' * int(pct/2)
        print(f"  {rating:11s}: {count:4d} ({pct:5.1f}%) {bar}")
    
    print("\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    # Save results to CSV for further analysis
    output_file = 'us_agg_linvest21_scores.csv'
    ratings_df.to_csv(output_file, index=False)
    print(f"\n💾 Results saved to: {output_file}")
    
    return ratings_df, quintile_stats

if __name__ == "__main__":
    ratings_df, quintile_stats = main()