import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ViewImagePropertiesSG.display",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ViewImagePropertiesSG") {
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Set minimum width only on initial creation
                const minWidth = 300;
                if (this.size[0] < minWidth) {
                    this.size[0] = minWidth;
                }
                
                return result;
            };

            const onConfigure = nodeType.prototype.onConfigure;
                nodeType.prototype.onConfigure = function(info) {
                    onConfigure?.apply(this, arguments);
                    if (info.imageParamsText) {
                        this.imageParamsText = info.imageParamsText;
    }
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
                onExecuted?.apply(this, arguments);
                
                if (message.text) {
                    this.imageParamsText = message.text; // Store as array [line1, line2, line3]
                    // Removed height adjustment to prevent stretching
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
                    
                    // Start from top (changed from bottom)
                    const startY = 65; // Position at top, just below title
                    
                    if (Array.isArray(this.imageParamsText)) {
                        // Draw each line
                        for (let i = 0; i < this.imageParamsText.length; i++) {
                            const textY = startY + (i * lineHeight);
                            ctx.fillText(this.imageParamsText[i], textX, textY);
                        }
                    } else {
                        // Fallback for single string
                        ctx.fillText(this.imageParamsText, textX, startY);
                    }
                    
                    ctx.restore();
                }
            };
        }
    }
});