import pdfplumber

def extract_text(pdf_path):
    """
    This function takes a PDF file path,
    opens it, reads every page,
    and returns all the text as one big string.
    """
    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # only add if page has text
                full_text += page_text + "\n"

    return full_text

# Change this path to your actual resume file
resume_path = "data/resumes/resume1.pdf"

extracted = extract_text(resume_path)

print("===== EXTRACTED TEXT FROM RESUME =====")
print(extracted)
print("===== TOTAL CHARACTERS:", len(extracted), "=====")