import markdown
from weasyprint import HTML

# Read the markdown file
with open('readme.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Convert to HTML
html_content = markdown.markdown(text)

# Add basic styling to make it look decent in PDF
full_html = f"<html><head><style>body {{ font-family: sans-serif; padding: 20px; }}</style></head><body>{html_content}</body></html>"

# Convert to PDF
HTML(string=full_html).write_pdf('readme.pdf')
print('Successfully converted readme.md to readme.pdf!')