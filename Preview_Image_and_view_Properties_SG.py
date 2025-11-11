import torch
import math
import os
import folder_paths
from PIL import Image, ImageOps
import numpy as np
import hashlib

class PreviewImageandviewPropertiesSG:
    """Preview image with passthrough and automatically view all properties"""
    
    CATEGORY = "image"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image", "batch_count", "width", "height", "width_ratio", "height_ratio", "Resolution_in_MP")
    FUNCTION = "preview_and_analyze"
    OUTPUT_NODE = True
    
    def preview_and_analyze(self, images):
        # Image is already a tensor [batch, H, W, 3]
        image_tensor = images
        
        # Run analysis on the image tensor
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
        
        # Convert tensor to numpy for image preview
        # ComfyUI expects images in format [B, H, W, C] with values 0-1
        images_np = (image_tensor.cpu().numpy() * 255).astype(np.uint8)
        
        # Prepare results for preview - need to save temp images
        results = []
        for i in range(batch_size):
            img_array = images_np[i]
            results.append(img_array)
        
        return {
            "ui": {
                "text": [line1, line2, line3],
                "images": self.save_images(results)
            },
            "result": (image_tensor, batch_size, width, height, width_ratio, height_ratio, resolution_mp)
        }
    
    def save_images(self, images_np_list):
        """Save images temporarily for preview"""
        from comfy.cli_args import args
        import json
        
        # Get output directory
        output_dir = folder_paths.get_temp_directory()
        
        results = []
        for i, img_array in enumerate(images_np_list):
            img = Image.fromarray(img_array)
            
            # Create unique filename
            filename = f"preview_{hash(img.tobytes())}_{i}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Save image
            img.save(filepath, compress_level=4)
            
            results.append({
                "filename": filename,
                "subfolder": "",
                "type": "temp"
            })
        
        return results

NODE_CLASS_MAPPINGS = {
    "PreviewImageandviewPropertiesSG": PreviewImageandviewPropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PreviewImageandviewPropertiesSG": "Preview Image and view Properties-SG"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]