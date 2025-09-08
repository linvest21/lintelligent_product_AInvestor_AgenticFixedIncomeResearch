# LINVEST21 Credit Rating System - Quick Reference Guide

## 🎯 Official 19-Notch Rating Scale

### Investment Grade Ratings (Score 65-100)

| Rating | Score | S&P | Moody's | Default % | Risk Level |
|--------|-------|-----|---------|-----------|------------|
| **LIN-AAA** | 95-100 | AAA | Aaa | <0.01% | Minimal |
| **LIN-AA+** | 90-94 | AA+ | Aa1 | 0.01-0.02% | Very Low |
| **LIN-AA** | 87-89 | AA | Aa2 | 0.02-0.03% | Very Low |
| **LIN-AA-** | 84-86 | AA- | Aa3 | 0.03-0.05% | Low |
| **LIN-A+** | 81-83 | A+ | A1 | 0.05-0.08% | Low |
| **LIN-A** | 78-80 | A | A2 | 0.08-0.12% | Low-Medium |
| **LIN-A-** | 75-77 | A- | A3 | 0.12-0.20% | Medium |
| **LIN-BBB+** | 72-74 | BBB+ | Baa1 | 0.20-0.35% | Medium |
| **LIN-BBB** | 68-71 | BBB | Baa2 | 0.35-0.60% | Medium |
| **LIN-BBB-** | 65-67 | BBB- | Baa3 | 0.60-1.00% | Medium-High |

### Non-Investment Grade Ratings (Score 0-64)

| Rating | Score | S&P | Moody's | Default % | Risk Level |
|--------|-------|-----|---------|-----------|------------|
| **LIN-BB+** | 55-64 | BB+ | Ba1 | 1.00-2.00% | High |
| **LIN-BB** | 50-54 | BB | Ba2 | 2.00-4.00% | High |
| **LIN-BB-** | 45-49 | BB- | Ba3 | 4.00-6.00% | High |
| **LIN-B+** | 35-44 | B+ | B1 | 6.00-8.00% | Very High |
| **LIN-B** | 30-34 | B | B2 | 8.00-12.00% | Very High |
| **LIN-B-** | 25-29 | B- | B3 | 12.00-18.00% | Very High |
| **LIN-CCC+** | 15-24 | CCC+ | Caa1 | 18.00-25.00% | Extreme |
| **LIN-CCC** | 10-14 | CCC | Caa2 | 25.00-35.00% | Extreme |
| **LIN-CCC-** | 0-9 | CCC- | Caa3 | >35.00% | Default Imminent |

## 📊 Grade Categories

### Prime (Score 95-100)
- **Ratings**: LIN-AAA
- **Characteristics**: Exceptional quality, virtually risk-free
- **Typical Issuers**: None currently in market environment

### High Grade (Score 84-94)
- **Ratings**: LIN-AA+, LIN-AA, LIN-AA-
- **Characteristics**: Superior to excellent quality, minimal risk
- **Typical Issuers**: Top sovereigns (in stable conditions)

### Upper Medium Grade (Score 75-83)
- **Ratings**: LIN-A+, LIN-A, LIN-A-
- **Characteristics**: Strong to good quality, low to medium risk
- **Typical Issuers**: Strong corporates, quality municipals

### Lower Medium Grade (Score 65-74)
- **Ratings**: LIN-BBB+, LIN-BBB, LIN-BBB-
- **Characteristics**: Adequate quality, medium risk
- **Typical Issuers**: Average corporates, weaker sovereigns

### Non-Investment Grade (Score 45-64)
- **Ratings**: LIN-BB+, LIN-BB, LIN-BB-
- **Characteristics**: Speculative, substantial risk
- **Typical Issuers**: High yield bonds, stressed credits

### Highly Speculative (Score 25-44)
- **Ratings**: LIN-B+, LIN-B, LIN-B-
- **Characteristics**: High to very high risk
- **Typical Issuers**: Distressed companies, emerging markets

### Distressed (Score 0-24)
- **Ratings**: LIN-CCC+, LIN-CCC, LIN-CCC-
- **Characteristics**: Extreme risk to default imminent
- **Typical Issuers**: Near-default situations

## 🔄 Key Conversions

### Investment Grade Cutoff
- **LINVEST21**: LIN-BBB- (Score 65)
- **S&P**: BBB-
- **Moody's**: Baa3

### Speculative Grade Start
- **LINVEST21**: LIN-BB+ (Score 64 and below)
- **S&P**: BB+
- **Moody's**: Ba1

## 📈 Scoring Methodology

```
Total Score (0-100) = 
  40% × Quantitative Factors +
  35% × Agency Rating Translation +
  25% × Sector Dynamics +
  15% × Alpha Factors
```

### Component Breakdown:
- **Quantitative (40%)**: Duration, Spread, Liquidity
- **Agency (35%)**: Bloomberg rating, Trajectory, Outlook
- **Sector (25%)**: Industry risk, Momentum, Peer comparison
- **Alpha (15%)**: Price momentum, Stability, Currency risk

## 🎯 Quick Score Interpretation

| Score Range | Interpretation | Investment Action |
|-------------|---------------|-------------------|
| **95-100** | Exceptional (AAA) | Strong Buy |
| **84-94** | Superior (AA range) | Buy |
| **75-83** | Strong (A range) | Overweight |
| **65-74** | Adequate (BBB range) | Hold |
| **45-64** | Speculative (BB range) | Underweight |
| **25-44** | High Risk (B range) | Sell |
| **0-24** | Distressed (CCC range) | Avoid |

## 📌 Important Notes

1. **Forward-Looking**: LINVEST21 ratings are forward-looking, not historical
2. **Dynamic**: Ratings adjust for current market conditions
3. **Relative**: Scores consider peer group and sector dynamics
4. **Comprehensive**: Incorporates multiple risk factors beyond traditional metrics

## 🔗 Configuration Files

- **JSON Config**: `config/linvest21_rating_config.json`
- **Python Constants**: `config/rating_constants.py`
- **Full Documentation**: `docs/LINVEST21_RATING_SCALE_EXPLANATION.md`

---

*Version 1.0.0 | LINVEST21 Proprietary Rating System*