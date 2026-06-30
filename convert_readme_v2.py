import markdown
import pdfkit

# Read the markdown file
with open('readme.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Convert to HTML
html_content = markdown.markdown(text)

# Save to PDF using pdfkit
pdfkit.from_string(html_content, 'readme.pdf')
print('Successfully converted readme.md to readme.pdf!')