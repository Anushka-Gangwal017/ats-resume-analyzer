import re

def extract_sections(text):
    """
    Takes raw resume text and splits it into sections.
    Returns a dictionary like:
    {
        'summary': '...',
        'skills': '...',
        'experience': '...',
        'education': '...',
        'projects': '...',
        'certifications': '...',
        'other': '...'
    }
    """

    # These are all the possible section heading names
    # we look for in a resume (people write them differently)
    section_keywords = {
        'summary':        ['summary', 'objective', 'about me', 
                           'profile', 'about', 'overview'],
        'skills':         ['skills', 'technical skills', 'core skills',
                           'key skills', 'technologies', 'tools',
                           'tech stack', 'competencies'],
        'experience':     ['experience', 'work experience', 
                           'professional experience', 'employment',
                           'internship', 'work history', 'positions held'],
        'education':      ['education', 'academic background',
                           'qualifications', 'academics', 
                           'educational background'],
        'projects':       ['projects', 'personal projects', 
                           'academic projects', 'key projects',
                           'project work'],
        'certifications': ['certifications', 'certificates', 
                           'courses', 'training', 'achievements',
                           'awards', 'activities'],
        'research':       ['research', 'publications', 
                           'research experience', 'papers'],
    }

    # Start with empty sections
    sections = {key: '' for key in section_keywords}
    sections['other'] = ''

    # Split the resume text into individual lines
    lines = text.split('\n')

    current_section = 'other'  # we start in "other" until we find a heading

    for line in lines:
        line_stripped = line.strip()

        if not line_stripped:   # skip blank lines
            continue

        # Check if this line is a section heading
        line_lower = line_stripped.lower()
        found_section = False

        for section_name, keywords in section_keywords.items():
            for keyword in keywords:
                # Match if the line IS the keyword
                # or STARTS with it (e.g. "Skills & Tools")
                if line_lower == keyword or line_lower.startswith(keyword):
                    current_section = section_name
                    found_section = True
                    break
            if found_section:
                break

        # If it's not a heading, add text to the current section
        if not found_section:
            sections[current_section] += line_stripped + ' '

    return sections


def extract_contact_info(text):
    """
    Pulls out email, phone number, and LinkedIn URL
    from the resume text using regex patterns.
    """
    contact = {}

    # Find email address
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.findall(email_pattern, text)
    contact['email'] = email_match[0] if email_match else 'Not found'

    # Find phone number (handles formats like 9284248244, +91-9284248244, etc.)
    phone_pattern = r'(\+?\d[\d\s\-]{8,14}\d)'
    phone_match = re.findall(phone_pattern, text)
    contact['phone'] = phone_match[0].strip() if phone_match else 'Not found'

    # Find LinkedIn URL
    linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9\-]+'
    linkedin_match = re.findall(linkedin_pattern, text)
    contact['linkedin'] = linkedin_match[0] if linkedin_match else 'Not found'

    # Find GitHub URL
    github_pattern = r'github\.com/[a-zA-Z0-9\-]+'
    github_match = re.findall(github_pattern, text)
    contact['github'] = github_match[0] if github_match else 'Not found'

    return contact


# ==========================================
# TEST IT — run this file directly to test
# ==========================================
if __name__ == "__main__":

    # First we need the pdf_parser we built yesterday
    # Make sure pdf_parser.py is in the same src/ folder
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))  # helps Python find our files

    from pdf_parser import extract_text

    # Change this to your resume path
    resume_path = "data/resumes/resume2.pdf"

    print("Reading resume PDF...")
    raw_text = extract_text(resume_path)

    print("\n" + "="*50)
    print("CONTACT INFORMATION FOUND:")
    print("="*50)
    contact_info = extract_contact_info(raw_text)
    for key, value in contact_info.items():
        print(f"  {key.upper()}: {value}")

    print("\n" + "="*50)
    print("SECTIONS FOUND IN RESUME:")
    print("="*50)
    sections = extract_sections(raw_text)
    for section_name, section_content in sections.items():
        if section_content.strip():  # only print sections that have content
            print(f"\n📌 {section_name.upper()}:")
            print(f"   {section_content[:200]}...")  # show first 200 chars
            print(f"   (total length: {len(section_content)} characters)")