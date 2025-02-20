from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
import yaml
import aiofiles
import hashlib
import os
import aiohttp
from typing import List
import json
from cachetools import TTLCache
import tempfile

# Initialize FastAPI app
app = FastAPI(
    title="PDF Processing API",
    description="API for processing PDF documents",
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

# Initialize cache with 5-day TTL (in seconds)
cache = TTLCache(maxsize=100, ttl=432000)

# Load Swagger YAML file
with open('swagger.yaml', 'r') as file:
    swagger_doc = yaml.safe_load(file)
app.openapi_schema = swagger_doc

async def get_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(8192):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

async def load_prompt(prompt_file: str) -> str:
    """Load prompt from file."""
    try:
        async with aiofiles.open(prompt_file, 'r') as f:
            return await f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Prompt file '{prompt_file}' not found"
        )

@app.post("/process-pdfs")
async def process_pdfs(files: List[UploadFile] = File(...)):
    """
    Process uploaded PDF files and return analysis results.
    """
    try:
        # Validate number of files
        if len(files) < 1:
            raise HTTPException(status_code=400, detail="Please upload at least one PDF file.")
        if len(files) > 2:
            raise HTTPException(status_code=400, detail="You can upload up to 2 PDF files only.")

        # Load prompt from file
        prompt = await load_prompt('prompts/trade_finance_prompt.txt')

        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded files
            file_paths = []
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)
                async with aiofiles.open(file_path, 'wb') as f:
                    content = await file.read()
                    await f.write(content)
                file_paths.append(file_path)

            # Generate cache key
            cache_key = '-'.join([await get_file_hash(path) for path in file_paths])

            # Check cache
            if cache_key in cache:
                print('Returning cached response')
                return JSONResponse(content=cache[cache_key])

            # Prepare files for API request
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field('prompt', prompt)
                
                for file_path in file_paths:
                    form_data.add_field(
                        'files',
                        open(file_path, 'rb'),
                        filename=os.path.basename(file_path)
                    )

                # Make API request
                async with session.post(
                    'https://contentgen.dev.edocsafeai.corporateidplatform.com/generate-content/',
                    data=form_data,
                    headers={'accept': 'application/json'}
                ) as response:
                    response_data = await response.json()

            # Process response
            response_text = response_data.get('response_text', response_data)
            
            try:
                # Clean and parse JSON response
                cleaned_json = response_text.replace('```json', '').replace('```', '').strip()
                json_response = json.loads(cleaned_json)
                
                # Cache the response
                cache[cache_key] = json_response
                
                return JSONResponse(content=json_response)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    content={
                        "error": "Invalid JSON format from API",
                        "rawResponse": response_text
                    }
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api-docs")
async def get_docs():
    """Serve Swagger UI documentation."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Documentation")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
