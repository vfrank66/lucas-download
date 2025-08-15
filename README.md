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

### Basic Usage (Downloads 1992-2005 by default)
```bash
python main.py
```

### Custom Date Range
```bash
# Download from 1995 to 2000 with default 40 threads
python main.py 1995 2000

# Download from 1992 to 2005 with 20 threads
python main.py 1992 2005 20
```

### Command Line Arguments
- **First argument**: Start year (default: 1992)
- **Second argument**: End year (default: 2005)
- **Third argument**: Number of concurrent threads (default: 40)

## Output

- **Downloads folder**: `./downloads/YEAR/MONTH/DAY/`
- **Progress file**: `download_progress.json` (tracks completed downloads)
- **Log file**: `camara_downloader.log`

## Example Output Structure
```
downloads/
├── 1992/
│   ├── 01/
│   │   ├── 15/
│   │   │   └── DCD0019920115000490000.PDF
│   │   └── 16/
│   │       └── DCD0019920116000490000.PDF
│   └── 02/
│       └── 01/
│           └── DCD0019920201000490000.PDF
├── 1993/
│   └── 01/
│       └── 01/
└── 2005/
    └── 12/
        └── 31/
```

The program automatically resumes from where it left off if interrupted. Files are organized in a year/month/day structure for easy navigation and traversal.
