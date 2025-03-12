from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import json
import logging
import re
from src.utils import process_uploaded_files, cleanup_temp_files
from src.generate import generate_multimodal_content
from src.prompt import analysis_prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trade Finance API",
    description=(
        "API to accept at least one PDF file (mandatory) and optionally a second file, "
        "then process them with detailed verification checks. Performs a series of verification "
        "checks and returns a JSON report detailing the results and a risk rating (Red/Amber/Green)."
    ),
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/validate-trade-finance")
async def validate_trade_finance(files: List[UploadFile] = File(...)):
    """
    Validate trade finance documents and return a JSON report.
    
    Args:
        files (list[UploadFile]): List of uploaded files.
    
    Returns:
        JSONResponse: JSON response containing the validation report.
    """
    image_paths = []
    max_retries = 2

    try:
        # Process uploaded files
        image_paths = await process_uploaded_files(files, logger)
        if not image_paths:
            raise HTTPException(status_code=400, detail="No valid files to process.")
        
        # Try generating content with retries
        for attempt in range(max_retries):
            try:
                response_text = generate_multimodal_content(analysis_prompt, image_paths)
                logger.info("Successfully generated content with the model.")
                
                # Clean and parse JSON response
                cleaned_response = re.sub(r'^.*?{', '{', response_text, flags=re.S)
                cleaned_response = re.sub(r'}[^}]*$', '}', cleaned_response, flags=re.S)
                cleaned_text = json.loads(re.sub(r'\\n|/n', ' ', cleaned_response).strip("' "))
                
                return JSONResponse(content=cleaned_text)
            except json.JSONDecodeError:
                logger.error(f"JSON decoding error on attempt {attempt + 1}", exc_info=True)
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail="Invalid JSON format in API response.")
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error during PDF processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error.")
    finally:
        # Clean up temporary files
        cleanup_temp_files(image_paths, logger)
