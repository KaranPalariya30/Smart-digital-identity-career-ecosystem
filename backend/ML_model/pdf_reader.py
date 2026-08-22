import os
import PyPDF2

# ---- Exraxt text from PDF -----

def extract_text_from_pdf(file_path : str) -> str:

    # CHECK 1 : --------- Check if file actually exist or not -----------
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found at path : {file_path}")

    # CHECK 2 : ---------- Check if uploaded file is a pdf or not -------
    if not file_path.lower().endswith(".pdf"):
        raise ValueError(f"File must be a pdf")

    # Store page text
    extracted_text = []

    # with ----> automatically closes the file 
    # rb = read binary mode for pdf files
    with open(file_path,"rb") as pdf_file:

        reader = PyPDF2.PdfReader(pdf_file)

        total_pages = len(reader.pages)

        # Text from each page
        for page_num in range(total_pages):

            page = reader.pages[page_num]

            page_text = page.extract_text()

            if page_text:
                extracted_text.append(page_text)


            #add new line after each text extraxted
            full_text = "\n".join(extracted_text)

        if not full_text.strip():
            raise ValueError(
                    "Couldn't extracted text from the PDF it is NULL"
                    "It's might be a scanned image. Uplaod a text-based PDF "
                )


        return full_text








