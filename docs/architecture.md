# System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite)"]
        LP[Login Page]
        DP[Dashboard]
        AP[Analysis Page]
        MI[Model Insights]
        PP[Portfolio]
    end

    subgraph Backend["Backend (FastAPI)"]
        AR[Auth Router]
        SR[Stock Router]
        PR[Predict Router]
        SER[Sentiment Router]
        WR[Watchlist Router]
        IR[Internal Router]
    end

    subgraph ML["ML Pipeline"]
        FE[Feature Engineering]
        LR[Linear Regression]
        RF[Random Forest]
        XG[XGBoost]
        LS[LSTM]
        MC[Model Comparison]
    end

    subgraph Data["Data Layer"]
        DB[(PostgreSQL)]
        YF[Yahoo Finance API]
        GN[Google News RSS]
    end

    Frontend -->|REST API| Backend
    AR -->|JWT| DB
    SR --> DB
    PR --> ML
    SER --> GN
    WR --> DB
    IR --> YF
    IR --> DB
    ML --> DB
    FE --> LR & RF & XG & LS
    MC --> LR & RF & XG & LS
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend API
    participant ML as ML Model
    participant DB as PostgreSQL
    participant YF as Yahoo Finance

    U->>F: Search stock (e.g., AAPL)
    F->>B: GET /api/stocks/AAPL
    B->>DB: Query stock_prices
    DB-->>B: Price history
    B-->>F: JSON response
    F-->>U: Chart + Info Cards

    U->>F: Click "Predict"
    F->>B: POST /api/predict {symbol: "AAPL"}
    B->>DB: Fetch recent prices
    B->>ML: Feature engineering + predict
    ML-->>B: Prediction + confidence
    B-->>F: PredictResponse
    F-->>U: Prediction card with metrics
```

## Directory Structure

```
stock-predictor/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── auth.py              # JWT & password utilities
│   ├── database.py          # Connection pool management
│   ├── helpers.py           # Yahoo Finance fetch + refresh logic
│   ├── models.py            # Pydantic request/response models
│   ├── sentiment.py         # News sentiment analysis (VADER)
│   └── routers/
│       ├── auth.py          # /api/auth/* endpoints
│       ├── stocks.py        # /api/stocks/* endpoints
│       ├── predictions.py   # /api/predict endpoint
│       ├── sentiment.py     # /api/sentiment/* endpoint
│       ├── watchlist.py     # /api/watchlist/* endpoints
│       └── internal.py      # /internal/* admin endpoints
├── frontend/
│   └── src/
│       ├── components/      # Reusable UI components
│       ├── context/         # React contexts (Auth)
│       ├── pages/           # Route pages
│       └── lib/             # API client
├── ml_model/
│   ├── train.py             # Multi-model training pipeline
│   ├── feature_engineering.py # Technical indicators
│   ├── lstm_model.py        # LSTM deep learning model
│   ├── model_comparison.py  # Chart generation
│   └── results/             # Comparison outputs
├── data_pipeline/
│   ├── fetch_data.py        # S&P 500 + NIFTY 500 data fetcher
│   └── db_setup.sql         # Database schema
├── tests/                   # Unit tests
└── docs/                    # Documentation
```

## Technology Justification

| Technology | Purpose | Why Chosen |
|-----------|---------|------------|
| FastAPI | Backend API | Async support, auto-docs, Pydantic validation, modern Python |
| React + Vite | Frontend | Component-based UI, fast HMR, rich ecosystem |
| PostgreSQL | Database | ACID compliance, time-series queries, Supabase hosting |
| scikit-learn | ML (classical) | Industry standard, well-documented, multiple algorithms |
| XGBoost | ML (gradient boosting) | State-of-the-art for tabular data, feature importance |
| TensorFlow/Keras | ML (deep learning) | LSTM for sequential data, GPU acceleration |
| VADER | Sentiment analysis | Pre-trained for social media/financial text, no API key |
| JWT + bcrypt | Authentication | Stateless auth, secure password hashing |
