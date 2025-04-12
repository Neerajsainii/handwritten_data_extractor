from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pytesseract
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import os
import uuid
from pdf2image import convert_from_path
import io
import fitz  # PyMuPDF for PDF processing
import re

# Configure Tesseract path
TESSERACT_CMD = getattr(settings, 'TESSERACT_CMD', r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def index(request):
    """
    Render the main OCR page
    """
    return render(request, 'ocr_app/index.html')

def process_image(request):
    """
    Process uploaded image or PDF file and extract text using OCR
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is supported'})
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file part'})
    
    file = request.FILES['file']
    if file.name == '':
        return JsonResponse({'error': 'No selected file'})
    
    # Get file extension
    file_extension = os.path.splitext(file.name)[1].lower()
    
    # Create a unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save the file temporarily
    filepath = os.path.join(temp_dir, unique_filename)
    with open(filepath, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    # Process based on file type
    try:
        if file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            # Process image file
            text = process_image_file(filepath)
        elif file_extension == '.pdf':
            # Process PDF file
            text = process_pdf_file_pymupdf(filepath)
        else:
            return JsonResponse({'error': 'Unsupported file format'})
    except Exception as e:
        return JsonResponse({'error': f'Error processing file: {str(e)}'})
    finally:
        # Clean up the temporary file
        try:
            os.remove(filepath)
        except:
            pass
    
    return JsonResponse({'text': text})

def process_image_file(image_path):
    """
    Process an image file using Tesseract OCR optimized for handwritten text
    with improved formatting preservation
    """
    try:
        # Read image with OpenCV
        image = cv2.imread(image_path)
        if image is None:
            raise Exception("Could not read image with OpenCV")
        
        # Get image dimensions for layout analysis
        height, width = image.shape[:2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply preprocessing for handwritten text
        # Noise removal with bilateral filter
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive thresholding for better results with varying lighting
        adaptive_thresh = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Dilation to connect broken strokes
        kernel = np.ones((2,2), np.uint8)
        dilated = cv2.dilate(adaptive_thresh, kernel, iterations=1)
        
        # Apply additional image enhancements
        # Contrast adjustment
        enhanced = cv2.convertScaleAbs(dilated, alpha=1.5, beta=0)
        
        # For table detection, try to detect lines first
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        
        # Detect horizontal lines
        horizontal_lines = cv2.erode(dilated, horizontal_kernel, iterations=2)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=2)
        
        # Detect vertical lines
        vertical_lines = cv2.erode(dilated, vertical_kernel, iterations=2)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=2)
        
        # Combine horizontal and vertical lines
        table_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
        
        # Check if we detected a table structure
        is_table = cv2.countNonZero(table_mask) > (width * height * 0.01)  # At least 1% of image has lines
        
        # Primary approach: Try to use Tesseract's built-in table detection
        # PSM 6: Assume a single uniform block of text
        # PSM 4: Assume a single column of text of variable sizes
        # PSM 3: Fully automatic page segmentation, but no OSD
        
        if is_table:
            # For tables, use PSM 6 with preserve_interword_spaces
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            
            # Get structured output with bounding boxes
            data = pytesseract.image_to_data(enhanced, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Get words with their positions
            words = []
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    words.append({
                        'text': data['text'][i],
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'line_num': data['line_num'][i],
                        'block_num': data['block_num'][i]
                    })
            
            # Sort words by line number and then by left position
            words.sort(key=lambda w: (w['line_num'], w['left']))
            
            # Group words by line
            lines = {}
            for word in words:
                line_num = word['line_num']
                if line_num not in lines:
                    lines[line_num] = []
                lines[line_num].append(word)
            
            # Detect table columns based on word positions
            all_x_positions = []
            for line_words in lines.values():
                for word in line_words:
                    all_x_positions.append(word['left'])
            
            # Cluster x positions to find column boundaries
            if all_x_positions:
                # Sort x positions
                all_x_positions.sort()
                
                # Find clusters with gap detection
                column_borders = []
                last_x = all_x_positions[0]
                for x in all_x_positions:
                    if x - last_x > 20:  # If gap > 20px, it's a new column
                        column_borders.append((last_x + x) // 2)
                    last_x = x
                
                # Add endpoints
                column_borders = [0] + column_borders + [width]
                
                # Build table rows
                table_rows = []
                for line_num, line_words in sorted(lines.items()):
                    row = [""] * (len(column_borders) - 1)
                    for word in line_words:
                        # Find which column this word belongs to
                        for i in range(len(column_borders) - 1):
                            if column_borders[i] <= word['left'] < column_borders[i+1]:
                                row[i] += word['text'] + " "
                                break
                    
                    # Trim whitespace
                    row = [cell.strip() for cell in row]
                    table_rows.append(row)
                
                # Convert to formatted text
                structured_text = ""
                for row in table_rows:
                    formatted_row = "\t".join(cell for cell in row)
                    structured_text += formatted_row + "\n"
            else:
                # Fallback to standard OCR if column detection fails
                text = pytesseract.image_to_string(enhanced, config=custom_config)
                structured_text = improve_column_formatting(text)
        else:
            # Try multiple segmentation modes for best results
            results = []
            
            # Try PSM 4 (single column variable sizes)
            config4 = r'--oem 3 --psm 4 -c preserve_interword_spaces=1'
            text4 = pytesseract.image_to_string(enhanced, config=config4)
            results.append(text4)
            
            # Try PSM 6 (uniform block of text)
            config6 = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text6 = pytesseract.image_to_string(enhanced, config=config6)
            results.append(text6)
            
            # Try PSM 3 (fully automatic)
            config3 = r'--oem 3 --psm 3 -c preserve_interword_spaces=1'
            text3 = pytesseract.image_to_string(enhanced, config=config3)
            results.append(text3)
            
            # Choose the result with most characters
            text = max(results, key=lambda t: len(t.strip()))
            
            # Improve formatting
            structured_text = improve_column_formatting(text)
        
        return structured_text
        
    except Exception as e:
        # Fallback method using PIL if OpenCV processing fails
        try:
            image = Image.open(image_path)
            # Convert to grayscale
            image = image.convert('L')
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Use Tesseract with configuration for handwritten text and format preservation
            custom_config = r'--oem 3 --psm 4 -c preserve_interword_spaces=1'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Improve formatting
            text = improve_column_formatting(text)
            
            return text
        except Exception as nested_e:
            return f"Error processing image: {str(e)}, Fallback error: {str(nested_e)}"

def improve_column_formatting(text):
    """
    Analyze text to detect and improve column formatting
    """
    lines = text.split('\n')
    
    # Skip empty lines
    lines = [line for line in lines if line.strip()]
    
    if not lines:
        return text
    
    # Check for potential tabular data by looking for consistent separator patterns
    potential_delimiters = ['\t', '  ', '   ', '    ']
    delimiter_counts = {}
    
    for delim in potential_delimiters:
        count = sum(1 for line in lines if delim in line)
        if count > len(lines) * 0.3:  # If at least 30% of lines have this delimiter
            delimiter_counts[delim] = count
    
    if delimiter_counts:
        # Use the most common delimiter
        best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        
        # Reformat with consistent spacing
        formatted_lines = []
        max_cells = 0
        
        # Split lines by delimiter
        split_lines = []
        for line in lines:
            cells = [cell.strip() for cell in line.split(best_delimiter)]
            split_lines.append(cells)
            max_cells = max(max_cells, len(cells))
        
        # Add empty cells to make all rows have the same number of columns
        for cells in split_lines:
            while len(cells) < max_cells:
                cells.append("")
        
        # Calculate column widths
        col_widths = [0] * max_cells
        for cells in split_lines:
            for i, cell in enumerate(cells):
                col_widths[i] = max(col_widths[i], len(cell))
        
        # Format lines with consistent column widths
        for cells in split_lines:
            formatted_cells = []
            for i, cell in enumerate(cells):
                formatted_cells.append(cell.ljust(col_widths[i]))
            formatted_lines.append("  ".join(formatted_cells))
            
        return '\n'.join(formatted_lines)
    
    # Check for potential column structure based on character positions
    # Find common space positions
    space_positions = {}
    for line in lines:
        for i, char in enumerate(line):
            if char == ' ':
                if i in space_positions:
                    space_positions[i] += 1
                else:
                    space_positions[i] = 1
    
    # Find positions that have spaces in more than 60% of lines
    common_spaces = []
    threshold = max(3, len(lines) * 0.6)  # At least 60% of lines or 3 lines minimum
    for pos, count in sorted(space_positions.items()):
        if count >= threshold:
            common_spaces.append(pos)
    
    # Group adjacent spaces
    if common_spaces:
        column_breaks = []
        current_group = [common_spaces[0]]
        
        for i in range(1, len(common_spaces)):
            if common_spaces[i] - common_spaces[i-1] <= 2:  # Adjacent spaces
                current_group.append(common_spaces[i])
            else:
                # Take middle of current group
                column_breaks.append(sum(current_group) // len(current_group))
                current_group = [common_spaces[i]]
        
        # Add the last group
        if current_group:
            column_breaks.append(sum(current_group) // len(current_group))
        
        # Reformat based on detected column positions
        if len(column_breaks) >= 1:  # Need at least one column break
            formatted_lines = []
            
            for line in lines:
                if not line.strip():
                    formatted_lines.append("")
                    continue
                
                # Insert tab characters at column breaks
                parts = []
                last_pos = 0
                for pos in column_breaks:
                    if pos > len(line):
                        break
                    
                    # Extract from last_pos to pos
                    if pos > last_pos:
                        parts.append(line[last_pos:pos].strip())
                    else:
                        parts.append("")
                    last_pos = pos
                
                # Add the remainder
                if last_pos < len(line):
                    parts.append(line[last_pos:].strip())
                
                # Join with tabs
                formatted_lines.append("\t".join(parts))
            
            return '\n'.join(formatted_lines)
    
    # Detect clear tabular structure based on consistent word count
    word_counts = [len(line.split()) for line in lines]
    if len(lines) >= 3 and len(set(word_counts[:min(5, len(lines))])) <= 2:
        # Likely a table with consistent word counts per row
        max_words = max(word_counts)
        if max_words >= 2:  # At least 2 columns
            formatted_lines = []
            
            # Calculate number of words per column
            words_per_column = 1  # Default to 1 word per column
            
            # Format each line
            for line in lines:
                words = line.split()
                # Ensure consistent number of columns
                while len(words) < max_words:
                    words.append("")
                
                # Group words into columns
                columns = []
                for i in range(0, len(words), words_per_column):
                    if i + words_per_column <= len(words):
                        columns.append(" ".join(words[i:i+words_per_column]))
                    else:
                        columns.append(" ".join(words[i:]))
                
                formatted_lines.append("\t".join(columns))
            
            return '\n'.join(formatted_lines)
    
    # If no clear column structure, return the original text
    return text

def process_pdf_file(pdf_path):
    """
    Process a PDF file using pdf2image and Tesseract OCR
    """
    try:
        # Try to use pdf2image with poppler
        images = convert_from_path(pdf_path)
        
        # Process each page
        text_result = ""
        for i, image in enumerate(images):
            # Convert PIL image to OpenCV format for preprocessing
            open_cv_image = np.array(image) 
            open_cv_image = open_cv_image[:, :, ::-1].copy() # Convert RGB to BGR
            
            # Process with the improved image processing method
            image_path = f"temp_page_{i}.png"
            image.save(image_path)
            page_text = process_image_file(image_path)
            try:
                os.remove(image_path)
            except:
                pass
            
            text_result += f"\n--- Page {i+1} ---\n{page_text}"
            
        return text_result
    except Exception as e:
        return f"Error processing PDF with pdf2image: {str(e)}"

def process_pdf_file_pymupdf(pdf_path):
    """
    Process a PDF file using PyMuPDF and Tesseract OCR with improved formatting
    """
    try:
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        
        text_result = ""
        for page_num in range(len(pdf_document)):
            # Get the page
            page = pdf_document.load_page(page_num)
            
            # Try to extract text directly from PDF if it's not scanned
            direct_text = page.get_text()
            if len(direct_text.strip()) > 100:  # If substantial text is found
                text_result += f"\n--- Page {page_num+1} ---\n{direct_text}"
                continue
            
            # For scanned PDFs, convert to image and use OCR
            # Higher resolution for better OCR results
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            
            # Save temporary image file for processing
            temp_img_path = f"temp_pdf_page_{page_num}.png"
            pix.save(temp_img_path)
            
            # Process with the improved image processing method
            page_text = process_image_file(temp_img_path)
            
            # Clean up
            try:
                os.remove(temp_img_path)
            except:
                pass
            
            text_result += f"\n--- Page {page_num+1} ---\n{page_text}"
        
        # Close the document
        pdf_document.close()
        
        return text_result
    except Exception as e:
        # Try to use original pdf2image method if PyMuPDF fails
        try:
            return process_pdf_file(pdf_path)
        except Exception as nested_e:
            return f"Error processing PDF: {str(e)}, Fallback error: {str(nested_e)}"
