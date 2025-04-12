# HandWrite OCR - Extract Text from Handwritten Documents

HandWrite OCR is a web application that extracts text from images and PDF files, with specialized processing for handwritten text. It preserves formatting such as tables, columns, and rows.

![HandWrite OCR Screenshot](screenshot.png)

## Features

- Extract text from handwritten documents and images
- Support for a variety of file formats: JPG, JPEG, PNG, BMP, TIFF, PDF
- Intelligent table and column detection
- Preserves original formatting of handwritten text
- Modern and responsive user interface
- One-click text copying functionality

## Technology Stack

- **Backend:** Django (Python)
- **OCR Engine:** Tesseract OCR
- **Image Processing:** OpenCV, PIL
- **PDF Processing:** PyMuPDF, pdf2image
- **Frontend:** HTML5, CSS3, JavaScript

## Installation

### Prerequisites

1. Python 3.6+ with pip
2. Tesseract OCR installed on your system

### Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/handwrite-ocr.git
cd handwrite-ocr
```

### Step 2: Create and activate a virtual environment

```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install required packages

```bash
pip install -r requirements.txt
```

### Step 4: Install Tesseract OCR

- **Windows:** Download and install from [UB-Mannheim's GitHub](https://github.com/UB-Mannheim/tesseract/releases)
- **Linux:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`

### Step 5: Configure the application

Update the `TESSERACT_CMD` in `ocr_project/settings.py` to point to your Tesseract OCR installation path.

### Step 6: Run the application

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your web browser to use the application.

## Deployment to Render

### Step 1: Set up a Render account

Sign up for a free account at [render.com](https://render.com).

### Step 2: Create a new Web Service

1. Click "New" and select "Web Service"
2. Connect your GitHub repository
3. Give your service a name
4. Select "Python 3" as the environment
5. Set the build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
6. Set the start command: `gunicorn ocr_project.wsgi:application`
7. Add the following environment variables:
   - `PYTHON_VERSION`: 3.10.0
   - `DEBUG`: False
   - `ALLOWED_HOSTS`: .render.com,localhost
   - `SECRET_KEY`: your_secret_key

### Step 3: Install additional dependencies on Render

For PDF processing, Render may need additional packages. You can add apt packages in the Render dashboard under "Environment" → "Advanced" → "Clear Build Cache & Deploy with Apt Packages": `tesseract-ocr libgl1-mesa-glx libsm6 libxext6 poppler-utils`

## Usage

1. Upload an image or PDF file containing handwritten text
2. Click "Extract Text" to process the file
3. View the extracted text, preserving the original formatting
4. Copy the text to your clipboard with a single click

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [OpenCV](https://opencv.org/)
- [Django](https://www.djangoproject.com/)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)
- [pdf2image](https://github.com/Belval/pdf2image) 