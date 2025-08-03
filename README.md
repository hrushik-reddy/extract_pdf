# PDF Text Extractor API

A FastAPI server for extracting text from PDF files using multiple extraction methods including pdfplumber, PyMuPDF, and PyPDF2.

## Features

- **Multiple extraction methods**: Automatically tries the best available method or allows you to specify one
- **Smart fallback**: Falls back to other methods if the primary one fails
- **Text cleaning**: Automatically cleans and normalizes extracted text
- **RESTful API**: Easy-to-use endpoints with proper error handling
- **CORS enabled**: Ready for web applications

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the server on port 8003:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

The server will be available at `http://localhost:8003`

## API Endpoints

### GET /
Returns API information and available endpoints.

### GET /health
Health check endpoint.

### POST /extract
Extract text from PDF using the best available method.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: PDF file upload

**Response:**
```json
{
  "success": true,
  "message": "Successfully extracted text from 5 pages",
  "total_pages": 5,
  "extraction_method": "pdfplumber",
  "pages": [
    {
      "page_num": 1,
      "content": "Extracted text content..."
    }
  ]
}
```

### POST /extract/{method}
Extract text using a specific method (`pdfplumber`, `pymupdf`, or `pypdf2`).

## Usage Examples

### Using curl:
```bash
# Extract using best available method
curl -X POST "http://localhost:8003/extract" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# Extract using specific method
curl -X POST "http://localhost:8003/extract/pdfplumber" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Using Python requests:
```python
import requests

# Extract text from PDF
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8003/extract', files=files)
    result = response.json()
    
    if result['success']:
        for page in result['pages']:
            print(f"Page {page['page_num']}: {page['content'][:100]}...")
```

## Interactive API Documentation

Once the server is running, visit `http://localhost:8003/docs` for interactive API documentation powered by Swagger UI.

## Extraction Methods

1. **pdfplumber** (preferred): Best for layout preservation and formatting
2. **PyMuPDF** (fast): High-quality and fast extraction
3. **PyPDF2** (fallback): Reliable fallback when other methods fail

The server automatically tries methods in order and uses the first one that successfully extracts text.
