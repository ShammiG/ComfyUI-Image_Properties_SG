import torch
import math
import os
import folder_paths
from PIL import Image, ImageOps
import numpy as np
import hashlib

class LoadImageandviewPropertiesSG:
    """Load image with drag-and-drop and automatically extract all parameters"""
    
    CATEGORY = "image/analysis"
    
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image", "batch_count", "width", "height", "width_ratio", "height_ratio", "Resolution_in_MP")
    FUNCTION = "load_and_analyze"
    OUTPUT_NODE = True
    
    @classmethod
    def IS_CHANGED(cls, image):
        # Force re-execution when image changes
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()
    
    @classmethod
    def VALIDATE_INPUTS(cls, image):
        # Pre-validate and potentially analyze here
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True
    
    def load_and_analyze(self, image):
        # Load image from file
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        
        # Handle EXIF orientation
        img = ImageOps.exif_transpose(img)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to tensor [1, H, W, 3]
        image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        
        # Run analysis on loaded image
        batch_size, height, width, channels = image_tensor.shape
        
        # Calculate resolution in megapixels
        total_pixels = width * height
        resolution_mp = float(total_pixels / 1_000_000)
        
        # Calculate image size in MB (uncompressed in memory)
        size_bytes = width * height * channels * 4 * batch_size
        size_mb = float(size_bytes / (1024 * 1024))
        
        # GCD calculation for aspect ratio
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        
        # Find closest standard aspect ratio
        def find_closest_standard_ratio(decimal_ratio):
            standard_ratios = [
                (1.0, '1:1'), (1.25, '5:4'), (1.33333, '4:3'),
                (1.5, '3:2'), (1.6, '16:10'), (1.66667, '5:3'),
                (1.77778, '16:9'), (1.88889, '17:9'), (2.0, '2:1'),
                (2.33333, '21:9'), (2.35, '2.35:1'), (2.39, '2.39:1'),
                (2.4, '12:5'),
            ]
            
            closest_diff = float('inf')
            closest_ratio = None
            error_threshold = 0.05
            
            for std_value, std_string in standard_ratios:
                diff = abs(std_value - decimal_ratio)
                if diff < closest_diff:
                    closest_diff = diff
                    closest_ratio = std_string
            
            if closest_diff <= error_threshold:
                return closest_ratio
            return None
        
        # Calculate aspect ratio
        divisor = gcd(width, height)
        width_ratio = float(width // divisor)
        height_ratio = float(height // divisor)
        aspect_ratio_decimal = width / height
        closest_standard = find_closest_standard_ratio(aspect_ratio_decimal)
        
        # Create display lines for UI
        line1 = f"{width}x{height} | {resolution_mp:.2f}MP "
        
        if closest_standard and closest_standard != f"{int(width_ratio)}:{int(height_ratio)}":
            line2 = f"Ratio: {int(width_ratio)}:{int(height_ratio)} or {aspect_ratio_decimal:.2f}:1 or ~{closest_standard}"
        else:
            line2 = f"Ratio: {int(width_ratio)}:{int(height_ratio)} or {aspect_ratio_decimal:.2f}:1"
        
        if batch_size > 1:
            total_size_mb = size_mb * batch_size
            line3 = f"Batch: {batch_size} images | Total Tensor: {total_size_mb:.2f}MB"
        else:
            line3 = f"Tensor Size: {size_mb:.2f}MB"
        
        return {
            "ui": {"text": [line1, line2, line3]},
            "result": (image_tensor, batch_size, width, height, width_ratio, height_ratio, resolution_mp)
        }

NODE_CLASS_MAPPINGS = {
    "LoadImageandviewPropertiesSG": LoadImageandviewPropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageandviewPropertiesSG": "Load Image and view Properties-SG"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
