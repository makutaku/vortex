# Vortex Architecture

## Overview

Vortex follows Clean Architecture principles with clear separation of concerns:

```
src/vortex/
├── models/       # Domain models (Instrument, Future, Stock, etc.)
├── services/     # Business services (downloaders, processors)
├── providers/    # External data provider implementations
├── storage/      # Data storage implementations
├── cli/          # Command-line interface
└── shared/       # Cross-cutting concerns (logging, exceptions, etc.)
```

## Key Components

### Domain Models (`models/`)
- `Instrument`: Base class for tradeable instruments
- `Future`, `Stock`, `Forex`: Specific instrument types
- `PriceSeries`: Time series data representation

### Business Services (`services/`)
- `UpdatingDownloader`: Main downloader with existing data checks
- `BackfillDownloader`: Historical data range downloads
- `DownloadJob`: Individual download task representation

### Data Providers (`providers/`)
- `BarchartDataProvider`: Barchart.com integration
- `YahooDataProvider`: Yahoo Finance API
- `IbkrDataProvider`: Interactive Brokers TWS/Gateway

### Storage Layer (`storage/`)
- `CsvStorage`: Primary CSV format storage
- `ParquetStorage`: Backup Parquet format
- `FileStorage`: Base file storage abstraction

## Data Flow

1. CLI receives user commands
2. Configuration loaded and validated
3. Appropriate downloader created based on provider
4. Instrument definitions processed into download jobs
5. Data downloaded and stored in multiple formats
6. Existing data checked to avoid duplicates