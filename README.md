# LINVEST21 Agentic Fixed Income Research Platform

## Credit Rating Research System (v1.0)

A proprietary forward-looking credit rating system that analyzes fixed income securities, with particular focus on the Bloomberg US Aggregate benchmark.

## 🎯 Key Features

- **Multi-factor credit scoring** with 40% Quantitative, 35% Agency, 25% Sector, 15% Alpha weighting
- **Forward-looking analysis** identifying market inefficiencies
- **Bloomberg data integration** for comprehensive market coverage  
- **Traditional rating format** (LIN-AAA through LIN-CCC)
- **High-performance processing** (>10 bonds/second)

## 📁 Project Structure

```
lintelligent_product_AInvestor_AgenticFixedIncomeResearch/
├── src/                      # Core source code
│   ├── core/                 # Rating engine
│   ├── data/                 # Bloomberg connector
│   ├── validation/           # Quality control
│   ├── models/               # Database models
│   ├── api/                  # REST API endpoints
│   └── etl/                  # Data pipeline
├── tests/                    # Test suites
│   ├── integration/          # Integration tests
│   ├── stress/               # Performance tests
│   └── *.py                  # Unit tests
├── examples/                 # Demo scripts
│   ├── demo_us_agg_enhanced.py     # Enhanced US AGG analysis
│   ├── demo_us_agg_workflow.py     # Complete workflow demo
│   └── demo_specification_compliance.py # Spec compliance demo
├── docs/                     # Documentation
│   ├── TEST_RESULTS_SUMMARY.md     # Test results
│   ├── rating_summary_report.md    # US AGG analysis report
│   └── jira_update_AINV-711.md    # JIRA ticket update
├── scripts/                  # Utility scripts
│   └── jira_update_script.sh       # JIRA automation
├── utilities/                # Test utilities
│   ├── test_complete_workflow.py   # Standalone workflow test
│   ├── run_validation_tests.py     # Validation test runner
│   └── debug_*.py                  # Debug utilities
├── requirements.txt          # Python dependencies
└── CLAUDE.md                # AI assistant configuration
```

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone [repository-url]
cd lintelligent_product_AInvestor_AgenticFixedIncomeResearch

# Install dependencies
pip install -r requirements.txt
```

### Run Examples

```bash
# Analyze US AGG benchmark
python examples/demo_us_agg_enhanced.py

# Run complete workflow
python examples/demo_us_agg_workflow.py

# Test specification compliance
python examples/demo_specification_compliance.py
```

### Run Tests

```bash
# Run all tests
python utilities/test_complete_workflow.py

# Run validation tests
python utilities/run_validation_tests.py
```

## 📊 Key Results

- Processes Bloomberg US AGG benchmark (500 bonds)
- Identifies 60% of bonds as speculative grade (vs 0% by Bloomberg)
- 67.6% divergence rate from Bloomberg ratings (alpha opportunities)
- Performance: <0.1 sec/bond (10x faster than target)

## 🔍 Core Components

### Rating Engine (`src/core/rating_engine.py`)
Multi-factor scoring model combining quantitative metrics, agency ratings, sector dynamics, and alpha factors.

### Bloomberg Connector (`src/data/bloomberg_connector.py`)
Data integration layer for Bloomberg terminal data with mock generation capabilities.

### Validation Framework (`src/validation/quality_control.py`)
Quality control system ensuring rating consistency and identifying divergences.

### API Layer (`src/api/main.py`)
RESTful endpoints for rating calculation and batch processing.

## 📈 LINVEST21 Official Credit Rating Scale

### Complete 19-Notch Rating System

| Score Range | LINVEST21 Rating | S&P/Moody's | Grade Category | Default Probability | Description |
|-------------|------------------|-------------|----------------|-------------------|-------------|
| **95-100** | **LIN-AAA** | AAA/Aaa | Prime | <0.01% | Exceptional credit quality, virtually no default risk |
| **90-94** | **LIN-AA+** | AA+/Aa1 | High Grade | 0.01-0.02% | Superior credit quality, minimal risk |
| **87-89** | **LIN-AA** | AA/Aa2 | High Grade | 0.02-0.03% | Excellent credit quality, very low risk |
| **84-86** | **LIN-AA-** | AA-/Aa3 | High Grade | 0.03-0.05% | Very strong credit quality |
| **81-83** | **LIN-A+** | A+/A1 | Upper Medium Grade | 0.05-0.08% | Strong credit quality, low risk |
| **78-80** | **LIN-A** | A/A2 | Upper Medium Grade | 0.08-0.12% | Good credit quality, susceptible to economic conditions |
| **75-77** | **LIN-A-** | A-/A3 | Upper Medium Grade | 0.12-0.20% | Good credit quality, more susceptible to changes |
| **72-74** | **LIN-BBB+** | BBB+/Baa1 | Lower Medium Grade | 0.20-0.35% | Adequate credit quality, moderate risk |
| **68-71** | **LIN-BBB** | BBB/Baa2 | Lower Medium Grade | 0.35-0.60% | Adequate payment capacity, adverse conditions possible |
| **65-67** | **LIN-BBB-** | BBB-/Baa3 | Lower Medium Grade | 0.60-1.00% | Lowest investment grade, vulnerable to adverse conditions |
| **55-64** | **LIN-BB+** | BB+/Ba1 | Non-Investment Grade | 1.00-2.00% | Speculative, substantial credit risk |
| **50-54** | **LIN-BB** | BB/Ba2 | Non-Investment Grade | 2.00-4.00% | Speculative, significant ongoing uncertainty |
| **45-49** | **LIN-BB-** | BB-/Ba3 | Non-Investment Grade | 4.00-6.00% | Speculative, high credit risk |
| **35-44** | **LIN-B+** | B+/B1 | Highly Speculative | 6.00-8.00% | Highly speculative, likely to fulfill obligations |
| **30-34** | **LIN-B** | B/B2 | Highly Speculative | 8.00-12.00% | Highly speculative, high credit risk |
| **25-29** | **LIN-B-** | B-/B3 | Highly Speculative | 12.00-18.00% | Very high credit risk, vulnerable |
| **15-24** | **LIN-CCC+** | CCC+/Caa1 | Substantial Risk | 18.00-25.00% | Substantial credit risk, vulnerable to default |
| **10-14** | **LIN-CCC** | CCC/Caa2 | Extremely Speculative | 25.00-35.00% | Very high levels of credit risk |
| **0-9** | **LIN-CCC-** | CCC-/Caa3 | Default Imminent | >35.00% | Near default with little recovery prospect |

### Investment Grade vs Non-Investment Grade

- **Investment Grade**: LIN-AAA through LIN-BBB- (Score 65-100)
- **Non-Investment Grade (Speculative)**: LIN-BB+ and below (Score <65)
- **Highly Speculative**: LIN-B+ and below (Score <45)
- **Distressed**: LIN-CCC+ and below (Score <25)

## 📝 Documentation

- [Test Results Summary](docs/TEST_RESULTS_SUMMARY.md)
- [Rating Analysis Report](docs/rating_summary_report.md)
- [JIRA Update](docs/jira_update_AINV-711.md)

## 🛠️ Development

- Python 3.8+
- FastAPI for REST API
- SQLAlchemy for database ORM
- Pandas/NumPy for data analysis

## 📄 License

Proprietary - LINVEST21

## 🤝 Contributing

Please see CLAUDE.md for development guidelines and JIRA workflow requirements.

---

**Version**: 1.0.0  
**Status**: Production Ready  
**JIRA Ticket**: AINV-711