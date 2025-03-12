from pdf2image import convert_from_path
import aiofiles
import os 
import tempfile
import platform


# Environment variable for Poppler path, needed for PDF to image conversion (on Windows)
POPLER_PATH = os.getenv("POPLER_PATH", r"poppler-24.07.0\Library\bin")
 


async def process_uploaded_files(files, logger):
    """
    Process a list of uploaded files and convert them to image file paths.
    
    Args:
        files (list[UploadFile]): List of uploaded files.
        logger (logging.Logger): Logger instance for logging operations.
    
    Returns:
        list: List of image file paths generated from the uploaded files.
    """
    image_paths = []
    try:
        for file in files:
            logger.info(f"Received file: {file.filename} of type {file.content_type}")
            
            if file.content_type == "application/pdf":
                pdf_paths = await process_pdf(file, logger)
                image_paths.extend(pdf_paths)
            elif file.content_type in ["image/jpeg", "image/png"]:
                image_path = await process_image(file, logger)
                image_paths.append(image_path)
            else:
                logger.error(f"Unsupported file type: {file.filename}")
        return image_paths
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise


async def process_pdf(file, logger):
    """
    Process a PDF file and convert each page to an image.
    
    Args:
        file (UploadFile): The uploaded PDF file.
        logger (logging.Logger): Logger instance for logging operations.
    
    Returns:
        list: List of file paths to images generated from the PDF pages.
    """
    pdf_path = None
    pdf_paths = []
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf_file:
            await temp_pdf_file.write(await file.read())
            pdf_path = temp_pdf_file.name
        
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPLER_PATH) if platform.system() == "Windows" else convert_from_path(pdf_path, dpi=300)
        
        if not images:
            logger.error(f"No images extracted from PDF: {file.filename}")
            return []
        
        for page_num, image in enumerate(images):
            image_path = os.path.join(tempfile.gettempdir(), f"{file.filename}_page_{page_num + 1}.png")
            image.save(image_path, 'PNG')
            pdf_paths.append(image_path)
            logger.info(f"Processed page {page_num + 1} of PDF: {file.filename}")
        
        return pdf_paths
    except Exception as e:
        logger.error(f"Error processing PDF {file.filename}: {str(e)}")
        raise
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                logger.info(f"Deleted temporary PDF file: {pdf_path}")
            except Exception as e:
                logger.error(f"Error deleting temporary PDF file {pdf_path}: {str(e)}")


async def process_image(file, logger):
    """
    Process an image file and save it temporarily.
    
    Args:
        file (UploadFile): The uploaded image file.
        logger (logging.Logger): Logger instance for logging operations.
    
    Returns:
        str: Path to the temporarily saved image.
    """
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image_file:
            await temp_image_file.write(await file.read())
            image_path = temp_image_file.name
        
        logger.info(f"Successfully processed image: {file.filename}")
        return image_path
    except Exception as e:
        logger.error(f"Error processing image {file.filename}: {str(e)}")
        raise


def cleanup_temp_files(image_paths, logger):
    """
    Delete temporary image files from the filesystem.
    
    Args:
        image_paths (list): List of file paths to be deleted.
        logger (logging.Logger): Logger instance for logging operations.
    """
    for path in image_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted temporary file: {path}")
        except Exception as e:
            logger.error(f"Error deleting temporary file {path}: {str(e)}")
