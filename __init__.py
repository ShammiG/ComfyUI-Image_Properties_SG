"""
Loads image with drag-and-drop and automatically display image properties
"""

from .Load_Image_and_view_Properties_SG import LoadImageandviewPropertiesSG
from .View_Image_Properties_SG import ViewImagePropertiesSG
from .Preview_Image_and_view_Properties_SG import PreviewImageandviewPropertiesSG
from .Save_Image_and_view_properties_SG import SaveImageandviewPropertiesSG

NODE_CLASS_MAPPINGS = {
    "ViewImagePropertiesSG": ViewImagePropertiesSG,
    "LoadImageandviewPropertiesSG": LoadImageandviewPropertiesSG,
    "PreviewImageandviewPropertiesSG": PreviewImageandviewPropertiesSG,
    "SaveImageandviewPropertiesSG": SaveImageandviewPropertiesSG
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ViewImagePropertiesSG": "View Image Properties-SG",
    "LoadImageandviewPropertiesSG": "Load Image and view Properties-SG",
    "PreviewImageandviewPropertiesSG": "Preview Image and view Properties-SG",
    "SaveImageandviewPropertiesSG": "Save Image and view Properties-SG"
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
