import os
from PIL import Image
from PIL.ExifTags import TAGS
import re
import piexif
import json

def windows_sort_key(filename):
    """
    Windows-style sorting: splits filename into numeric and non-numeric parts
    for proper numeric sorting (e.g., 2_0 comes before 10_0)
    """
    parts = re.split(r'(\d+)', filename)
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def get_image_pairs(directory):
    """Get all image pairs sorted in Windows style"""
    files = [f for f in os.listdir(directory) if f.endswith(('.png', '.jpg', '.jpeg'))]
    files.sort(key=windows_sort_key)
    
    pairs = {}
    for filename in files:
        # Extract the number prefix (e.g., "0" from "0_0.png" or "0_1.png")
        match = re.match(r'(\d+)_(\d+)\.', filename)
        if match:
            prefix = match.group(1)
            suffix = match.group(2)
            
            if prefix not in pairs:
                pairs[prefix] = {}
            
            pairs[prefix][suffix] = filename
    
    # Convert to list of tuples [(prefix, first_file, second_file), ...]
    result = []
    for prefix in sorted(pairs.keys(), key=int):
        if '0' in pairs[prefix] and '1' in pairs[prefix]:
            result.append((prefix, pairs[prefix]['0'], pairs[prefix]['1']))
    
    return result

def merge_images(first_path, second_path, output_path):
    """Merge two images vertically after upscaling the second one"""
    # Open images
    first_img = Image.open(first_path)
    second_img = Image.open(second_path)
    
    # Copy metadata from first image
    metadata = first_img.info.copy() if first_img.info else {}
    
    # First image: 3488x1984 (keep as is)
    # Second image: 2688x1536 -> upscale to 3488x1993
    target_width = 3488
    target_height_first = 1984
    target_height_second = 1993
    
    # Resize first image if needed (should already be correct size)
    if first_img.size != (target_width, target_height_first):
        first_img = first_img.resize((target_width, target_height_first), Image.LANCZOS)
    
    # Upscale second image to 3488x1993
    second_img = second_img.resize((target_width, target_height_second), Image.LANCZOS)
    
    # Create merged image: 3488x3977 (1984 + 1993)
    merged_width = target_width
    merged_height = target_height_first + target_height_second
    
    merged_img = Image.new('RGB', (merged_width, merged_height))
    merged_img.paste(first_img, (0, 0))
    merged_img.paste(second_img, (0, target_height_first))
    
    # Prepare save parameters
    save_kwargs = {'quality': 100, 'method': 6}
    
    # WebP doesn't support PNG's 'parameters' metadata field directly
    # We need to embed it in EXIF UserComment to preserve it
    try:
        # Get existing EXIF from first image if available
        exif_dict = {}
        if 'exif' in metadata:
            try:
                exif_dict = piexif.load(metadata['exif'])
            except:
                pass
        
        # If no EXIF exists, create a new one
        if not exif_dict:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
        
        # Embed all metadata fields in EXIF UserComment
        # Store the 'parameters' field (and other metadata) in EXIF UserComment
        if metadata:
            # Combine all metadata into a JSON string
            metadata_json = json.dumps(metadata)
            # EXIF UserComment tag is 37510 (0x9286)
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = metadata_json.encode('utf-8')
        
        # Convert EXIF dict to bytes
        exif_bytes = piexif.dump(exif_dict)
        save_kwargs['exif'] = exif_bytes
        
    except Exception as e:
        print(f"Warning: Could not embed metadata in EXIF: {e}")
        # Fallback: try to preserve supported metadata fields
        if metadata:
            for key in ['icc_profile', 'dpi']:
                if key in metadata:
                    save_kwargs[key] = metadata[key]
    
    merged_img.save(output_path, 'WEBP', **save_kwargs)
    
    print(f"Saved: {output_path} ({merged_width}x{merged_height})")

def main():
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__)) or '.'
    
    # Create merges subfolder
    merges_dir = os.path.join(current_dir, 'merges')
    os.makedirs(merges_dir, exist_ok=True)
    
    # Get all image pairs
    pairs = get_image_pairs(current_dir)
    
    if not pairs:
        print("No image pairs found!")
        return
    
    print(f"Found {len(pairs)} image pairs to process...")
    
    # Process each pair
    for prefix, first_file, second_file in pairs:
        first_path = os.path.join(current_dir, first_file)
        second_path = os.path.join(current_dir, second_file)
        output_path = os.path.join(merges_dir, f"{prefix}_merged.webp")
        
        try:
            merge_images(first_path, second_path, output_path)
        except Exception as e:
            print(f"Error processing pair {prefix}: {e}")

if __name__ == "__main__":
    main()

