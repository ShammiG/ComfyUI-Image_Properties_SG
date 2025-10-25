import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "LoadImageandviewPropertiesSG.display",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LoadImageandviewPropertiesSG") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Set minimum width only on initial creation
                const minWidth = 300; // Adjust this value as needed
                if (this.size[0] < minWidth) {
                    this.size[0] = minWidth;
                }
                
                const imageWidget = this.widgets?.find((w) => w.name === "image");
                
                if (imageWidget) {
                    const self = this;
                    let lastValue = imageWidget.value;
                    
                    // Create a timer to check for value changes
                    const checkInterval = setInterval(() => {
                        if (imageWidget.value !== lastValue) {
                            lastValue = imageWidget.value;
                            
                            if (imageWidget.value && typeof imageWidget.value === 'string') {
                                // Load and analyze the image
                                const img = new Image();
                                const imageUrl = `/view?filename=${encodeURIComponent(imageWidget.value)}&type=input&subfolder=`;
                                
                                img.onload = function() {
                                    const width = img.naturalWidth;
                                    const height = img.naturalHeight;
                                    
                                    // Calculate parameters
                                    const resolution_mp = (width * height / 1_000_000).toFixed(2);
                                    
                                    // GCD calculation
                                    function gcd(a, b) {
                                        while (b) {
                                            let temp = b;
                                            b = a % b;
                                            a = temp;
                                        }
                                        return a;
                                    }
                                    
                                    const divisor = gcd(width, height);
                                    const width_ratio = width / divisor;
                                    const height_ratio = height / divisor;
                                    const aspect_decimal = (width / height).toFixed(2);
                                    
                                    // Find closest standard ratio
                                    const standardRatios = [
                                        [1.0, '1:1'], [1.25, '5:4'], [1.33333, '4:3'],
                                        [1.5, '3:2'], [1.6, '16:10'], [1.66667, '5:3'],
                                        [1.77778, '16:9'], [1.88889, '17:9'], [2.0, '2:1'],
                                        [2.33333, '21:9'], [2.35, '2.35:1'], [2.39, '2.39:1'],
                                        [2.4, '12:5']
                                    ];
                                    
                                    let closestRatio = null;
                                    let closestDiff = Infinity;
                                    const aspectRatio = width / height;
                                    
                                    for (const [value, label] of standardRatios) {
                                        const diff = Math.abs(value - aspectRatio);
                                        if (diff < closestDiff) {
                                            closestDiff = diff;
                                            closestRatio = label;
                                        }
                                    }
                                    
                                    if (closestDiff > 0.05) {
                                        closestRatio = null;
                                    }
                                    
                                    // Calculate tensor size
                                    const tensorSizeMB = (width * height * 3 * 4 / (1024 * 1024)).toFixed(2);
                                    
                                    // Create display lines
                                    const line1 = `${width}x${height} | ${resolution_mp}MP`;
                                    
                                    let line2;
                                    if (closestRatio && closestRatio !== `${width_ratio}:${height_ratio}`) {
                                        line2 = `Ratio: ${width_ratio}:${height_ratio} or ${aspect_decimal}:1 or ~${closestRatio}`;
                                    } else {
                                        line2 = `Ratio: ${width_ratio}:${height_ratio} or ${aspect_decimal}:1`;
                                    }
                                    
                                    const line3 = `Tensor Size: ${tensorSizeMB}MB`;
                                    
                                    // Store and redraw
                                    self.imageParamsText = [line1, line2, line3];
                                    
                                    // Adjust node height only (not width - let user resize)
                                    const baseHeight = self.computeSize()[1];
                                    const textHeight = 65;
                                    self.size[1] = Math.max(baseHeight + textHeight, 250);
                                    
                                    // Force redraw
                                    app.graph.setDirtyCanvas(true, true);
                                };
                                
                                img.onerror = function() {
                                    console.error("Failed to load image:", imageUrl);
                                };
                                
                                img.src = imageUrl;
                            }
                        }
                    }, 500); // Check every 500ms
                    
                    // Clean up interval when node is removed
                    const onRemoved = this.onRemoved;
                    this.onRemoved = function() {
                        clearInterval(checkInterval);
                        if (onRemoved) {
                            onRemoved.apply(this, arguments);
                        }
                    };
                }
                
                return result;
            };
            
            const onExecuted = nodeType.prototype.onExecuted;
            
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                
                if (message.text) {
                    this.imageParamsText = message.text;
                    
                    // Only adjust height, not width
                    const baseHeight = this.computeSize()[1];
                    const textHeight = 65;
                    this.size[1] = Math.max(baseHeight + textHeight, 250);
                }
            };
            
            const origDrawForeground = nodeType.prototype.onDrawForeground;
            
            nodeType.prototype.onDrawForeground = function (ctx) {
                origDrawForeground?.apply(this, arguments);
                
                if (this.imageParamsText) {
                    ctx.save();
                    ctx.font = "12px monospace";
                    ctx.fillStyle = "#ccc";
                    
                    const textX = 10;
                    const lineHeight = 18;
                    
                    // Position text at top
                    const startY = 65;
                    
                    // Draw each line
                    this.imageParamsText.forEach((line, index) => {
                        const yPos = startY + (index * lineHeight);
                        ctx.fillText(line, textX, yPos);
                    });
                    
                    ctx.restore();
                }
            };
        }
    }
});
