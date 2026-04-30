import fitz # PyMuPDF
import pandas as pd
import io
import docx

def parse_pdf(file_bytes: bytes) -> dict:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_data = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pages_data.append({
            "node_type": "page",
            "node_id": f"page_{page_num + 1}",
            "content": page.get_text("text").strip()
        })
    return {"document_type": "pdf", "structure": pages_data}

def parse_docx(file_bytes: bytes) -> dict:
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs_data = []
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            # In a production app, you can read para.style.name to identify headings
            paragraphs_data.append({
                "node_type": "paragraph",
                "node_id": f"para_{i + 1}",
                "content": para.text.strip()
            })
    return {"document_type": "docx", "structure": paragraphs_data}

def parse_excel(file_bytes: bytes) -> dict:
    excel_data = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
    sheets_data = []
    for sheet_name, df in excel_data.items():
        sheets_data.append({
            "node_type": "sheet",
            "node_id": f"sheet_{sheet_name}",
            "content": df.to_json(orient="records")
        })
    return {"document_type": "excel", "structure": sheets_data}
