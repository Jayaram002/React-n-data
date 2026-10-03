# React n Data: AI-Scored Two-Sided Data Marketplace (MVP)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite_%2B_TS-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Styles-TailwindCSS-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_%2F_SQLite-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org)
[![Alembic](https://img.shields.io/badge/Migrations-Alembic-orange?style=flat-square)](https://alembic.sqlalchemy.org)
[![Pytest](https://img.shields.io/badge/Tests-32%2F32_Passing-brightgreen?style=flat-square&logo=pytest)](https://pytest.org)

**React n Data** is a production-grade, two-sided data marketplace where contributors upload image and tabular datasets that are evaluated by **Gemma AI** models and rule-based pre-checks. The system calculates a multi-dimensional **Trust Score (0–100)**, suggests dynamic commercial pricing with bounded contributor overrides ($0.8\times - 1.3\times$), aggregates datasets across taxonomy domains for enterprise agency buyers, executes payments through an **80/20 double-entry financial ledger**, and automates dispute-window-protected payouts.

---

## 🏗 System Architecture & 8-Phase Roadmap

```
+--------------------------------------------------------------------------------------------------+
|                                    REACT N DATA PLATFORM                                         |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   CONTRIBUTOR PORTAL                 MARKETPLACE & AGENCY                     ADMIN CONSOLE      |
|  - File Ingestion & Drag-Drop       - Multi-Domain Discovery Filter        - Moderation Queue    |
|  - Consent & License Declarations   - Safe Watermarked/Masked Previews     - Taxonomy Tree Editor|
|  - Gemma AI Trust Score Review      - Mock Checkout Sandbox                - Payout Approval Flow|
|  - Wallet, Escrow & Payouts         - Licensed Dataset Streaming           - Revenue Analytics   |
|                                                                                                  |
+-------------------------------------------------+------------------------------------------------+
                                                  |
                                    REST API & JWT Role-Based Auth
                                                  |
+-------------------------------------------------v------------------------------------------------+
|                                   FASTAPI BACKEND ENGINE                                         |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|  [Ingestion & Pre-checks]          [AI Trust Engine]                  [Financial Ledger]         |
|  - Perceptual Hashing (pHash)      - Gemma Classification             - 80/20 Split Engine       |
|  - Tabular PII Masking/Hashing     - 5-Dimension Scorer (0-100)       - Double-Entry Bookkeeping |
|  - Schema & EXIF Stripping         - Piecewise Pricing Engine         - Dispute Escrow Release   |
|                                                                                                  |
+-------------------------------------------------+------------------------------------------------+
                                                  |
                                   Storage & Persistence Layer
                                                  |
+-------------------------------------------------v------------------------------------------------+
|   PostgreSQL / SQLite Database  |  MinIO S3 / Local File Storage  |  Gemma AI (Live / Mock)      |
+--------------------------------------------------------------------------------------------------+
```

### 8 Sequential Implementation Phases
- **Phase 1: Foundation & Auth Scaffold** — Docker Compose, 17 SQLAlchemy models + Alembic migrations, JWT Auth with 3 roles (`contributor`, `agency`, `admin`), Seed taxonomy (11 root domains + 20 subcategories).
- **Phase 2: Ingestion & Pre-checks** — File storage abstraction (Local / S3 MinIO), perceptual image hashing (`pHash`/`dHash`), tabular PII masking & schema inference, consent capture, and safe preview generation.
- **Phase 3: Gemma AI Classification & Trust Scoring** — Gemma AI categorization, confidence routing ($\ge 0.75$ auto-assign, $0.50-0.75$ flagged for review, $<0.50$ held uncategorized), 5-factor Trust Score ($Q \cdot 0.35 + A \cdot 0.20 + U \cdot 0.15 + M \cdot 0.15 + R \cdot 0.15$), piecewise pricing bounds ($0.8\times - 1.3\times$).
- **Phase 4: Marketplace Discovery & Previews** — Agency catalog discovery with search, multi-faceted filtering, cross-contributor domain aggregation, and isolated safe preview rendering.
- **Phase 5: Checkout, Ledger & Licensing** — Mock checkout payment sandbox, 80/20 double-entry ledger bookkeeping, automated commercial license generation, and streaming dataset download with audit trails.
- **Phase 6: Contributor Earnings & Payouts** — Wallet tracking (Pending vs Available), dispute window automated release mechanism, contributor payout request lifecycle, and rejected payout refund engine.
- **Phase 7: Admin Moderation, Taxonomy & Analytics** — Human-in-the-loop admin moderation queue, real-time taxonomy manager with version increments, platform revenue analytics (GMV, net platform fee, payout volume), and comprehensive audit log viewer.
- **Phase 8: Seed Ecosystem, E2E Integration & Verification** — 27 multi-domain datasets across all 11 taxonomy domains, full end-to-end integration test suite, and production build verification.

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Docker & Docker Compose** (Optional for local PostgreSQL & MinIO)

---

### Step 1: Clone & Configure Infrastructure

Start the background database and object storage containers:
```bash
docker compose up -d
```
*(This starts PostgreSQL on port `5432` and MinIO S3 on ports `9000`/`9001`)*

---

### Step 2: Backend Setup

Navigate to the `backend/` directory:
```bash
cd backend
```

Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Run Alembic database migrations:
```bash
alembic upgrade head
```

Seed the marketplace with 27 realistic multi-domain datasets and test accounts:
```bash
python -m app.db.seed_data
```

Start the FastAPI application server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **API Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc UI**: `http://localhost:8000/redoc`

---

### Step 3: Frontend Setup

Open a new terminal and navigate to `frontend/`:
```bash
cd frontend
```

Install frontend packages:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```
- **Frontend Web Application**: `http://localhost:5173`

---

## 👥 Seed Test Accounts & Credentials

The seed script (`app/db/seed_data.py`) automatically generates the following pre-configured user accounts with password `Password123!`:

| Role | Email Address | Password | Description / Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@reactndata.com` | `Password123!` | Full platform administration, moderation queue, taxonomy editor, payout approval, financial analytics |
| **Contributor** | `contributor@reactndata.com` | `Password123!` | Ingest datasets, AI trust scores, manage listings, view wallet earnings, request payouts |
| **Contributor** | `sarah.chen@biovision.io` | `Password123!` | Sample contributor with Health & Biology datasets |
| **Contributor** | `marcus.vance@quantumlab.org` | `Password123!` | Sample contributor with Physics & Quantum datasets |
| **Agency** | `agency@reactndata.com` | `Password123!` | Browse catalog, search & filter, preview datasets, execute sandbox checkouts, download licensed data |
| **Agency** | `data.procure@nexusai.corp` | `Password123!` | Enterprise AI training data procurement agency |

---

## 🧠 Gemma AI Scorer & Dynamic Pricing Engine

### 1. 5-Dimension Trust Score Formulation
$$\text{Trust Score} = 0.35 \cdot Q + 0.20 \cdot A + 0.15 \cdot U + 0.15 \cdot M + 0.15 \cdot R$$

- **$Q$ (Quality - 35%)**: Resolution, null-value ratios, distribution entropy, schema completeness.
- **$A$ (Authenticity - 20%)**: Sensor telemetry variance, camera metadata signature, synthetic artifact scan.
- **$U$ (Uniqueness - 15%)**: Perceptual hash distance ($d_H(\text{pHash}) > 10$) and column schema vector similarity.
- **$M$ (Metadata Accuracy - 15%)**: Alignment between title, tags, column descriptors, and payload contents.
- **$R$ (Contributor Reputation - 15%)**: Historical acceptance rate, moderation track record, dispute history.

### 2. Piecewise Pricing Engine
Suggested commercial pricing is calculated dynamically based on base domain price, AI Trust Score factor, and category demand multipliers:

$$\text{Price}_{\text{suggested}} = \text{Base Price} \times f(\text{Trust Score}) \times \text{Demand Multiplier}$$

$$\text{Contributor Floor} = 0.80 \times \text{Price}_{\text{suggested}} \quad \Big| \quad \text{Contributor Ceiling} = 1.30 \times \text{Price}_{\text{suggested}}$$

---

## 💰 80/20 Double-Entry Ledger Bookkeeping

Every transaction in the marketplace strictly maintains double-entry accounting invariances:
$$\sum \text{Debits} = \sum \text{Credits}$$

When an agency purchases a dataset for **\$100 (10,000 paise)**:
1. **Buyer Account**: Debit \$100.00 (`BUYER_PAYMENT`)
2. **Contributor Escrow**: Credit \$80.00 (`CONTRIBUTOR_CREDIT`, pending dispute window maturity)
3. **Platform Revenue**: Credit \$20.00 (`PLATFORM_FEE`, available immediately)

---

## 🧪 Testing & Verification

### Running Backend Unit & End-to-End Tests
React n Data includes an extensive test suite with **32 comprehensive tests** covering all phases:

```bash
cd backend
python -m pytest -v
```

**Test Suite Coverage Summary:**
- `test_phase1.py`: Auth registration, JWT tokens, RBAC permissions, taxonomy seeding.
- `test_phase2.py`: Storage abstraction, perceptual hashes, EXIF stripping, PII detection, tabular safe previews.
- `test_phase3.py`: Gemma AI classification routing, 5-dimension Trust Scoring, piecewise pricing calculation.
- `test_phase4.py`: Marketplace browsing, search filters, domain cross-aggregation, preview protection.
- `test_phase5.py`: Mock checkout sandbox, 80/20 double-entry ledger verification, licensing, and streaming download logs.
- `test_phase6.py`: Wallet balance calculations, dispute escrow window release, payout request lifecycle.
- `test_phase7.py`: Admin moderation queue actions, category taxonomy management, revenue analytics, audit trail.
- `test_phase8_e2e.py`: **Complete 10-step full marketplace lifecycle integration test** (Contributor onboarding $\to$ Ingestion $\to$ AI Scoring $\to$ Publishing $\to$ Agency Search $\to$ Checkout $\to$ Licensing $\to$ Download $\to$ Payouts $\to$ Platform Analytics).

### Verifying Frontend Build
```bash
cd frontend
npm run build
```
*(Executes TypeScript typecheck `tsc` and compiles the production Vite bundle without warnings).*

---

## 📁 Project Repository Structure

```
REACT HYD/
├── docker-compose.yml              # PostgreSQL and MinIO container definitions
├── README.md                       # Comprehensive system documentation
├── backend/
│   ├── alembic/                    # Alembic migration scripts and version history
│   ├── app/
│   │   ├── api/                    # REST API endpoints (auth, uploads, listings, orders, admin, etc.)
│   │   ├── core/                   # Security, JWT, database session, AI configuration
│   │   ├── db/                     # Initial database setup & multi-domain seed script (seed_data.py)
│   │   ├── models/                 # 17 SQLAlchemy ORM models (User, Upload, Order, Ledger, Audit, etc.)
│   │   ├── schemas/                # Pydantic validation and serialization models
│   │   └── services/               # Core services (Gemma AI, Storage, Ledger, Pricing, Hashing)
│   ├── storage/                    # Local storage fallback directory (uploads & previews)
│   └── tests/                      # Pytest suite (32 unit, integration, and E2E lifecycle tests)
└── frontend/
    ├── src/
    │   ├── api/                    # Axios API client integrations
    │   ├── components/             # Reusable UI widgets, Navbar, StatusBadges, Modal dialogs
    │   ├── context/                # Authentication context and user state
    │   ├── pages/                  # Route views (Marketplace, Upload, Earnings, Admin, MockCheckout)
    │   ├── types/                  # TypeScript interfaces matching backend schemas
    │   ├── App.tsx                 # Root React Router switch
    │   └── main.tsx                # Application bootstrap
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

---

## 📜 License
This project is developed as an MVP data marketplace reference architecture under the MIT License.
