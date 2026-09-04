# ⚡ PriceSense

### AI-Based Real-Time E-Commerce Price Comparison and Market Analysis System

PriceSense is a web-based price intelligence system designed to compare product prices across multiple quick-commerce and e-commerce platforms.

The system searches for a requested product, collects available pricing information from supported platforms, matches similar products, and presents the comparison through an interactive dashboard.

Currently supported platforms:

- 🟢 Blinkit
- 🟣 Zepto
- 🟠 Swiggy Instamart
- 🔵 BigBasket

---

## 🚀 Features

- 🔍 Product-based price search
- ⚡ Real-time price extraction using Playwright
- 🛒 Multi-platform price comparison
- 📊 Interactive price comparison dashboard
- 🏆 Automatic identification of the cheapest available platform
- 📦 Product-name and pack-size matching
- 🔄 Dynamic webpage handling
- 📈 Price comparison visualization
- 🟢 Live price indication
- 🟡 Estimated price indication when sufficient legitimate price data is available
- ⚪ Unavailable status when reliable pricing information cannot be obtained
- 📱 Responsive web interface

---

## 🏗️ System Architecture

```text
                    ┌──────────────────┐
                    │      User        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  PriceSense UI   │
                    │ HTML / CSS / JS  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Flask Server   │
                    │     app.py       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Scraping Engine │
                    │   scraper.py     │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
     ┌─────────┐        ┌─────────┐       ┌───────────┐
     │ Blinkit │        │  Zepto  │       │ Instamart │
     └─────────┘        └─────────┘       └───────────┘
                             │
                             ▼
                       ┌───────────┐
                       │ BigBasket │
                       └───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Product Matching │
                    │ & Price Analysis │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Comparison Result│
                    └──────────────────┘
