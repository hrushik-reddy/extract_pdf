import logging
import re
from io import BytesIO
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PDF Text Extractor API",
    description="API for extracting text from PDF files using multiple extraction methods",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class PageContent(BaseModel):
    page_num: int
    content: str

class ExtractionResponse(BaseModel):
    success: bool
    message: str
    total_pages: int
    extraction_method: str
    pages: List[PageContent]

class ErrorResponse(BaseModel):
    success: bool
    message: str
    error_type: str

def clean_extracted_text(text: str) -> str:
    """
    Clean and normalize extracted text from PDFs.
    
    Args:
        text: Raw text extracted from PDF
        
    Returns:
        str: Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that are often extraction artifacts
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\<\>\~\`]', '', text)
    
    # Fix common PDF extraction issues
    text = re.sub(r'(\w+)\s*-\s*(\w+)', r'\1-\2', text)  # Fix hyphenated words
    text = re.sub(r'(\w)\s+(\w)', r'\1 \2', text)  # Normalize word spacing
    
    # Remove excessive punctuation
    text = re.sub(r'\.{3,}', '...', text)
    text = re.sub(r'-{2,}', '--', text)
    
    # Clean up line breaks and spacing
    text = text.strip()
    
    return text

def extract_pdf_text_pdfplumber(file_bytes):
    """
    Extract text from PDF using pdfplumber for better formatting.
    
    Args:
        file_bytes: BytesIO object containing PDF data
        
    Returns:
        list: List of page contents with better formatting
    """
    try:
        import pdfplumber
        
        pages_content = []
        with pdfplumber.open(file_bytes) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text with better layout preservation
                text = page.extract_text()
                if text and text.strip():
                    cleaned_text = clean_extracted_text(text)
                    pages_content.append({
                        "page_num": page_num,
                        "content": cleaned_text
                    })
        return pages_content
    except ImportError:
        return None
    except Exception as e:
        logging.info(f"Error with pdfplumber extraction: {e}")
        return None

def extract_pdf_text_pymupdf(file_bytes):
    """
    Extract text from PDF using PyMuPDF (fitz) for high-quality extraction.
    
    Args:
        file_bytes: BytesIO object containing PDF data
        
    Returns:
        list: List of page contents with high-quality formatting
    """
    try:
        import fitz
        
        pages_content = []
        pdf_document = fitz.open(stream=file_bytes.read(), filetype="pdf")
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            # Extract text with layout information
            text = page.get_text()
            if text and text.strip():
                cleaned_text = clean_extracted_text(text)
                pages_content.append({
                    "page_num": page_num + 1,
                    "content": cleaned_text
                })
        
        pdf_document.close()
        return pages_content
    except ImportError:
        return None
    except Exception as e:
        logging.info(f"Error with PyMuPDF extraction: {e}")
        return None

def extract_pdf_text_pypdf2(file_bytes):
    """
    Fallback PDF extraction using PyPDF2 with improved text cleaning.
    
    Args:
        file_bytes: BytesIO object containing PDF data
        
    Returns:
        list: List of page contents
    """
    try:
        from PyPDF2 import PdfReader
        
        pages_content = []
        reader = PdfReader(file_bytes)
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                cleaned_text = clean_extracted_text(text)
                pages_content.append({
                    "page_num": page_num,
                    "content": cleaned_text
                })
        return pages_content
    except Exception as e:
        logging.info(f"Error with PyPDF2 extraction: {e}")
        return []

def extract_pdf_text_best_available(file_bytes):
    """
    Extract PDF text using the best available method.
    Tries pdfplumber, then PyMuPDF, then falls back to PyPDF2.
    
    Args:
        file_bytes: BytesIO object containing PDF data
        
    Returns:
        tuple: (pages_content, method_used)
    """
    # Reset file pointer
    file_bytes.seek(0)
    
    # Try pdfplumber first (best formatting)
    result = extract_pdf_text_pdfplumber(file_bytes)
    if result:
        logging.info("Used pdfplumber for PDF extraction")
        return result, "pdfplumber"
    
    # Try PyMuPDF second (fast and reliable)
    file_bytes.seek(0)
    result = extract_pdf_text_pymupdf(file_bytes)
    if result:
        logging.info("Used PyMuPDF for PDF extraction")
        return result, "PyMuPDF"
    
    # Fall back to PyPDF2
    file_bytes.seek(0)
    result = extract_pdf_text_pypdf2(file_bytes)
    logging.info("Used PyPDF2 for PDF extraction (fallback)")
    return result, "PyPDF2"

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PDF Text Extractor API",
        "version": "1.0.0",
        "endpoints": {
            "/extract": "POST - Extract text from PDF file",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "PDF Extractor API is running"}

@app.post("/extract", response_model=ExtractionResponse)
async def extract_pdf_text(file: UploadFile = File(...)):
    """
    Extract text from uploaded PDF file.
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        ExtractionResponse: Extracted text with metadata
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="File must be a PDF"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        file_bytes = BytesIO(file_content)
        
        # Extract text using best available method
        pages_content, method_used = extract_pdf_text_best_available(file_bytes)
        
        if not pages_content:
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from PDF. The file may be corrupted or contain only images."
            )
        
        return ExtractionResponse(
            success=True,
            message=f"Successfully extracted text from {len(pages_content)} pages",
            total_pages=len(pages_content),
            extraction_method=method_used,
            pages=pages_content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

@app.post("/extract/{method}", response_model=ExtractionResponse)
async def extract_pdf_text_specific_method(
    method: str, 
    file: UploadFile = File(...)
):
    """
    Extract text from PDF using a specific extraction method.
    
    Args:
        method: Extraction method ('pdfplumber', 'pymupdf', or 'pypdf2')
        file: Uploaded PDF file
        
    Returns:
        ExtractionResponse: Extracted text with metadata
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="File must be a PDF"
        )
    
    # Validate method
    valid_methods = ['pdfplumber', 'pymupdf', 'pypdf2']
    if method.lower() not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid method. Use one of: {', '.join(valid_methods)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        file_bytes = BytesIO(file_content)
        
        # Extract using specific method
        if method.lower() == 'pdfplumber':
            pages_content = extract_pdf_text_pdfplumber(file_bytes)
        elif method.lower() == 'pymupdf':
            pages_content = extract_pdf_text_pymupdf(file_bytes)
        elif method.lower() == 'pypdf2':
            pages_content = extract_pdf_text_pypdf2(file_bytes)
        
        if not pages_content:
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract text using {method}. The library may not be installed or the PDF may be incompatible."
            )
        
        return ExtractionResponse(
            success=True,
            message=f"Successfully extracted text from {len(pages_content)} pages using {method}",
            total_pages=len(pages_content),
            extraction_method=method,
            pages=pages_content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing PDF with {method}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF with {method}: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    ) 