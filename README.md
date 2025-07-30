# 🏗️ Building Permit Intelligence Platform

An automated system for fetching, processing, and searching building permits from multiple Florida counties using vector embeddings and semantic search.

## 🎯 Features

- **Multi-County Data Collection**: Fetches permits from Miami-Dade and Hillsborough counties
- **Intelligent Processing**: Normalizes data across different county formats with geocoding
- **Vector Search**: ChromaDB + OpenAI embeddings for semantic permit search
- **Web Interface**: Streamlit app for intuitive permit discovery
- **Automated Pipeline**: Daily scheduled data collection and processing

## 🏗️ Architecture

```
Building Permit Intelligence Platform
├── Data Fetchers (Miami-Dade API, Hillsborough Web Scraping)
├── Data Processor (Normalization + Geocoding)
├── Vector Database (ChromaDB + OpenAI Embeddings)
└── Search Interface (Streamlit Web App)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OpenAI API Key
- Google Maps API Key (optional, for geocoding)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/barrymjulien/Permit-Intelligence-Platform.git
cd Permit-Intelligence-Platform
```

2. **Set up virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r config/dependencies.txt
```

4. **Configure environment**
```bash
# Create .env file with your API keys
echo "OPENAI_API_KEY=your_openai_key_here" > .env
echo "GOOGLE_MAPS_API_KEY=your_google_maps_key_here" >> .env
```

5. **Run the pipeline**
```bash
# Fetch and process permits from the last day
python main.py --days 1

# Start the search interface
cd src/web_interface
streamlit run streamlit_permit_search.py
```

## 📊 Usage

### Data Pipeline
```bash
# Fetch permits from last 7 days
python main.py --days 7

# Limit to 100 records for testing
python main.py --days 7 --max-records 100
```

### Search Interface
1. Open http://localhost:8501
2. Enter search queries like:
   - "kitchen renovation"
   - "HVAC installation"
   - "new construction in Wimauma"
   - "swimming pool permits"

## 🗂️ Project Structure

```
src/
├── data_fetchers/          # County-specific data collection
│   ├── miamidade_fetch.py  # Miami-Dade API integration
│   └── hillsborough_permits.py  # Hillsborough web scraping
├── processors/             # Data normalization and geocoding
│   └── prepare_permits.py  # Multi-county data standardization
├── database/              # Vector database operations
│   └── upload_to_chroma.py # ChromaDB integration
└── web_interface/         # Search and visualization
    └── streamlit_permit_search.py  # Web search interface

data/
├── raw/                   # Original permit data
├── processed/             # Normalized permit data
├── chroma_db/            # Vector database files
└── cache/                # Geocoding cache

config/
├── pipeline_config.json  # Pipeline configuration
└── dependencies.txt     # Package requirements
```

## 🔧 Configuration

### County Data Sources
- **Miami-Dade**: ArcGIS REST API
- **Hillsborough**: Web scraping (configurable)

### Data Processing
- **Geocoding**: Google Maps API with intelligent caching
- **Normalization**: Standardized schema across counties
- **Embeddings**: OpenAI text-embedding-3-small

## 📈 Current Status

- ✅ **End-to-end pipeline working**
- ✅ **48 permits in database** (geocoded)
- ✅ **Streamlit search interface functional**
- ✅ **Multi-county data normalization**
- ⚠️ **Miami-Dade API**: Needs debugging for recent dates
- 📁 **Hillsborough**: Currently using static data file

## 🎯 Roadmap

### Phase 2: Live Data Sources
- [ ] Debug Miami-Dade API date filtering
- [ ] Implement Hillsborough web scraping
- [ ] QC testing with live data

### Phase 3: Production Deployment
- [ ] Daily automated scheduling (GitHub Actions)
- [ ] Production Streamlit deployment
- [ ] Performance optimization

### Phase 4: Expansion
- [ ] Additional Florida counties
- [ ] Advanced analytics dashboard
- [ ] API endpoints for external access

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Miami-Dade County Open Data Portal
- Hillsborough County Building Department
- OpenAI for embedding models
- Streamlit for the web interface framework
