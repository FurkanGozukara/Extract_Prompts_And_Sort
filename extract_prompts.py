import os
from PIL import Image
import re
import json

# Try to import piexif, but make it optional
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


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
    Also checks EXIF UserComment for embedded metadata (used in WebP files).
    Robust to handle various metadata formats and missing libraries.
    """
    try:
        with Image.open(image_path) as img:
            # Get all metadata
            info = img.info or {}
            
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
            
            # Check EXIF UserComment for embedded metadata (used in WebP files)
            if 'exif' in info and PIEXIF_AVAILABLE:
                try:
                    exif_dict = piexif.load(info['exif'])
                    exif_section = exif_dict.get('Exif', {})
                    
                    if piexif.ExifIFD.UserComment in exif_section:
                        user_comment = exif_section[piexif.ExifIFD.UserComment]
                        
                        # UserComment can be bytes or tuple, handle both
                        metadata_str = None
                        if isinstance(user_comment, bytes):
                            try:
                                metadata_str = user_comment.decode('utf-8')
                            except UnicodeDecodeError:
                                # Try to find utf-8 string in bytes
                                try:
                                    # Sometimes it's prefixed with charset info
                                    if user_comment.startswith(b'UNICODE\x00\x00\x00'):
                                        metadata_str = user_comment[8:].decode('utf-8')
                                    else:
                                        # Try to decode skipping non-utf8 bytes
                                        metadata_str = user_comment.decode('utf-8', errors='ignore')
                                except:
                                    pass
                        elif isinstance(user_comment, tuple) and len(user_comment) > 0:
                            if isinstance(user_comment[0], bytes):
                                try:
                                    metadata_str = user_comment[0].decode('utf-8')
                                except UnicodeDecodeError:
                                    try:
                                        if user_comment[0].startswith(b'UNICODE\x00\x00\x00'):
                                            metadata_str = user_comment[0][8:].decode('utf-8')
                                        else:
                                            metadata_str = user_comment[0].decode('utf-8', errors='ignore')
                                    except:
                                        pass
                            else:
                                metadata_str = str(user_comment[0])
                        else:
                            metadata_str = str(user_comment)
                        
                        # Parse the JSON metadata
                        if metadata_str:
                            try:
                                metadata_json = json.loads(metadata_str)
                                
                                # Check if it's a dict with 'parameters' field
                                if isinstance(metadata_json, dict):
                                    if 'parameters' in metadata_json:
                                        # Parse the parameters JSON string
                                        try:
                                            params_json = json.loads(metadata_json['parameters'])
                                            if 'sui_image_params' in params_json:
                                                sui_params = params_json['sui_image_params']
                                                if isinstance(sui_params, dict) and 'prompt' in sui_params:
                                                    prompt = sui_params['prompt']
                                                    if prompt and isinstance(prompt, str) and prompt.strip():
                                                        return prompt.strip()
                                        except (json.JSONDecodeError, TypeError, AttributeError):
                                            pass
                                    
                                    # Also check if sui_image_params is directly in metadata_json
                                    if 'sui_image_params' in metadata_json:
                                        sui_params = metadata_json['sui_image_params']
                                        if isinstance(sui_params, dict) and 'prompt' in sui_params:
                                            prompt = sui_params['prompt']
                                            if prompt and isinstance(prompt, str) and prompt.strip():
                                                return prompt.strip()
                            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                                # Try to extract prompt from malformed JSON
                                if 'sui_image_params' in metadata_str and 'prompt' in metadata_str:
                                    try:
                                        # Try to find prompt value using regex as fallback
                                        import re as regex_module
                                        prompt_match = regex_module.search(r'"prompt"\s*:\s*"([^"]+)"', metadata_str)
                                        if prompt_match:
                                            return prompt_match.group(1).strip()
                                    except:
                                        pass
                except Exception as e:
                    # Silently continue if EXIF reading fails
                    pass
            
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
    
    # Get all image files (including WebP)
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.PNG', '.JPG', '.JPEG', '.WEBP'}
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
            print(f"  [OK] {image_file}: Prompt found")
        else:
            print(f"  [SKIP] {image_file}: No prompt metadata found (skipped)")
    
    return prompts


def main():
    """
    Main function to process all folders and create txt files.
    Also processes images in the root directory.
    """
    # Get current directory
    base_dir = os.getcwd()
    
    # Check if root directory has images
    root_has_images = False
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isfile(item_path) and any(item.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
            root_has_images = True
            break
    
    # Process root directory if it has images
    if root_has_images:
        print(f"\n{'='*60}")
        print(f"Processing root directory: {base_dir}")
        print(f"{'='*60}")
        
        prompts = process_folder(base_dir)
        
        # Write prompts to prompts.txt file
        if prompts:
            output_file = os.path.join(base_dir, "prompts.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, prompt in enumerate(prompts, start=1):
                    f.write(f"{i}.\n\n{prompt}\n\n\n")
            
            print(f"\n[SUCCESS] Created {output_file} with {len(prompts)} prompts")
        else:
            print(f"\n[SKIP] No prompts found in root directory, skipping txt file creation")
    
    # Find all folders that contain images
    folders_to_process = []
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Check if folder contains image files
            has_images = False
            for file in os.listdir(item_path):
                if any(file.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    has_images = True
                    break
            
            if has_images:
                folders_to_process.append(item)
    
    if folders_to_process:
        print(f"\nFound {len(folders_to_process)} folders to process: {folders_to_process}\n")
    
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
                for i, prompt in enumerate(prompts, start=1):
                    f.write(f"{i}.\n\n{prompt}\n\n\n")
            
            print(f"\n[SUCCESS] Created {output_file} with {len(prompts)} prompts")
        else:
            print(f"\n[SKIP] No prompts found in {folder_name}, skipping txt file creation")
    
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

