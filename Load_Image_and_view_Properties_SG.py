import torch
import math
import os
import folder_paths
from PIL import Image, ImageOps
import numpy as np
import hashlib
import json
import re

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
            },
        }
    
    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("image", "mask", "width", "height", "width_ratio", "height_ratio", "Resolution_in_MP")
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
    
    def extract_model_name(self, img):
        """Extract model name from image metadata"""
        model_name = "N/A"
        try:
            if not hasattr(img, 'info') or not img.info:
                return model_name
            
            if 'prompt' in img.info:
                try:
                    prompt_data = json.loads(img.info['prompt'])
                    for node_id, node_data in prompt_data.items():
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
                    print(f"Error parsing prompt metadata: {e}")
            
            if model_name == "N/A" and 'workflow' in img.info:
                try:
                    workflow_data = json.loads(img.info['workflow'])
                    for node in workflow_data.get('nodes', []):
                        node_type = node.get('type', '')
                        if 'Checkpoint' in node_type or 'Loader' in node_type:
                            widgets = node.get('widgets_values', [])
                            if widgets and len(widgets) > 0:
                                model_name = widgets[0]
                                break
                except Exception as e:
                    print(f"Error parsing workflow metadata: {e}")
            
            if model_name == "N/A" and 'parameters' in img.info:
                try:
                    params = img.info['parameters']
                    model_pattern = r'Model:\s*([^,\n]+)'
                    match = re.search(model_pattern, params)
                    if match:
                        model_name = match.group(1).strip()
                except Exception as e:
                    print(f"Error parsing A1111 metadata: {e}")
        
        except Exception as e:
            print(f"Error extracting model metadata: {e}")
        
        return model_name
    
    def extract_generation_params(self, img):
        """Extract generation parameters (seed, steps, cfg, sampler, scheduler) from image metadata"""
        params = {
            'seed': 'N/A',
            'steps': 'N/A',
            'cfg': 'N/A',
            'sampler': 'N/A',
            'scheduler': 'N/A'
        }
        
        try:
            if not hasattr(img, 'info') or not img.info:
                return params
            
            # Try ComfyUI format first
            if 'prompt' in img.info:
                try:
                    prompt_data = json.loads(img.info['prompt'])
                    for node_id, node_data in prompt_data.items():
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
                    print(f"Error parsing ComfyUI generation params: {e}")
            
            # Try A1111/Forge format
            if 'parameters' in img.info and any(v == 'N/A' for v in params.values()):
                try:
                    metadata_text = img.info['parameters']
                    
                    seed_match = re.search(r'Seed:\s*(\d+)', metadata_text)
                    if seed_match:
                        params['seed'] = int(seed_match.group(1))
                    
                    steps_match = re.search(r'Steps:\s*(\d+)', metadata_text)
                    if steps_match:
                        params['steps'] = int(steps_match.group(1))
                    
                    cfg_match = re.search(r'CFG scale:\s*([\d.]+)', metadata_text)
                    if cfg_match:
                        params['cfg'] = float(cfg_match.group(1))
                    
                    sampler_match = re.search(r'Sampler:\s*([^,\n]+)', metadata_text)
                    if sampler_match:
                        params['sampler'] = sampler_match.group(1).strip()
                    
                    scheduler_match = re.search(r'Schedule type:\s*([^,\n]+)', metadata_text)
                    if scheduler_match:
                        params['scheduler'] = scheduler_match.group(1).strip()
                except Exception as e:
                    print(f"Error parsing A1111 generation params: {e}")
        
        except Exception as e:
            print(f"Error extracting generation parameters: {e}")
        
        return params
    
    def load_and_analyze(self, image):
        # Load image from file
        image_path = folder_paths.get_annotated_filepath(image)
        img = Image.open(image_path)
        
        # Extract metadata
        model_name = self.extract_model_name(img)
        gen_params = self.extract_generation_params(img)
        
        # Handle EXIF orientation
        img = ImageOps.exif_transpose(img)
        
        # Convert to RGB if needed
        if img.mode == 'I':
            img = img.point(lambda i: i * (1 / 255))
        
        # Store original for mask extraction
        original_img = img
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to tensor [1, H, W, 3]
        image_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        
        # Generate mask from alpha channel
        if 'A' in original_img.getbands():
            mask = np.array(original_img.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            # Create mask matching image dimensions (all white/unmasked)
            mask = torch.zeros((img.size[1], img.size[0]), dtype=torch.float32, device="cpu")
        
        # Run analysis on loaded image
        batch_size, height, width, channels = image_tensor.shape
        
        # Calculate resolution in megapixels
        total_pixels = width * height
        resolution_mp = float(total_pixels / 1_000_000)
             
        # Get actual file 
        try:
            file_size_bytes = os.path.getsize(image_path)
            file_size_mb = float(file_size_bytes) / (1024 * 1024)
        except:
            file_size_mb = 0.0

        
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
        
        line3 = f"File Size: {file_size_mb:.2f}MB"
    
        # Add metadata lines
        line4 = f"Model: {model_name}"
        line5 = f"Seed: {gen_params['seed']} | Steps: {gen_params['steps']} | CFG: {gen_params['cfg']}"
        line6 = f"Sampler: {gen_params['sampler']} | Scheduler: {gen_params['scheduler']}"
        
        return {
            "ui": {"text": [line1, line2, line3, "", line4, line5, line6]},
            "result": (image_tensor, mask, width, height, width_ratio, height_ratio, resolution_mp)
        }

NODE_CLASS_MAPPINGS = {
    "LoadImageandviewPropertiesSG": LoadImageandviewPropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageandviewPropertiesSG": "Load Image and view Properties-SG"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
