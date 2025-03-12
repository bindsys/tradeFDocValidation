import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part, SafetySetting
import os
import logging
import yaml
from src.prompt import system_prompt, static_prompt
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Load configurations from YAML
config_path = os.path.join("config", "config.yaml")
if not os.path.exists(config_path):
    # logger.error(f"Configuration file not found at {config_path}")
    raise FileNotFoundError(f"Configuration file not found at {config_path}")

with open(config_path, "r") as config_file:
    config = yaml.safe_load(config_file)
    
PROJECT_NAME = config["PROJECT_NAME"]
LOCATION = config["LOCATION"]
MODEL = config["MODEL"]

# Define safety settings to filter out harmful or unwanted content in the model's output
safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH
    )
]

# Configuration for content generation, adjusting the output characteristics
generation_config = {
    "max_output_tokens": 8192,  # Maximum number of tokens (words or parts of words) in the generated output
    "temperature": 0,           # Controls the randomness of the output; lower values = more deterministic
    "top_p": 0.95,              # Limits the generated output to a subset of tokens that make up the top 95% probability
}

# Initialize Vertex AI with the project and region
vertexai.init(project=PROJECT_NAME, location=LOCATION)

# Load the Generative Model using the specified model and system prompt
model = GenerativeModel(MODEL, system_instruction=[system_prompt])

# Function to generate multimodal content (text from images + prompt)
def generate_multimodal_content(prompt: str, image_paths: list):
    """
    Generate multimodal content based on the provided text prompt and images.

    Args:
        prompt (str): The text input prompt to guide content generation.
        image_paths (list): List of file paths to images to be used in content generation.

    Returns:
        str: The generated text content.
    """
    try:
        images = []
        
        # Load each image from the provided file paths
        for image_path in image_paths:
            image = Image.load_from_file(image_path)
            images.append(image)

        # Generate content using the prompt, static prompt, and images
        response = model.generate_content(
            [f"{static_prompt} : {prompt}"] + images,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        return response.text  # Return the generated text content

    except Exception as e:
        # Log any errors encountered during the generation proces
        logging.error(f"Error generating content with AI: {str(e)}")
        raise
