/**
 * PromptForge — Client-side Web App
 * 
 * Port of the Python semantic optimization pipeline to vanilla JS.
 * Zero dependencies, runs entirely in the browser.
 */

// --- Constants & Config --- //

const MAX_INPUT_LENGTH = 500000;

const MODELS = {
    chatgpt: {
        aggressiveness: 1, // 0=conservative, 1=moderate, 2=aggressive
        priceInput: 2.50, // per 1M tokens
        charPerTokenRatio: 4.0 // heuristic
    },
    claude: {
        aggressiveness: 0,
        priceInput: 3.00,
        charPerTokenRatio: 3.5
    },
    gemini: {
        aggressiveness: 2,
        priceInput: 1.25,
        charPerTokenRatio: 3.8
    }
};

// --- Pipeline: Stage 1 - Normalizer --- //

const FILLER_PATTERNS = [
    // Conservative
    { regex: /\b(?:hey|hi|hello)\b[,.]?\s*/gi, level: 0 },
    { regex: /\bthanks?\b[!.]?\s*/gi, level: 0 },
    { regex: /\bthank\s+you\b[!.]?\s*/gi, level: 0 },
    { regex: /\bplease\b\s*/gi, level: 0 },
    { regex: /\bkindly\b\s*/gi, level: 0 },
    // Moderate
    { regex: /\bcould\s+you\b\s*/gi, level: 1 },
    { regex: /\bwould\s+you\b\s*/gi, level: 1 },
    { regex: /\bcan\s+you\b\s*/gi, level: 1 },
    { regex: /\bi\s+need\s+you\s+to\b\s*/gi, level: 1 },
    { regex: /\bi\s+would\s+like\s+you\s+to\b\s*/gi, level: 1 },
    { regex: /\bi\s+want\s+you\s+to\b\s*/gi, level: 1 },
    { regex: /\bif\s+possible\b[,.]?\s*/gi, level: 1 },
    // Aggressive
    { regex: /\bjust\b\s*/gi, level: 2 },
    { regex: /\bbasically\b[,.]?\s*/gi, level: 2 },
    { regex: /\bessentially\b[,.]?\s*/gi, level: 2 },
    { regex: /\bactually\b[,.]?\s*/gi, level: 2 },
    { regex: /\bliterally\b\s*/gi, level: 2 },
    { regex: /\bsimply\b\s*/gi, level: 2 },
    { regex: /\breally\b\s*/gi, level: 2 }
];

function normalize(text, aggressiveness) {
    if (!text) return "";
    
    // Normalize unicode equivalents roughly (JS normalize)
    let nText = text.normalize("NFC");
    
    // Remove zero-width spaces
    nText = nText.replace(/[\u200B-\u200D\uFEFF]/g, '');

    // Remove fillers based on aggressiveness
    for (const pattern of FILLER_PATTERNS) {
        if (pattern.level <= aggressiveness) {
            nText = nText.replace(pattern.regex, '');
        }
    }

    // Collapse whitespace
    nText = nText.replace(/\n{3,}/g, '\n\n');
    nText = nText.replace(/[ \t]{2,}/g, ' ');

    // Fix punctuation
    nText = nText.replace(/\s+([.,;:!?])/g, '$1');
    nText = nText.replace(/([.,;:!?])\s*\1+/g, '$1');

    return nText.trim();
}

// --- Pipeline: Stage 2 - Parser --- //

function extractConstraintItems(text) {
    const listMatch = text.match(/(?:^|\n)\s*[-*•]\s+(.+)/g);
    if (listMatch) {
        return listMatch.map(m => m.replace(/^[ \t]*[-*•]\s+/, '').trim()).filter(x => x);
    }
    
    const sentences = text.split(/(?<=[.!?])\s+/);
    let items = sentences.map(s => s.trim().replace(/\.$/, '')).filter(x => x);
    
    if (items.length === 1) {
        const parts = items[0].split(/\s*(?:,\s*and\s+|,\s+and\s+|\s+and\s+)/);
        if (parts.length > 1) {
            items = parts.map(p => p.trim()).filter(x => x);
        }
    }
    
    return items.length ? items : [text.trim()];
}

function parse(text) {
    if (!text) return {};
    
    // Very simplified JS parsing since full intent classification requires Spacy/regex weights
    // We rely heavily on detecting existing structure or falling back to treating it as just 'task'
    const sections = {};
    
    // Simple heuristic: Does it have explicit section headers?
    const hasHeaders = /^(?:#{1,6}\s+)?(?:task|goal|objective|constraints|rules|requirements|format|output|context|background|example)[s]?\s*[:]/im.test(text);

    if (hasHeaders) {
        let currentCategory = "task";
        let currentLines = [];
        
        const lines = text.split('\n');
        for (const line of lines) {
            const match = line.match(/^(?:#{1,6}\s+)?(task|goal|constraints|rules|requirements|format|output|context|background|example)[s]?\s*[:]\s*(.*)/i);
            
            if (match) {
                if (currentLines.length) {
                    sections[currentCategory] = (sections[currentCategory] ? sections[currentCategory] + '\n' : '') + currentLines.join('\n').trim();
                    currentLines = [];
                }
                
                let header = match[1].toLowerCase();
                // Map to canonical
                if (['goal', 'objective'].includes(header)) header = 'task';
                if (['rules', 'requirements'].includes(header)) header = 'constraints';
                if (['output', 'response'].includes(header)) header = 'format';
                if (['background', 'situation'].includes(header)) header = 'context';
                if (['examples', 'sample'].includes(header)) header = 'examples';
                
                currentCategory = header;
                if (match[2].trim()) currentLines.push(match[2].trim());
            } else {
                currentLines.push(line);
            }
        }
        if (currentLines.length) {
            sections[currentCategory] = (sections[currentCategory] ? sections[currentCategory] + '\n' : '') + currentLines.join('\n').trim();
        }
    } else {
        // Unstructured: Try to split by format cues
        const formatSplit = text.split(/format\s+(?:as|in|with):?\s*|output\s+(?:should\s+be|as)\s*/i);
        if (formatSplit.length > 1) {
            sections["format"] = formatSplit.pop().trim();
            text = formatSplit.join(" ");
        }

        const constraintSplit = text.split(/(?:must|ensure|important|avoid)\s+/i);
        if (constraintSplit.length > 1) {
            sections["task"] = constraintSplit[0].trim();
            sections["constraints"] = constraintSplit.slice(1).map((s, i) => {
                const prefix = text.match(/(?:must|ensure|important|avoid)/ig)[i].toLowerCase();
                return prefix + " " + s.trim();
            }).join('. ');
        } else {
            sections["task"] = text.trim();
        }
    }

    return sections;
}

// --- Pipeline: Stage 3 - Compressor --- //

const COMPRESSION_RULES = [
    { regex: /\bi\s+need\s+you\s+to\b/gi, rep: '' },
    { regex: /\bmake\s+sure\s+(?:that\s+)?(?:you\s+)?\b/gi, rep: 'ensure ' },
    { regex: /\bin\s+order\s+to\b/gi, rep: 'to' },
    { regex: /\bdue\s+to\s+the\s+fact\s+that\b/gi, rep: 'because' },
    { regex: /\bas\s+a\s+result\s+of\b/gi, rep: 'because' },
    { regex: /\bat\s+this\s+point\s+in\s+time\b/gi, rep: 'now' },
    { regex: /\bprior\s+to\b/gi, rep: 'before' },
    { regex: /\bon\s+a\s+regular\s+basis\b/gi, rep: 'regularly' }
];

function compressSections(sections) {
    const compressed = {};
    for (const [key, val] of Object.entries(sections)) {
        let content = val;
        for (const rule of COMPRESSION_RULES) {
            content = content.replace(rule.regex, rule.rep);
        }
        content = content.replace(/\s+/g, ' ').trim();
        if (content) compressed[key] = content;
    }
    return compressed;
}

// --- Pipeline: Stage 4 - Reconstructor --- //

function reconstruct(sections, model) {
    if (Object.keys(sections).length === 0) return "";
    
    const parts = [];
    
    if (model === 'claude') {
        // Structured / XML format
        if (sections.task) parts.push(`Task: ${sections.task}`);
        if (sections.context) parts.push(`Context: ${sections.context}`);
        if (sections.constraints) {
            const items = extractConstraintItems(sections.constraints);
            if (items.length > 1) {
                parts.push(`Constraints:\n` + items.map(i => `- ${i}`).join('\n'));
            } else {
                parts.push(`Constraints: ${sections.constraints}`);
            }
        }
        if (sections.examples) parts.push(`Examples:\n${sections.examples}`);
        if (sections.format) parts.push(`Output Format: ${sections.format}`);
        
    } else if (model === 'chatgpt') {
        // Natural format
        if (sections.task) parts.push(sections.task);
        if (sections.context) parts.push(`Background: ${sections.context}`);
        if (sections.constraints) {
            const items = extractConstraintItems(sections.constraints);
            if (items.length > 1) {
                parts.push(`Requirements:\n` + items.map(i => `- ${i}`).join('\n'));
            } else {
                parts.push(sections.constraints);
            }
        }
        if (sections.examples) parts.push(`Examples:\n${sections.examples}`);
        if (sections.format) parts.push(`Output: ${sections.format}`);
        
    } else if (model === 'gemini') {
        // Concise format
        if (sections.task) parts.push(`→ ${sections.task}`);
        if (sections.context) parts.push(sections.context);
        if (sections.constraints) {
            const items = extractConstraintItems(sections.constraints);
            parts.push(items.map(i => `• ${i}`).join('\n'));
        }
        if (sections.examples) parts.push(`Ex: ${sections.examples}`);
        if (sections.format) parts.push(`Output: ${sections.format}`);
    }
    
    return parts.join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
}

// --- Estimators --- //

function estimateTokens(text, charRatio) {
    if (!text) return 0;
    // Blend of character and word counting
    const words = (text.match(/\S+/g) || []).length;
    const charEst = text.length / charRatio;
    const wordEst = words * 1.3;
    return Math.max(1, Math.round((charEst * 0.6) + (wordEst * 0.4)));
}

// --- UI Logic --- //

document.addEventListener('DOMContentLoaded', () => {
    
    const inputEditor = document.getElementById('input-editor');
    const outputEditor = document.getElementById('output-editor');
    const btnOptimize = document.getElementById('btn-optimize');
    const btnCompare = document.getElementById('btn-compare');
    const btnClear = document.getElementById('btn-clear');
    const btnCopy = document.getElementById('btn-copy');
    const aggressionSlider = document.getElementById('aggression-slider');
    
    const tabs = document.querySelectorAll('.model-tab');
    let currentModel = 'claude';
    let outputText = '';
    
    // Switch tabs
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentModel = tab.dataset.model;
            
            // Auto-update slider based on model defaults
            aggressionSlider.value = MODELS[currentModel].aggressiveness;
            
            if (inputEditor.value.trim().length > 3) {
                runOptimization();
            }
        });
    });
    
    // Input listener
    inputEditor.addEventListener('input', () => {
        const val = inputEditor.value;
        const len = val.length;
        
        document.getElementById('stat-input-chars').textContent = `${len.toLocaleString()} chars`;
        document.getElementById('stat-input-tokens').textContent = `~${estimateTokens(val, 3.8).toLocaleString()} tokens`;
        
        btnOptimize.disabled = len < 5;
    });
    
    // Clear
    btnClear.addEventListener('click', () => {
        inputEditor.value = '';
        outputEditor.innerHTML = `
            <div class="output-placeholder">
                <div class="placeholder-icon">✨</div>
                <p>Optimized prompt will appear here</p>
                <p class="placeholder-hint">Enter a prompt and click Optimize</p>
            </div>`;
        document.getElementById('stat-input-chars').textContent = `0 chars`;
        document.getElementById('stat-input-tokens').textContent = `0 tokens`;
        document.getElementById('metrics-dashboard').classList.add('hidden');
        document.getElementById('compare-view').classList.add('hidden');
        btnOptimize.disabled = true;
        btnCopy.disabled = true;
    });

    // Copy
    btnCopy.addEventListener('click', () => {
        if (!outputText) return;
        navigator.clipboard.writeText(outputText).then(() => {
            showToast("Copied to clipboard!");
        });
    });
    
    // Optimize action
    btnOptimize.addEventListener('click', runOptimization);
    
    // Compare All action
    btnCompare.addEventListener('click', () => {
        const raw = inputEditor.value.trim();
        if (raw.length < 5) return;
        
        const grid = document.getElementById('compare-grid');
        grid.innerHTML = '';
        
        ['chatgpt', 'claude', 'gemini'].forEach(m => {
            const aggr = MODELS[m].aggressiveness;
            const n = normalize(raw, aggr);
            const s = parse(n);
            const c = compressSections(s);
            const res = reconstruct(c, m);
            
            const origTok = estimateTokens(raw, MODELS[m].charPerTokenRatio);
            const newTok = estimateTokens(res, MODELS[m].charPerTokenRatio);
            const savP = ((origTok - newTok) / Math.max(1, origTok)) * 100;
            
            const card = document.createElement('div');
            card.className = 'compare-card';
            card.innerHTML = `
                <div class="compare-card-header ${m}">
                    <span class="compare-model-name">${m.toUpperCase()}</span>
                    <span class="compare-savings">-${savP.toFixed(0)}%</span>
                </div>
                <div class="compare-card-body">${escapeHtml(res)}</div>
                <div class="compare-card-footer">
                    <span>${newTok.toLocaleString()} tokens</span>
                </div>
            `;
            grid.appendChild(card);
        });
        
        document.getElementById('compare-view').classList.remove('hidden');
    });

    // Run local pipeline
    function runOptimization() {
        const t0 = performance.now();
        const raw = inputEditor.value.trim();
        if (raw.length < 5) return;
        
        document.getElementById('compare-view').classList.add('hidden');
        
        const aggLevel = parseInt(aggressionSlider.value, 10);
        const modelConf = MODELS[currentModel];
        
        // Pipeline
        const norm = normalize(raw, aggLevel);
        const sections = parse(norm);
        const comp = compressSections(sections);
        outputText = reconstruct(comp, currentModel);
        
        const t1 = performance.now();

        // If optimization made it worse (too short to optimize usually)
        if (outputText.length >= raw.length) outputText = raw;

        // Render output
        outputEditor.textContent = outputText;
        btnCopy.disabled = false;
        
        // Metrics
        const origTok = estimateTokens(raw, modelConf.charPerTokenRatio);
        const newTok = estimateTokens(outputText, modelConf.charPerTokenRatio);
        const savedTok = origTok - newTok;
        const savP = (savedTok / Math.max(1, origTok)) * 100;
        
        document.getElementById('metric-tokens-value').textContent = savedTok > 0 ? savedTok.toLocaleString() : "0";
        document.getElementById('metric-tokens-detail').textContent = `${origTok.toLocaleString()} → ${newTok.toLocaleString()}`;
        
        document.getElementById('metric-savings-value').textContent = savedTok > 0 ? `${savP.toFixed(1)}%` : "0%";
        document.getElementById('metric-savings-detail').textContent = `${(origTok / Math.max(1, newTok)).toFixed(2)}x ratio`;
        
        const costOrig = (origTok / 1000000) * modelConf.priceInput;
        const costNew = (newTok / 1000000) * modelConf.priceInput;
        const costDiff = costOrig - costNew;
        document.getElementById('metric-cost-value').textContent = `$${costDiff.toFixed(5)}`;
        
        document.getElementById('metric-time-value').textContent = `${(t1 - t0).toFixed(1)}ms`;
        
        document.getElementById('metrics-dashboard').classList.remove('hidden');
    }
    
    function escapeHtml(str) {
        return str.replace(/[&<>"']/g, function(m) {
            switch (m) {
                case '&': return '&amp;';
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '"': return '&quot;';
                case "'": return '&#039;';
                default: return m;
            }
        });
    }

    function showToast(msg) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }
});
