import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "PreviewImageandviewPropertiesSG.display",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PreviewImageandviewPropertiesSG") {
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
                    this.imageParamsText = message.text;

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
                    const startY = 55;
                    
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