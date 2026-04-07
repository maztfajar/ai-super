import io
import markdown
import traceback
from fpdf import FPDF

try:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # Text safely encoded
    html = markdown.markdown("Hello Table\n\| A | B |\n|---|---|\n| 1 | 2 |", extensions=['tables'])
    html_safe = html.encode('latin-1', 'replace').decode('latin-1')
    pdf.write_html(html_safe)
    
    buf = io.BytesIO()
    pdf.output(buf)
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()
