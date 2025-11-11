import torch
import math
import os
import folder_paths
from PIL import Image, ImageOps
import numpy as np
import hashlib
import json
from datetime import datetime
import re

class SaveImageFormatQualityPropertiesSG:
    """Save image with custom image format and further control quality and compression levels"""
    CATEGORY = "image"
    
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.temp_dir = folder_paths.get_temp_directory()
        self.type = "output"
        self.prefix_append = ""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "Properties": ([
                    "None",
                    "Basic",
                    "Metadata",
                    "Both"
                ], {
                    "default": "Both",
                    "tooltip": "Display options:\n"
                               "• None: Hides all information\n"
                               "• Basic: Shows resolution, aspect ratio, and size\n"
                               "• Metadata: Shows model, seed, steps, CFG, sampler, scheduler\n"
                               "• Both: Shows all information"
                }),
                "format": ([
                    "PNG (lossless, larger files)",
                    "JPEG (lossy, smaller files)",
                    "WEBP (modern, good compression)",
                    "BMP (uncompressed, largest)",
                    "TIFF (flexible, lossless, limited support)",
                ],
                {
                    'default': 'PNG (lossless, larger files)',
                    'tooltip': ' ❗WARNING❗\nOnly PNG saves comfyUI workflow and metadata'
                }
                ),
            },
            "optional": {
                # PNG specific
                "png_compress_level": ("INT", {
                    "default": 9,
                    "min": 0,
                    "max": 9,
                    "step": 1,
                    "tooltip": "PNG compression level (0-9):\n"
                               "Note: All levels are lossless"
                               "• 0: No compression (fastest, largest file)\n"
                               "• 1-3: Low compression (fast, large files)\n"
                               "• 4-6: Medium compression (balanced) [Recommended: 4-6]\n"
                               "• 7-9: Maximum compression (slowest, smallest files)\n"
                }),
                # JPEG specific
                "jpeg_quality": ("INT", {
                    "default": 95,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "JPEG quality (1-100):\n"
                               "• 1-50: Low quality, visible artifacts, small files\n"
                               "• 51-75: Medium quality, some artifacts\n"
                               "• 76-90: Good quality, minimal artifacts\n"
                               "• 91-95: High quality, nearly imperceptible loss [Recommended: 90-95]\n"
                               "• 96-100: Maximum quality, large files"
                }),
                "jpeg_optimize": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Enable JPEG optimization:\n"
                               "• True: Multiple encoding passes for smaller file size (slower)\n"
                               "• False: Single pass encoding (faster)\n"
                               "Recommended: True for final output"
                }),
                "jpeg_subsampling": ([
                    "4:4:4 (No subsampling, best quality)",
                    "4:2:2 (Moderate subsampling)",
                    "4:2:0 (Maximum subsampling, smaller files)",
                    "Auto (based on quality)"
                ], {
                    "default": "Auto (based on quality)",
                    "tooltip": "Chroma subsampling method:\n"
                               "• 4:4:4: No color subsampling, best quality for detailed images\n"
                               "• 4:2:2: Half horizontal color resolution\n"
                               "• 4:2:0: Quarter color resolution (JPEG default)\n"
                               "• Auto: 4:4:4 for quality ≥95, 4:2:0 otherwise\n"
                               "Subsampling affects color detail, not luminance"
                }),
                # WebP specific
                "webp_quality": ("INT", {
                    "default": 90,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "WebP quality (1-100):\n"
                               "• 1-50: Low quality, aggressive compression\n"
                               "• 51-75: Medium quality, good compression\n"
                               "• 76-90: High quality, balanced [Recommended: 85-90]\n"
                               "• 91-100: Near-lossless to lossless, larger files\n"
                               "WebP typically achieves 25-35% smaller files than JPEG at same quality"
                }),
                "webp_method": ("INT", {
                    "default": 4,
                    "min": 0,
                    "max": 6,
                    "step": 1,
                    "tooltip": "WebP compression method (0-6):\n"
                               "• 0: Fastest, largest files\n"
                               "• 1-3: Fast compression\n"
                               "• 4: Balanced speed/compression [Recommended: 4]\n"
                               "• 5-6: Slowest, best compression\n"
                               "Higher values = better compression but slower encoding"
                }),
                "webp_lossless": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "WebP lossless mode:\n"
                               "• True: Lossless compression (like PNG but smaller)\n"
                               "• False: Lossy compression (like JPEG but better)\n"
                               "Lossless ignores quality setting and uses method only"
                }),
                # TIFF specific
                "tiff_compression": ([
                    "none (uncompressed, largest)",
                    "lzw (lossless, good compression)",
                    "tiff_deflate (lossless, better compression)",
                    "jpeg (lossy, smallest)",
                    "packbits (lossless, basic)"
                ], {
                    "default": "tiff_deflate (lossless, better compression)",
                    "tooltip": "TIFF compression algorithm:\n"
                               "• none: No compression\n"
                               "• lzw: Lempel-Ziv-Welch (widely compatible)\n"
                               "• tiff_deflate: Same as PNG compression [Recommended]\n"
                               "• jpeg: Lossy JPEG compression inside TIFF\n"
                               "• packbits: Simple run-length encoding"
                }),
                "tiff_jpeg_quality": ("INT", {
                    "default": 90,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "TIFF JPEG quality (1-100):\n"
                               "Only used when compression is 'jpeg'\n"
                               "Same scale as standard JPEG quality"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }
    
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "save_and_analyze"
    OUTPUT_NODE = True
    
    def extract_model_name(self, prompt):
        """Extract model name from prompt metadata"""
        model_name = "N/A"
        try:
            if not prompt:
                return model_name
            
            for node_id, node_data in prompt.items():
                class_type = node_data.get('class_type', '')
                inputs = node_data.get('inputs', {})
                
                if 'CheckpointLoader' in class_type and 'ckpt_name' in inputs:
                    model_name = inputs['ckpt_name']
                    break
                if 'UNETLoader' in class_type and 'unet_name' in inputs:
                    model_name = f"{inputs['unet_name']} (UNET)"
                    break
                if 'Loader' in class_type:
                    if 'ckpt_name' in inputs:
                        model_name = inputs['ckpt_name']
                        break
                    elif 'unet_name' in inputs:
                        model_name = f"{inputs['unet_name']} (UNET)"
                        break
                    elif 'model_name' in inputs:
                        model_name = inputs['model_name']
                        break
        except Exception as e:
            print(f"Error extracting model metadata: {e}")
        
        return model_name
    
    def extract_generation_params(self, prompt):
        """Extract generation parameters (seed, steps, cfg, sampler, scheduler) from prompt metadata"""
        params = {
            'seed': 'N/A',
            'steps': 'N/A',
            'cfg': 'N/A',
            'sampler': 'N/A',
            'scheduler': 'N/A'
        }
        
        try:
            if not prompt:
                return params
            
            for node_id, node_data in prompt.items():
                class_type = node_data.get('class_type', '')
                inputs = node_data.get('inputs', {})
                
                # KSampler node has all the info we need
                if class_type == "KSampler":
                    params['seed'] = inputs.get('seed', 'N/A')
                    params['steps'] = inputs.get('steps', 'N/A')
                    params['cfg'] = inputs.get('cfg', 'N/A')
                    params['sampler'] = inputs.get('sampler_name', 'N/A')
                    params['scheduler'] = inputs.get('scheduler', 'N/A')
                    return params
                
                # Check individual nodes for distributed sampler setup
                if 'seed' in inputs or 'noise_seed' in inputs:
                    params['seed'] = inputs.get('seed', inputs.get('noise_seed', params['seed']))
                if 'steps' in inputs:
                    params['steps'] = inputs.get('steps', params['steps'])
                if 'cfg' in inputs:
                    params['cfg'] = inputs.get('cfg', params['cfg'])
                if 'sampler_name' in inputs:
                    params['sampler'] = inputs.get('sampler_name', params['sampler'])
                if 'scheduler' in inputs:
                    params['scheduler'] = inputs.get('scheduler', params['scheduler'])
        except Exception as e:
            print(f"Error extracting generation parameters: {e}")
        
        return params
    
    def save_and_analyze(self, images, filename_prefix="ComfyUI", Properties="Both", format="PNG (lossless, larger files)",
                        png_compress_level=6, jpeg_quality=95, jpeg_optimize=True,
                        jpeg_subsampling="Auto (based on quality)", webp_quality=90, webp_method=4,
                        webp_lossless=False, tiff_compression="tiff_deflate (lossless, better compression)",
                        tiff_jpeg_quality=90, prompt=None, extra_pnginfo=None):
        
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
        
        # Extract metadata
        model_name = self.extract_model_name(prompt)
        gen_params = self.extract_generation_params(prompt)
        
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
        
        # Add metadata lines
        line4 = f"Model: {model_name}"
        line5 = f"Seed: {gen_params['seed']} | Steps: {gen_params['steps']} | CFG: {gen_params['cfg']}"
        line6 = f"Sampler: {gen_params['sampler']} | Scheduler: {gen_params['scheduler']}"
        
        # Build display text based on Properties selection
        if Properties == "None":
            display_lines = []
        elif Properties == "Basic":
            display_lines = [line1, line2, line3]
        elif Properties == "Metadata":
            display_lines = [line4, line5, line6]
        else:  # Both
            display_lines = [line1, line2, line3, "", line4, line5, line6]
        
        # Convert tensor to numpy for image saving
        images_np = (image_tensor.cpu().numpy() * 255).astype(np.uint8)
        
        # Save images with proper naming
        results = []
        for i in range(batch_size):
            img_array = images_np[i]
            results.append(img_array)
        
        # Collect quality parameters
        quality_params = {
            "png_compress_level": png_compress_level,
            "jpeg_quality": jpeg_quality,
            "jpeg_optimize": jpeg_optimize,
            "jpeg_subsampling": jpeg_subsampling,
            "webp_quality": webp_quality,
            "webp_method": webp_method,
            "webp_lossless": webp_lossless,
            "tiff_compression": tiff_compression,
            "tiff_jpeg_quality": tiff_jpeg_quality
        }
        
        saved_images = self.save_images_with_format(results, filename_prefix, format, quality_params, width, height)
        
        return {
            "ui": {
                "text": display_lines,
                "images": saved_images
            }
        }
    
    def save_images_with_format(self, images_np_list, filename_prefix, format_choice, quality_params, width, height):
        """Save images with formatted filename and specified format"""
        # Extract format from dropdown choice
        format_map = {
            "PNG (lossless, larger files)": "png",
            "JPEG (lossy, smaller files)": "jpg",
            "WEBP (modern, good compression)": "webp",
            "BMP (uncompressed, largest)": "bmp",
            "TIFF (flexible, lossless, limited support)": "tiff"
        }
        
        file_extension = format_map[format_choice]
        
        # Process filename prefix with date formatting
        filename_prefix = self.parse_filename(filename_prefix)
        
        # Get output path and counter
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix, self.output_dir, width, height
        )
        
        results = []
        for i, img_array in enumerate(images_np_list):
            img = Image.fromarray(img_array)
            
            # Format counter with leading zeros (5 digits)
            file_number = f"{counter:05d}"
            
            # Build final filename
            final_filename = f"{filename}_{file_number}_.{file_extension}"
            filepath = os.path.join(full_output_folder, final_filename)
            
            # Save based on format with quality settings
            if file_extension == "png":
                img.save(filepath, compress_level=quality_params["png_compress_level"])
            elif file_extension == "jpg":
                # Parse subsampling option
                subsampling_map = {
                    "4:4:4 (No subsampling, best quality)": 0,
                    "4:2:2 (Moderate subsampling)": 1,
                    "4:2:0 (Maximum subsampling, smaller files)": 2,
                    "Auto (based on quality)": -1  # Use PIL default behavior
                }
                
                subsampling_value = subsampling_map[quality_params["jpeg_subsampling"]]
                save_kwargs = {
                    "quality": quality_params["jpeg_quality"],
                    "optimize": quality_params["jpeg_optimize"]
                }
                
                # Only add subsampling if not Auto
                if subsampling_value >= 0:
                    save_kwargs["subsampling"] = subsampling_value
                
                img.save(filepath, **save_kwargs)
            elif file_extension == "webp":
                save_kwargs = {
                    "method": quality_params["webp_method"]
                }
                
                if quality_params["webp_lossless"]:
                    save_kwargs["lossless"] = True
                else:
                    save_kwargs["quality"] = quality_params["webp_quality"]
                
                img.save(filepath, **save_kwargs)
            elif file_extension == "bmp":
                img.save(filepath)
            elif file_extension == "tiff":
                # Parse compression option
                compression_map = {
                    "none (uncompressed, largest)": None,
                    "lzw (lossless, good compression)": "tiff_lzw",
                    "tiff_deflate (lossless, better compression)": "tiff_deflate",
                    "jpeg (lossy, smallest)": "jpeg",
                    "packbits (lossless, basic)": "packbits"
                }
                
                compression_value = compression_map[quality_params["tiff_compression"]]
                save_kwargs = {}
                if compression_value:
                    save_kwargs["compression"] = compression_value
                    if compression_value == "jpeg":
                        save_kwargs["quality"] = quality_params["tiff_jpeg_quality"]
                
                img.save(filepath, **save_kwargs)
            
            # For browser preview, create PNG version in TEMP folder if TIFF or BMP
            preview_filename = final_filename
            preview_subfolder = subfolder
            preview_type = self.type
            
            if file_extension in ["tiff", "bmp"]:
                # Save PNG preview to temp directory for browser display
                preview_filename = f"{filename}_{file_number}_preview.png"
                preview_path = os.path.join(self.temp_dir, preview_filename)
                img.save(preview_path, compress_level=4)
                
                # Update to use temp type for preview
                preview_subfolder = ""
                preview_type = "temp"
            
            results.append({
                "filename": preview_filename,
                "subfolder": preview_subfolder,
                "type": preview_type
            })
            
            counter += 1
        
        return results
    
    def parse_filename(self, filename_prefix):
        """
        Parse filename prefix to support ComfyUI naming schemes like %date%, %time%, etc.
        """
        # Replace %date:format% patterns (handles both date AND time components)
        def replace_date(match):
            format_str = match.group(1)
            conversions = {
                'yyyy': '%Y',
                'yy': '%y',
                'MM': '%m',
                'dd': '%d',
                'HH': '%H',
                'hh': '%H',
                'mm': '%M',
                'ss': '%S'
            }
            for old, new in conversions.items():
                format_str = format_str.replace(old, new)
            return datetime.now().strftime(format_str)
        
        filename_prefix = re.sub(r'%date:([^%]+)%', replace_date, filename_prefix)
        
        # Replace %time:format% patterns
        def replace_time(match):
            format_str = match.group(1)
            conversions = {
                'HH': '%H',
                'hh': '%H',
                'mm': '%M',
                'ss': '%S'
            }
            for old, new in conversions.items():
                format_str = format_str.replace(old, new)
            return datetime.now().strftime(format_str)
        
        filename_prefix = re.sub(r'%time:([^%]+)%', replace_time, filename_prefix)
        
        # Default replacements
        if '%date%' in filename_prefix:
            filename_prefix = filename_prefix.replace('%date%', datetime.now().strftime('%Y-%m-%d'))
        if '%time%' in filename_prefix:
            filename_prefix = filename_prefix.replace('%time%', datetime.now().strftime('%H-%M-%S'))
        if '%timestamp%' in filename_prefix:
            filename_prefix = filename_prefix.replace('%timestamp%', str(int(datetime.now().timestamp())))
        
        return filename_prefix

NODE_CLASS_MAPPINGS = {
    "SaveImageFormatQualityPropertiesSG": SaveImageFormatQualityPropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageFormatQualityPropertiesSG": "Save Image Format Quality Properties-SG"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
