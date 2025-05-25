# Brazilian Chamber of Deputies PDF Scraper

A Python program to automatically download PDF documents from the Brazilian Chamber of Deputies (Câmara dos Deputados) website.

## Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python main.py
```

### Custom Options
```bash
# Download 5 years back with 30 threads
python main.py 5 30

# Download 1 year back with 20 threads  
python main.py 1 20
```

### Command Line Arguments
- **First argument**: Number of years back to download (default: 2)
- **Second argument**: Number of concurrent threads (default: 40)

## Output

- **Downloads folder**: `./downloads/YEAR/MONTH_NAME/`
- **Progress file**: `download_progress.json` (tracks completed downloads)
- **Log file**: `camara_downloader.log`

## Example Output Structure
```
downloads/
├── 2023/
│   ├── 01_Janeiro/
│   │   └── DCD0020230101000490000.PDF
│   └── 02_Fevereiro/
└── 2024/
    └── 01_Janeiro/
```

The program automatically resumes from where it left off if interrupted.
