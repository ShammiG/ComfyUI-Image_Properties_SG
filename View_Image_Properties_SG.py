import torch
import math

class ViewImagePropertiesSG:
    """Extract all image information: dimensions, aspect ratio, resolution in MP, and file size"""
    
    CATEGORY = "image/analysis"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image", "batch_count", "width", "height", "width_ratio", "height_ratio", "Resolution_in_MP")
    FUNCTION = "image_properties"
    OUTPUT_NODE = True
    
    def image_properties(self, image):
        # Get image dimensions from tensor
        # Tensor shape is [batch_size, height, width, channels]
        batch_size, height, width, channels = image.shape
        
        # Calculate resolution in megapixels
        total_pixels = width * height
        resolution_mp = float(total_pixels / 1_000_000)
        
        # Calculate image size in MB (uncompressed in memory)
        # Tensor is float32 (4 bytes per value)
        size_bytes = width * height * channels * 4 * batch_size
        size_mb = float(size_bytes / (1024 * 1024))
        
        # Calculate GCD (Greatest Common Divisor) to simplify the aspect ratio
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        
        # Find closest standard aspect ratio
        def find_closest_standard_ratio(decimal_ratio):
            """Find the closest standard aspect ratio"""
            # Common standard aspect ratios [ratio_value, display_string]
            standard_ratios = [
                (1.0, '1:1'),
                (1.25, '5:4'),
                (1.33333, '4:3'),
                (1.5, '3:2'),
                (1.6, '16:10'),
                (1.66667, '5:3'),
                (1.77778, '16:9'),
                (1.88889, '17:9'),
                (2.0, '2:1'),
                (2.33333, '21:9'),
                (2.35, '2.35:1'),
                (2.39, '2.39:1'),
                (2.4, '12:5'),
            ]
            
            # Find the closest match
            closest_diff = float('inf')
            closest_ratio = None
            error_threshold = 0.05  # 5% tolerance
            
            for std_value, std_string in standard_ratios:
                diff = abs(std_value - decimal_ratio)
                if diff < closest_diff:
                    closest_diff = diff
                    closest_ratio = std_string
            
            # Only return if within tolerance
            if closest_diff <= error_threshold:
                return closest_ratio
            return None
        
        # Find the GCD of width and height
        divisor = gcd(width, height)
        
        # Calculate simplified aspect ratio
        width_ratio = float(width // divisor)
        height_ratio = float(height // divisor)
        
        # Calculate decimal aspect ratio
        aspect_ratio_decimal = width / height
        
        # Find closest standard ratio
        closest_standard = find_closest_standard_ratio(aspect_ratio_decimal)
        
        # Create display lines
        # Line 1: Dimensions, MP, Size
        line1 = f"{width}x{height} | {resolution_mp:.2f}MP "
        
        # Line 2: Aspect ratio with approximate standard ratio if applicable
        if closest_standard and closest_standard != f"{int(width_ratio)}:{int(height_ratio)}":
            line2 = f"Ratio: {int(width_ratio)}:{int(height_ratio)} or {aspect_ratio_decimal:.2f}:1 or ~{closest_standard}"
        else:
            line2 = f"Ratio: {int(width_ratio)}:{int(height_ratio)} or {aspect_ratio_decimal:.2f}:1"
        
        # Line 3: Tensor size with batch info
        if batch_size > 1:
            total_size_mb = size_mb * batch_size
            line3 = f"Batch: {batch_size} images | Total Tensor: {total_size_mb:.2f}MB"
        else:
            line3 = f"Tensor Size: {size_mb:.2f}MB"
        
        return {
            "ui": {"text": [line1, line2, line3]},
            "result": (image, batch_size, width, height, width_ratio, height_ratio, resolution_mp)
        }


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "ViewImagePropertiesSG": ViewImagePropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ViewImagePropertiesSG": "View Image Properties-SG"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]