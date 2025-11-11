import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "SaveImageandviewPropertiesSG.display",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "SaveImageandviewPropertiesSG") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Set initial minimum width to 410px only when first created
                const currentSize = this.size || this.computeSize();
                this.size = [Math.max(410, currentSize[0]), currentSize[1]];
                
                // Add a custom widget that reserves space but doesn't draw input
                const displayWidget = this.addCustomWidget({
                    name: "display_info",
                    type: "DISPLAY_INFO",
                    value: [],
                    draw: function(ctx, node, width, y) {
                        if (!node.imageParamsText || node.imageParamsText.length === 0) {
                            return 0;
                        }
                        
                        const lineHeight = 18;
                        const padding = 5;
                        const totalHeight = (node.imageParamsText.length * lineHeight) + (padding * 2);
                        
                        // Draw text lines
                        ctx.save();
                        ctx.font = "12px monospace";
                        ctx.fillStyle = "#ccc";
                        ctx.textBaseline = "top";
                        
                        for (let i = 0; i < node.imageParamsText.length; i++) {
                            ctx.fillText(node.imageParamsText[i], 10, y + padding + (i * lineHeight));
                        }
                        
                        ctx.restore();
                        return totalHeight;
                    },
                    computeSize: function(width) {
                        if (!this.parent || !this.parent.imageParamsText) {
                            return [width, 0];
                        }
                        
                        const lineHeight = 18;
                        const padding = 10;
                        const height = (this.parent.imageParamsText.length * lineHeight) + padding;
                        return [width, height];
                    }
                });
                
                displayWidget.parent = this;
                this.displayWidget = displayWidget;
                
                // Setup widget visibility based on format
                this.updateWidgetVisibility = function() {
                    const formatWidget = this.widgets.find(w => w.name === "format");
                    if (!formatWidget) return;
                    
                    const format = formatWidget.value;
                    
                    // Define which widgets belong to which format
                    const widgetMap = {
                        "PNG (lossless, larger files)": ["png_compress_level"],
                        "JPEG (lossy, smaller files)": ["jpeg_quality", "jpeg_optimize", "jpeg_subsampling"],
                        "WEBP (modern, good compression)": ["webp_quality", "webp_method", "webp_lossless"],
                        "BMP (uncompressed, largest)": [],
                        "TIFF (flexible, lossless, limited support)": ["tiff_compression", "tiff_jpeg_quality"]
                    };
                    
                    const activeWidgets = widgetMap[format] || [];
                    
                    // Hide/show widgets based on format
                    for (const widget of this.widgets) {
                        // Skip non-quality widgets
                        if (widget.name === "format" || widget.name === "filename_prefix" || widget.name === "display_info") {
                            continue;
                        }
                        
                        // Check if this is a format-specific widget
                        const isFormatWidget = widget.name.startsWith("png_") || 
                                             widget.name.startsWith("jpeg_") || 
                                             widget.name.startsWith("webp_") || 
                                             widget.name.startsWith("tiff_");
                        
                        if (isFormatWidget) {
                            const shouldShow = activeWidgets.includes(widget.name);
                            
                            if (shouldShow) {
                                // Show widget - use proper computeSize
                                if (widget.origComputeSize) {
                                    widget.computeSize = widget.origComputeSize;
                                    delete widget.origComputeSize;
                                }
                                
                                // Remove hidden flag
                                delete widget.hidden;
                                
                            } else {
                                // Hide widget - store original computeSize
                                if (!widget.origComputeSize) {
                                    widget.origComputeSize = widget.computeSize || function(width) {
                                        return [width, 30];
                                    };
                                }
                                
                                // Make widget take no space
                                widget.computeSize = function(width) { 
                                    return [width, -4]; 
                                };
                                
                                // Mark as hidden but don't change type
                                widget.hidden = true;
                            }
                        }
                    }
                    
                    // CRITICAL FIX: Preserve the current width, only adjust height
                    const currentWidth = this.size[0];
                    const newSize = this.computeSize();
                    this.setSize([currentWidth, newSize[1]]);
                    
                    // Force canvas redraw
                    if (app.graph) {
                        app.graph.setDirtyCanvas(true, true);
                    }
                };
                
                // Hook into format widget changes
                const formatWidget = this.widgets.find(w => w.name === "format");
                if (formatWidget) {
                    const originalCallback = formatWidget.callback;
                    const node = this;
                    
                    formatWidget.callback = function(value) {
                        // Call original callback first
                        if (originalCallback) {
                            originalCallback.call(this, value);
                        }
                        
                        // Update visibility immediately without delay
                        node.updateWidgetVisibility();
                    };
                }
                
                // Initial visibility update
                setTimeout(() => {
                    this.updateWidgetVisibility();
                }, 100);
                
                return r;
            };
            
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                onConfigure?.apply(this, arguments);
                
                if (info.imageParamsText) {
                    this.imageParamsText = info.imageParamsText;
                }
                
                // DON'T reset size when loading - preserve user's size preference
                // Only set minimum width on first creation
                
                // Restore widget visibility after loading
                setTimeout(() => {
                    if (this.updateWidgetVisibility) {
                        this.updateWidgetVisibility();
                    }
                }, 150);
            };
            
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(info) {
                const data = onSerialize ? onSerialize.apply(this, arguments) : info;
                
                if (this.imageParamsText) {
                    data.imageParamsText = this.imageParamsText;
                }
                
                return data;
            };
            
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
                
                if (message && message.text) {
                    this.imageParamsText = message.text;
                    
                    // Hide dimension overlays using DOM manipulation
                    setTimeout(() => {
                        const captions = document.querySelectorAll(
                            '.comfy-img-preview .caption, .p-viewer-caption, [class*="caption"]'
                        );
                        
                        captions.forEach(cap => {
                            cap.style.display = 'none';
                            cap.style.visibility = 'hidden';
                            cap.style.opacity = '0';
                        });
                        
                        console.log(`[SaveImageandviewPropertiesSG] Hidden ${captions.length} dimension overlays`);
                    }, 100);
                    
                    // Only resize if it's the first time
                    if (!this._hasResized) {
                        this.setSize(this.computeSize());
                        this._hasResized = true;
                    }
                }
            };
        }
    }
});
