// Configuration
const API_BASE = 'http://localhost:8000/api';

// Global variables
let cy;
let currentPerson = '';
let treeData = { ancestors: [], descendants: [] };

// Initialize Cytoscape with hierarchical layout
function initCytoscape() {
    console.log("Initializing Cytoscape...");
    
    // Register Dagre extension if available
    if (typeof cytoscape !== 'undefined' && typeof dagre !== 'undefined' && typeof cytoscapeDagre !== 'undefined') {
        cytoscape.use(cytoscapeDagre);
        console.log("Dagre layout registered successfully");
    } else {
        console.warn("Dagre extension not available, will use fallback layout");
    }
    
    const cyContainer = document.getElementById('cy');
    if (!cyContainer) {
        console.error("Container element 'cy' not found!");
        return;
    }

    try {
        cy = cytoscape({
            container: cyContainer,
            
            elements: [], // Start with empty elements
            
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#e2e8f0',
                        'label': 'data(name)',
                        'width': 'mapData(level, 0, 4, 80, 50)',
                        'height': 'mapData(level, 0, 4, 80, 50)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': 'mapData(level, 0, 4, 16, 11)',
                        'font-weight': 'bold',
                        'color': '#1a202c',
                        'text-outline-width': '2px',
                        'text-outline-color': '#ffffff',
                        'border-width': '3px',
                        'border-color': '#ffffff',
                        'text-wrap': 'wrap',
                        'text-max-width': '90px',
                        'border-style': 'solid',
                        'shape': 'ellipse'
                    }
                },
                {
                    selector: 'node[sex = "male"]',
                    style: {
                        'background-color': '#4299e1',
                        'border-color': '#2b6cb0'
                    }
                },
                {
                    selector: 'node[sex = "female"]',
                    style: {
                        'background-color': '#f56565',
                        'border-color': '#c53030'
                    }
                },
                {
                    selector: 'node[type = "current"]',
                    style: {
                        'background-color': '#9f7aea',
                        'border-color': '#6b46c1',
                        'width': '100px',
                        'height': '100px',
                        'font-size': '18px',
                        'font-weight': 'bold',
                        'border-width': '5px',
                        'z-index': 10,
                        'shape': 'diamond'
                    }
                },
                {
                    selector: 'node[generation = "ancestor"]',
                    style: {
                        'opacity': 0.9,
                        'text-opacity': 1
                    }
                },
                {
                    selector: 'node[generation = "descendant"]',
                    style: {
                        'opacity': 0.9,
                        'text-opacity': 1
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 4,
                        'line-color': '#a0aec0',
                        'target-arrow-color': '#a0aec0',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'arrow-scale': 1.5,
                        'opacity': 0.8,
                        'control-point-step-size': 40
                    }
                },
                {
                    selector: 'edge[type = "ancestor"]',
                    style: {
                        'line-color': '#4299e1',
                        'target-arrow-color': '#4299e1',
                        'line-style': 'solid'
                    }
                },
                {
                    selector: 'edge[type = "descendant"]',
                    style: {
                        'line-color': '#48bb78',
                        'target-arrow-color': '#48bb78',
                        'line-style': 'solid'
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-color': '#fbd38d',
                        'border-width': '4px',
                        'background-color': '#fed7aa'
                    }
                }
            ],
            
            layout: {
                name: 'grid',
                padding: 30
            }
        });

        console.log("Cytoscape initialized successfully:", cy);

        // Enhanced click handler for nodes
        cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            const nodeName = node.data('name');
            
            // Highlight selected node
            cy.nodes().removeClass('selected');
            node.addClass('selected');
            
            // Auto-visualize the complete family tree for the clicked person
            if (nodeName && nodeName !== currentPerson) {
                // Add a message to chat showing what's happening
                addChatMessage(`Exploring ${nodeName}'s complete family tree...`, 'user');
                
                // Call the backend to get both ancestors and descendants
                visualizePersonFamilyTree(nodeName);
            }
        });

        // Double-click to explore new tree (keep this as backup)
        cy.on('dblclick', 'node', function(evt) {
            const node = evt.target;
            const nodeName = node.data('name');
            if (nodeName !== currentPerson) {
                const query = `Show me the ancestors of ${nodeName}`;
                document.getElementById('chatInput').value = query;
                sendChatMessage();
            }
        });

        // Zoom and pan controls
        cy.on('zoom', function(evt) {
            updateZoomLevel(cy.zoom());
        });

    } catch (error) {
        console.error("Error initializing Cytoscape:", error);
    }
}

// Build hierarchical family tree
function buildFamilyTree(centralPerson, ancestors, descendants) {
    console.log("Building hierarchical tree for:", centralPerson);
    
    if (!cy) {
        console.error("Cytoscape instance is not initialized!");
        addChatMessage("Error: Graph visualization not ready. Please refresh the page.", 'error');
        return;
    }

    const nodes = [];
    const edges = [];
    const nodeMap = new Map();
    const edgeSet = new Set();

    // Helper function to create safe node ID
    const createNodeId = (name) => {
        return name.replace(/[^a-zA-Z0-9]/g, '_');
    };

    // Create central person node
    const centralPersonId = createNodeId(centralPerson);
    const centralPersonData = {
        id: centralPersonId,
        name: centralPerson,
        type: 'current',
        generation: 'current',
        level: 0,
        sex: 'unknown'
    };
    nodes.push({ data: centralPersonData });
    nodeMap.set(centralPersonId, centralPersonData);

    // Process ancestors (going up the hierarchy)
    if (ancestors && Array.isArray(ancestors)) {
        ancestors.forEach((path, pathIndex) => {
            if (Array.isArray(path)) {
                let previousNodeId = centralPersonId;
                
                path.forEach((person, index) => {
                    if (person && person.name) {
                        const nodeId = createNodeId(person.name);
                        const currentLevel = -(index + 1); // -1, -2, -3, etc.
                        
                        if (!nodeMap.has(nodeId)) {
                            const nodeData = {
                                id: nodeId,
                                name: person.name,
                                sex: person.sex || 'unknown',
                                type: 'ancestor',
                                generation: 'ancestor',
                                level: currentLevel,
                                pathIndex: pathIndex
                            };
                            nodes.push({ data: nodeData });
                            nodeMap.set(nodeId, nodeData);
                        }

                        const edgeId = `${nodeId}_to_${previousNodeId}`;
                        if (!edgeSet.has(edgeId)) {
                            edges.push({
                                data: {
                                    id: edgeId,
                                    source: nodeId,
                                    target: previousNodeId,
                                    type: 'ancestor'
                                }
                            });
                            edgeSet.add(edgeId);
                        }

                        previousNodeId = nodeId;
                    }
                });
            }
        });
    }

    // Process descendants (going down the hierarchy)
    if (descendants && Array.isArray(descendants)) {
        descendants.forEach((path, pathIndex) => {
            if (Array.isArray(path)) {
                let previousNodeId = centralPersonId;
                
                path.forEach((person, index) => {
                    if (person && person.name) {
                        const nodeId = createNodeId(person.name);
                        const currentLevel = index + 1; // 1, 2, 3, etc.
                        
                        if (!nodeMap.has(nodeId)) {
                            const nodeData = {
                                id: nodeId,
                                name: person.name,
                                sex: person.sex || 'unknown',
                                type: 'descendant',
                                generation: 'descendant',
                                level: currentLevel,
                                pathIndex: pathIndex
                            };
                            nodes.push({ data: nodeData });
                            nodeMap.set(nodeId, nodeData);
                        }

                        const edgeId = `${previousNodeId}_to_${nodeId}`;
                        if (!edgeSet.has(edgeId)) {
                            edges.push({
                                data: {
                                    id: edgeId,
                                    source: previousNodeId,
                                    target: nodeId,
                                    type: 'descendant'
                                }
                            });
                            edgeSet.add(edgeId);
                        }

                        previousNodeId = nodeId;
                    }
                });
            }
        });
    }

    console.log("Nodes to add:", nodes.length);
    console.log("Edges to add:", edges.length);
    
    // Validate that we have at least the central person
    if (nodes.length === 0) {
        console.error("No nodes to display");
        addChatMessage("No family tree data available to display.", 'error');
        return;
    }

    try {
        // Clear and rebuild
        cy.elements().remove();
        cy.add(nodes);
        cy.add(edges);
        
        // Try hierarchical layout with better error handling
        let layoutApplied = false;
        
        // First try Dagre if available
        if (typeof cytoscapeDagre !== 'undefined') {
            try {
                console.log("Applying Dagre hierarchical layout");
                const layoutOptions = {
                    name: 'dagre',
                    rankDir: 'TB',
                    spacingFactor: 1.5,
                    nodeDimensionsIncludeLabels: true,
                    animate: true,
                    animationDuration: 800,
                    fit: true,
                    padding: 50,
                    rankSep: 100,
                    nodeSep: 80,
                    edgeSep: 20
                };
                
                const layout = cy.layout(layoutOptions);
                layout.run();
                layoutApplied = true;
                
                // Fit to viewport after layout completes
                setTimeout(() => {
                    cy.fit(cy.elements(), 60);
                    cy.center();
                    // Highlight central person
                    cy.$(`#${centralPersonId}`).addClass('selected');
                }, 900);
                
            } catch (dagreError) {
                console.error("Dagre layout failed:", dagreError);
                layoutApplied = false;
            }
        }
        
        // Fallback to breadthfirst if Dagre failed
        if (!layoutApplied) {
            console.log("Using breadthfirst hierarchical layout");
            try {
                const breadthFirstOptions = {
                    name: 'breadthfirst',
                    directed: true,
                    roots: `#${centralPersonId}`,
                    spacingFactor: 2,
                    animate: true,
                    animationDuration: 800,
                    fit: true,
                    padding: 50,
                    avoidOverlap: true,
                    nodeDimensionsIncludeLabels: true
                };
                
                const layout = cy.layout(breadthFirstOptions);
                layout.run();
                layoutApplied = true;
                
                setTimeout(() => {
                    cy.fit(cy.elements(), 60);
                    cy.center();
                    cy.$(`#${centralPersonId}`).addClass('selected');
                }, 900);
                
            } catch (breadthFirstError) {
                console.error("Breadthfirst layout failed:", breadthFirstError);
            }
        }
        
        // Final fallback to grid layout
        if (!layoutApplied) {
            console.log("Using grid layout as final fallback");
            const gridOptions = {
                name: 'grid',
                fit: true,
                padding: 50,
                avoidOverlap: true,
                animate: true,
                animationDuration: 500
            };
            
            const layout = cy.layout(gridOptions);
            layout.run();
            
            setTimeout(() => {
                cy.fit(cy.elements(), 60);
                cy.center();
                cy.$(`#${centralPersonId}`).addClass('selected');
            }, 600);
        }

        console.log("Family tree built successfully");
        showSuccessMessage(`Family tree loaded for ${centralPerson}`);

    } catch (error) {
        console.error("Error building tree:", error);
        addChatMessage(`Error building tree: ${error.message}`, 'error');
        
        // Emergency fallback - just show the nodes without layout
        try {
            cy.elements().remove();
            cy.add(nodes);
            cy.fit(cy.elements(), 100);
        } catch (emergencyError) {
            console.error("Emergency fallback failed:", emergencyError);
            addChatMessage("Critical error: Unable to display family tree.", 'error');
        }
    }
}

// Update zoom level display
function updateZoomLevel(zoom) {
    const zoomLevel = Math.round(zoom * 100);
    document.getElementById('zoomLevel').textContent = `${zoomLevel}%`;
}

// Control functions
function zoomIn() {
    if (cy) cy.zoom(cy.zoom() * 1.2);
}

function zoomOut() {
    if (cy) cy.zoom(cy.zoom() * 0.8);
}

function fitToScreen() {
    if (cy) cy.fit(cy.elements(), 50);
}

function centerView() {
    if (cy) cy.center();
}

function resetLayout() {
    if (cy && currentPerson) {
        buildFamilyTree(currentPerson, treeData.ancestors, treeData.descendants);
    }
}

// Show success message
function showSuccessMessage(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-notification';
    successDiv.textContent = message;
    document.body.appendChild(successDiv);
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

// Handle enter key press for chat
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// Add message to chat
function addChatMessage(message, type = 'bot') {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error("Chat messages container not found!");
        return;
    }
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    // Pretty print JSON objects from the API
    if (typeof message === 'object' && message !== null) {
        messageDiv.innerHTML = `<pre>${JSON.stringify(message, null, 2)}</pre>`;
    } else {
        messageDiv.textContent = message;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// New function to visualize a person's complete family tree
async function visualizePersonFamilyTree(personName) {
    try {
        // Show loading state
        const chatSendBtn = document.getElementById('chatSendBtn');
        const originalState = { disabled: chatSendBtn.disabled, innerHTML: chatSendBtn.innerHTML };
        chatSendBtn.disabled = true;
        chatSendBtn.innerHTML = '<div class="spinner"></div>';

        // Call the backend with a visualization query
        const response = await fetch(`${API_BASE}/natural_query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: `Visualize ${personName} family tree` })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }

        const result = await response.json();

        // Handle the response
        if (result.type === 'full_tree') {
            const ancestorCount = result.ancestors ? result.ancestors.length : 0;
            const descendantCount = result.descendants ? result.descendants.length : 0;
            
            addChatMessage(`Building complete family tree for ${result.person} with ${ancestorCount} ancestor paths and ${descendantCount} descendant paths...`, 'bot');
            
            currentPerson = result.person;
            buildFamilyTree(result.person, result.ancestors, result.descendants);
            treeData = { ancestors: result.ancestors, descendants: result.descendants };
        } else if (result.message) {
            addChatMessage(result.message, 'bot');
        } else {
            addChatMessage(`Visualized family tree for ${personName}`, 'bot');
        }

        // Restore button state
        chatSendBtn.disabled = originalState.disabled;
        chatSendBtn.innerHTML = originalState.innerHTML;

    } catch (error) {
        console.error('Error visualizing family tree:', error);
        addChatMessage(`Sorry, I couldn't visualize ${personName}'s family tree: ${error.message}`, 'error');
        
        // Restore button state
        const chatSendBtn = document.getElementById('chatSendBtn');
        chatSendBtn.disabled = false;
        chatSendBtn.innerHTML = '<span>📤</span>';
    }
}

// Send chat message
async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    
    const message = chatInput.value.trim();
    if (!message) return;

    addChatMessage(message, 'user');
    
    chatInput.value = '';
    chatSendBtn.disabled = true;
    chatSendBtn.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch(`${API_BASE}/natural_query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }

        const result = await response.json();

        // Check if the response is for a full family tree visualization
        if (result.type === 'full_tree') {
            const person = result.person;
            const ancestorCount = result.ancestors ? result.ancestors.length : 0;
            const descendantCount = result.descendants ? result.descendants.length : 0;
            
            addChatMessage(`Building complete family tree for ${person} with ${ancestorCount} ancestor paths and ${descendantCount} descendant paths...`, 'bot');
            
            currentPerson = person;
            buildFamilyTree(person, result.ancestors, result.descendants);
            treeData = { ancestors: result.ancestors, descendants: result.descendants };
        }
        // Check if the response is for a single tree visualization (ancestors or descendants only)
        else if (result.type === 'ancestors' || result.type === 'descendants') {
            const person = result.person;
            const count = result.data ? result.data.length : 0;
            const relationshipType = result.type === 'ancestors' ? 'ancestor paths' : 'descendant paths';
            
            addChatMessage(`Found ${count} ${relationshipType} for ${person}. Building family tree visualization...`, 'bot');
            
            currentPerson = person;
            if (result.type === 'ancestors') {
                buildFamilyTree(person, result.data, []);
                treeData = { ancestors: result.data, descendants: [] };
            } else {
                buildFamilyTree(person, [], result.data);
                treeData = { ancestors: [], descendants: result.data };
            }
        } else if (result.message) {
            // Handle conversational responses
            addChatMessage(result.message, 'bot');
        } else {
            // Fallback for any other response format
            addChatMessage(JSON.stringify(result, null, 2), 'bot');
        }

    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage(`Sorry, I encountered an error: ${error.message}`, 'error');
    } finally {
        chatSendBtn.disabled = false;
        chatSendBtn.innerHTML = '<span>📤</span>';
    }
}

// Handle knowledge base updates (add/remove facts)
async function handleKbUpdate(action) {
    const parentName = document.getElementById('parentName').value.trim();
    const childName = document.getElementById('childName').value.trim();

    if (!parentName || !childName) {
        addChatMessage('Please enter both a parent and child name.', 'error');
        return;
    }

    // Capitalize first letter of names
    const formattedParent = parentName.charAt(0).toUpperCase() + parentName.slice(1);
    const formattedChild = childName.charAt(0).toUpperCase() + childName.slice(1);

    let endpoint = '';
    let payload = {};
    let successMessage = '';

    if (action === 'add') {
        // First, check if the relationship already exists to avoid duplicates
        try {
            const checkQuery = `Is ${formattedParent} a parent of ${formattedChild}?`;
            const checkResponse = await fetch(`${API_BASE}/natural_query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: checkQuery })
            });
            if (checkResponse.ok) {
                const checkResult = await checkResponse.json();
                // If the backend's response indicates the relationship exists, stop here.
                if (checkResult.message && checkResult.message.toLowerCase().startsWith('yes')) {
                    addChatMessage(`Relationship (Parent ${formattedParent} ${formattedChild}) already exists.`, 'bot');
                    showSuccessMessage('Relationship already in knowledge base.');
                    return;
                }
            }
        } catch (e) {
            // If the check fails, we can still proceed, but log the error.
            console.warn("Could not verify relationship existence before adding:", e);
        }

        const parentGender = document.getElementById('parentGender').value;
        const childGender = document.getElementById('childGender').value;
        
        endpoint = `${API_BASE}/add_facts`;
        payload = {
            facts: [
                `(Parent ${formattedParent} ${formattedChild})`,
                `(${parentGender} ${formattedParent})`,
                `(${childGender} ${formattedChild})`
            ]
        };
        successMessage = `Successfully added relationship and gender facts for ${formattedParent} and ${formattedChild}.`;
        addChatMessage(`Attempting to add relationship: (Parent ${formattedParent} ${formattedChild})...`, 'user');

    } else if (action === 'remove') {
        endpoint = `${API_BASE}/remove_fact`;
        payload = {
            fact: `(Parent ${formattedParent} ${formattedChild})`
        };
        successMessage = `Successfully removed relationship: (Parent ${formattedParent} ${formattedChild}).`;
        addChatMessage(`Attempting to remove relationship: (Parent ${formattedParent} ${formattedChild})...`, 'user');
    }

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || `API error: ${response.status}`);
        }

        const result = await response.json();
        addChatMessage(result.message || successMessage, 'bot');
        showSuccessMessage(result.message || successMessage);

        // Clear inputs after success
        document.getElementById('parentName').value = '';
        document.getElementById('childName').value = '';

    } catch (error) {
        console.error('KB update error:', error);
        addChatMessage(`Error: ${error.message}`, 'error');
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM Content Loaded");
    
    // Initialize Cytoscape
    initCytoscape();
    
    // Add initial chat message
    setTimeout(() => {
        addChatMessage('🌳 Hi! I\'m your family tree assistant. You can ask me things like:\n\n• "Visualize Kevin\'s family tree" (creates complete tree)\n• "Show me Laura\'s ancestors" (shows ancestor tree)\n• "Who are Charles\'s children?"\n• "What is Diana\'s gender?"\n\nWhat would you like to know?', 'bot');
    }, 500);
});