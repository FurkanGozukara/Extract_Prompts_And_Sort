import os
from PIL import Image
import re
import json


def natural_sort_key(text):
    """
    Generate a key for natural sorting that handles numbers correctly.
    Windows-style sorting: '00.png', '01.png', '02.png', ..., '10.png', '11.png'
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    
    return [convert(c) for c in re.split(r'(\d+)', text)]


def extract_prompt_from_image(image_path):
    """
    Extract prompt from image metadata.
    Looks for JSON metadata with sui_image_params.prompt structure.
    """
    try:
        with Image.open(image_path) as img:
            # Get all metadata
            info = img.info
            
            # Check all metadata fields for JSON data
            for key, value in info.items():
                if isinstance(value, str):
                    # Try to parse as JSON
                    try:
                        metadata_json = json.loads(value)
                        
                        # Check if it has the sui_image_params structure
                        if isinstance(metadata_json, dict):
                            if 'sui_image_params' in metadata_json:
                                sui_params = metadata_json['sui_image_params']
                                if isinstance(sui_params, dict) and 'prompt' in sui_params:
                                    prompt = sui_params['prompt']
                                    if prompt and isinstance(prompt, str) and prompt.strip():
                                        return prompt.strip()
                    
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, continue checking other fields
                        continue
            
            return None
            
    except Exception as e:
        print(f"Error reading {image_path}: {e}")
        return None


def process_folder(folder_path):
    """
    Process all images in a folder and extract prompts.
    Returns a list of prompts in Windows-sorted order.
    """
    prompts = []
    
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist")
        return prompts
    
    # Get all image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'}
    image_files = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and 
        any(f.endswith(ext) for ext in image_extensions)
    ]
    
    # Sort using Windows-style natural sort
    image_files.sort(key=natural_sort_key)
    
    print(f"Processing {len(image_files)} images in {folder_path}...")
    
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        prompt = extract_prompt_from_image(image_path)
        
        if prompt:
            prompts.append(prompt)
            print(f"  ✓ {image_file}: Prompt found")
        else:
            print(f"  ✗ {image_file}: No prompt metadata found (skipped)")
    
    return prompts


def main():
    """
    Main function to process all folders and create txt files.
    """
    # Get current directory
    base_dir = os.getcwd()
    
    # Find all folders that contain images
    folders_to_process = []
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Check if folder contains image files
            has_images = False
            for file in os.listdir(item_path):
                if any(file.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
                    has_images = True
                    break
            
            if has_images:
                folders_to_process.append(item)
    
    print(f"Found {len(folders_to_process)} folders to process: {folders_to_process}\n")
    
    # Process each folder
    for folder_name in folders_to_process:
        folder_path = os.path.join(base_dir, folder_name)
        output_file = os.path.join(base_dir, f"{folder_name}.txt")
        
        print(f"\n{'='*60}")
        print(f"Processing folder: {folder_name}")
        print(f"{'='*60}")
        
        prompts = process_folder(folder_path)
        
        # Write prompts to txt file
        if prompts:
            with open(output_file, 'w', encoding='utf-8') as f:
                for prompt in prompts:
                    f.write(prompt + '\n')
            
            print(f"\n✓ Created {output_file} with {len(prompts)} prompts")
        else:
            print(f"\n✗ No prompts found in {folder_name}, skipping txt file creation")
    
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

