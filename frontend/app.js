/**
 * Agent Platform Frontend Application
 * Handles UI interactions, JSON-RPC communication, and A2A protocol
 */

const TERMINAL_TASK_STATES = new Set(['completed', 'failed', 'cancelled']);

class A2AUploadService {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.extensionUri = "urn:orquestrator:artifact-upload:v1";
        this.maxChunkSize = 1000000; // 1MB chunks
    }

    async uploadFile(file, sessionId, userId, onProgress = null) {
        try {
            // Start upload
            const startResponse = await this.startUpload(file, sessionId, userId);
            const uploadId = startResponse.result.uploadId;

            // Upload file in chunks
            const fileData = await this.fileToArrayBuffer(file);
            const totalChunks = Math.ceil(fileData.byteLength / this.maxChunkSize);

            for (let i = 0; i < totalChunks; i++) {
                const start = i * this.maxChunkSize;
                const end = Math.min(start + this.maxChunkSize, fileData.byteLength);
                const chunk = fileData.slice(start, end);
                const chunkBase64 = this.arrayBufferToBase64(chunk);

                await this.appendChunk(uploadId, chunkBase64, start);

                // Report progress
                if (onProgress) {
                    onProgress((i + 1) / totalChunks * 100);
                }
            }

            // Finish upload
            const finishResponse = await this.finishUpload(uploadId, 'session');
            return finishResponse.result;

        } catch (error) {
            console.error('Upload failed:', error);
            throw error;
        }
    }

    async startUpload(file, sessionId, userId) {
        const request = {
            jsonrpc: "2.0",
            method: "artifactUpload/start",
            params: {
                filename: file.name,
                mimeType: file.type || 'application/octet-stream',
                userId: userId,
                sessionId: sessionId
            },
            id: this.generateId()
        };

        return await this.sendRequest(request);
    }

    async appendChunk(uploadId, chunkBase64, offset) {
        const request = {
            jsonrpc: "2.0",
            method: "artifactUpload/append",
            params: {
                uploadId: uploadId,
                chunkBase64: chunkBase64,
                offset: offset
            },
            id: this.generateId()
        };

        return await this.sendRequest(request);
    }

    async finishUpload(uploadId, scope = 'session') {
        const request = {
            jsonrpc: "2.0",
            method: "artifactUpload/finish",
            params: {
                uploadId: uploadId,
                scope: scope
            },
            id: this.generateId()
        };

        return await this.sendRequest(request);
    }

    async abortUpload(uploadId) {
        const request = {
            jsonrpc: "2.0",
            method: "artifactUpload/abort",
            params: {
                uploadId: uploadId
            },
            id: this.generateId()
        };

        return await this.sendRequest(request);
    }

    async sendRequest(request) {
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-A2A-Extensions': this.extensionUri
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error.message || 'Upload error');
        }

        return data;
    }

    fileToArrayBuffer(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }

    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    generateId() {
        return 'upload_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
}

class AgentPlatform {
    constructor() {
        this.apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://localhost:8000';
        this.sessionId = null; // Will be set when user creates or loads a session
        this.sessionsListContainer = null; // Reference to sessions list container
        this.currentAgentName = null; // Default agent name, will be updated from agent card

        // Add debugging to track sessionId changes
        let originalSessionId = this.sessionId;
        Object.defineProperty(this, 'sessionId', {
            get: function () {
                return originalSessionId;
            },
            set: function (value) {
                if (originalSessionId !== value) {
                    console.log('🔄 sessionId changed from', originalSessionId, 'to', value);
                }
                originalSessionId = value;
            }
        });
        this.userId = localStorage.getItem('userId') || this.generateUserId();
        this.sessions = [];
        this.agents = [];
        this.attachments = [];
        this.pendingInputRequests = new Map();
        this.activeInputContext = null;
        this.defaultInputPlaceholder = 'Type your message... (Press Enter to send, Shift+Enter for new line)';
        this.isTyping = false;
        this.processingSessions = new Set(); // Track which sessions are currently processing
        this.toolCallMessages = new Map(); // Track tool calls by ID to match requests and responses
        this.toolCallStatusById = new Map(); // Track latest pending status per tool call
        this.activeTaskStorageKey = 'activeTaskSubscriptions';
        this.activeTaskSubscriptions = new Map(); // taskId -> subscription metadata
        this.streamContexts = new Map(); // streamId -> context
        this.sessionArtifactRefs = new Map(); // sessionId -> [{ app, user, session, filename, mime }]
        this.displayedArtifactIds = new Set(); // Track artifact IDs that have been displayed to prevent duplicates
        this.processedTaskArtifacts = new Map(); // Track which tasks have had their artifacts processed (taskId -> Set of artifact content hashes)
        this.streamingEnabled = localStorage.getItem('streamingEnabled') !== 'false'; // Default to true
        this.toastBehavior = localStorage.getItem('toastBehavior') || 'stack'; // Default to stack

        this.loadActiveTaskSubscriptionsFromStorage();

        // Initialize A2A upload service
        this.uploadService = new A2AUploadService(this.apiEndpoint);

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSessions();
        this.updateUserDisplay();
        this.sessions.forEach(session => {
            if (!this.sessionArtifactRefs.has(session.id)) {
                this.sessionArtifactRefs.set(session.id, []);
            }
        });

        // Initialize input controls as disabled until agent status is determined
        this.updateInputControlsState(false);

        // This will handle both agent connection and sub-agent loading
        this.updateOrchestratorHeader();
        this.applyTheme();
        this.initializePushNotifications();
        this.resumeActiveTaskStreams();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async updateOrchestratorHeader() {
        const { retryAttempts, retryInterval } = this.getRetryConfig();

        // Show initial loading state
        this.showConnectionStatus('Connecting to agent...', 'loading');

        const result = await this.retryAgentConnection(retryAttempts, retryInterval);

        if (result.success) {
            try {
                const orchestratorEndpoint = this.apiEndpoint || 'http://localhost:8000';
                const response = await fetch(`${orchestratorEndpoint}/.well-known/agent-card.json`);

                if (response.ok) {
                    const agentCard = await response.json();
                    const agentName = agentCard.name || 'Agent Name';

                    // Store the current agent name for use throughout the app
                    this.currentAgentName = agentName;

                    const agentBadge = document.querySelector('.agent-badge');
                    const statusDot = document.querySelector('.agent-indicator .status-dot');

                    if (agentBadge) {
                        agentBadge.textContent = agentName;
                    }

                    if (statusDot) {
                        statusDot.className = 'status-dot online';
                    }

                    // Show/hide the "Get Authenticated Agent Card" button based on supportsAuthenticatedExtendedCard
                    this.updateAuthenticatedAgentCardButton(agentCard.supportsAuthenticatedExtendedCard);

                    // Extract sub-agents from the orchestrator card
                    this.extractSubAgents(agentCard);

                    // Enable input controls since agent is online
                    this.updateInputControlsState(true);
                } else {
                    this.setOrchestratorFallback();
                }
            } catch (error) {
                console.error('Failed to fetch orchestrator agent card:', error);
                this.setOrchestratorFallback();
            }
        } else {
            // All retry attempts failed
            this.setOrchestratorFallback();
        }
    }

    setOrchestratorFallback() {
        const agentBadge = document.querySelector('.agent-badge');
        const statusDot = document.querySelector('.agent-indicator .status-dot');

        if (agentBadge) {
            agentBadge.textContent = 'Agent Name';
        }

        if (statusDot) {
            statusDot.className = 'status-dot offline';
        }

        // Hide the authenticated agent card button when there's an error
        this.updateAuthenticatedAgentCardButton(false);

        // Disable input controls since agent is offline
        this.updateInputControlsState(false);
    }

    updateAuthenticatedAgentCardButton(supportsAuthenticatedExtendedCard) {
        const getAgentCardBtn = document.getElementById('getAgentCardBtn');
        if (getAgentCardBtn) {
            // Show button only if explicitly set to true, hide otherwise (including undefined/null)
            if (supportsAuthenticatedExtendedCard === true) {
                getAgentCardBtn.style.display = 'inline-block';
                console.log('✅ Authenticated Agent Card button shown - agent supports authenticated extended cards');
            } else {
                getAgentCardBtn.style.display = 'none';
                console.log('❌ Authenticated Agent Card button hidden - agent does not support authenticated extended cards');
            }
        }
    }

    updateInputControlsState(isAgentOnline) {
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const newChatBtn = document.getElementById('newChatBtn');
        const attachBtn = document.getElementById('attachBtn');

        if (messageInput) {
            messageInput.disabled = !isAgentOnline;
            if (isAgentOnline) {
                if (this.activeInputContext) {
                    messageInput.placeholder = this.getInputContextPlaceholder(this.activeInputContext);
                } else {
                    messageInput.placeholder = this.defaultInputPlaceholder;
                }
            } else {
                messageInput.placeholder = 'Agent is offline - please wait for connection...';
            }
        }

        if (sendBtn) {
            sendBtn.disabled = !isAgentOnline;
        }

        if (newChatBtn) {
            newChatBtn.disabled = !isAgentOnline;
        }

        if (attachBtn) {
            attachBtn.disabled = !isAgentOnline;
        }

        console.log(`🔄 Input controls ${isAgentOnline ? 'enabled' : 'disabled'} - agent is ${isAgentOnline ? 'online' : 'offline'}`);
    }

    // Sleep utility function
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Get retry configuration from settings
    getRetryConfig() {
        const retryAttempts = parseInt(localStorage.getItem('retryAttempts')) || parseInt(document.getElementById('retryAttempts').value);
        const retryInterval = parseInt(localStorage.getItem('retryInterval')) || parseInt(document.getElementById('retryInterval').value);
        return { retryAttempts, retryInterval };
    }

    // Retry mechanism for agent connection
    async retryAgentConnection(maxAttempts, intervalSeconds) {
        console.log(`🔄 Starting agent connection retry: ${maxAttempts} attempts, ${intervalSeconds}s interval`);
        this.showToast(`Starting connection retry: ${maxAttempts} attempts`, 'info');

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                console.log(`🔄 Connection attempt ${attempt}/${maxAttempts}`);
                this.showToast(`Connection attempt ${attempt}/${maxAttempts}`, 'info');

                const orchestratorEndpoint = this.apiEndpoint || 'http://localhost:8000';
                const response = await fetch(`${orchestratorEndpoint}/.well-known/agent-card.json`);

                if (response.ok) {
                    console.log(`✅ Agent connection successful on attempt ${attempt}`);
                    this.showToast(`✅ Connected successfully on attempt ${attempt}`, 'success');
                    return { success: true, attempt };
                } else {
                    console.log(`❌ Agent connection failed on attempt ${attempt}: ${response.status}`);
                    this.showToast(`❌ Attempt ${attempt} failed (${response.status})`, 'error');
                }
            } catch (error) {
                console.log(`❌ Agent connection error on attempt ${attempt}:`, error.message);
                this.showToast(`❌ Attempt ${attempt} failed: ${error.message}`, 'error');
            }

            // Don't sleep after the last attempt
            if (attempt < maxAttempts) {
                console.log(`⏳ Waiting ${intervalSeconds} seconds before next attempt...`);
                this.showToast(`⏳ Waiting ${intervalSeconds}s before next attempt...`, 'info');
                await this.sleep(intervalSeconds * 1000);
            }
        }

        console.log(`❌ All ${maxAttempts} connection attempts failed`);
        this.showToast(`❌ All ${maxAttempts} connection attempts failed`, 'error');
        return { success: false, attempt: maxAttempts };
    }

    // Show connection status message
    showConnectionStatus(message, type = 'info') {
        console.log(`🔗 Connection Status: ${message}`);
        this.showToast(message, type);

        // Update agent badge with connection status
        const agentBadge = document.querySelector('.agent-badge');
        if (agentBadge && type === 'loading') {
            agentBadge.textContent = 'Connecting...';
        }
    }

    generateTaskId() {
        return 'task_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    generateSessionData() {
        return {
            id: this.sessionId, // Use sessionId as session ID (no confusion)
            sessionId: this.sessionId, // Session ID for this session
            taskIds: [], // Array of task_ids associated with this session
            title: 'New Session',
            messages: [],
            created_at: new Date().toISOString(),
            lastMessageAt: new Date().toISOString()
        };
    }

    generateUserId() {
        const userId = 'user_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('userId', userId);
        return userId;
    }

    updateUserDisplay() {
        const userNameElement = document.getElementById('userNameDisplay');
        if (userNameElement && this.userId) {
            userNameElement.textContent = this.userId;
        }
    }

    getWelcomeMessageHTML() {
        return `
            <div class="welcome-message" id="welcomeMessage">
                <div class="welcome-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <h2>Welcome to Agent Platform</h2>
                <p>Start a conversation with our AI agents. They can help with:</p>
                <div class="capability-cards">
                    <div class="capability-card">
                        <i class="fas fa-shield-alt"></i>
                        <h4>Cybersecurity</h4>
                        <p>Security analysis, threat detection</p>
                    </div>
                    <div class="capability-card">
                        <i class="fas fa-server"></i>
                        <h4>DevOps</h4>
                        <p>Deployment, CI/CD, Infrastructure</p>
                    </div>
                    <div class="capability-card">
                        <i class="fas fa-database"></i>
                        <h4>Data</h4>
                        <p>Analysis, ETL, Reporting</p>
                    </div>
                    <div class="capability-card">
                        <i class="fas fa-brain"></i>
                        <h4>Machine Learning</h4>
                        <p>Model training, Predictions</p>
                    </div>
                </div>
            </div>
        `;
    }

    logout() {
        // Show confirmation dialog
        this.showConfirmModal(
            'Logout',
            'Are you sure you want to logout? This will clear all your sessions and generate a new user ID.',
            () => {
                this.performLogout();
            }
        );
    }

    performLogout() {
        // Clear all user data
        localStorage.removeItem('userId');
        localStorage.removeItem('sessionData');
        localStorage.removeItem('userSessionId');

        // Generate new user ID
        this.userId = this.generateUserId();

        // Clear sessions
        this.sessions = [];
        this.sessionId = this.generateSessionId();
        this.pendingInputRequests.clear();
        this.clearActiveInputContext();
        this.sessionArtifactRefs.clear();
        this.sessionArtifactRefs.set(this.sessionId, []);

        // Update UI
        this.updateUserDisplay();
        this.updateSessionsList();

        // Clear chat and recreate welcome message
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = this.getWelcomeMessageHTML();
        }

        // Update chat title
        document.getElementById('chatTitle').textContent = 'New Session';

        this.showToast('Logged out successfully. New user ID generated.', 'success');
    }

    setupEventListeners() {
        // Message input
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        this.inputContextBanner = document.getElementById('inputContextBanner');
        this.inputContextDetails = document.getElementById('inputContextDetails');
        const clearInputContextBtn = document.getElementById('clearInputContextBtn');
        if (clearInputContextBtn) {
            clearInputContextBtn.addEventListener('click', () => this.clearActiveInputContext());
        }

        messageInput.addEventListener('input', (e) => {
            this.autoResizeTextarea(e.target);
            sendBtn.disabled = !e.target.value.trim();
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());

        // File attachment
        const attachBtn = document.getElementById('attachBtn');
        const fileInput = document.getElementById('fileInput');

        attachBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileAttachment(e));

        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', (e) => {
                console.log('🖱️ New Chat button clicked!', e);
                this.createNewChat();
            });
        }

        // Delete all sessions button
        const deleteAllBtn = document.getElementById('deleteAllBtn');
        if (deleteAllBtn) {
            deleteAllBtn.addEventListener('click', () => this.deleteAllSessions());
        }

        // Streaming toggle button
        const streamingToggleBtn = document.getElementById('streamingToggleBtn');
        if (streamingToggleBtn) {
            streamingToggleBtn.addEventListener('click', () => this.toggleStreaming());
            this.updateStreamingIcon();
        }

        // Theme toggle button
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => this.toggleTheme());
        }

        // Export chat button
        const exportChatBtn = document.getElementById('exportChatBtn');
        if (exportChatBtn) {
            exportChatBtn.addEventListener('click', () => this.exportChat());
        }

        // Settings
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettings());
        }

        const closeSettingsBtn = document.getElementById('closeSettingsBtn');
        if (closeSettingsBtn) {
            closeSettingsBtn.addEventListener('click', () => this.hideSettings());
        }

        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        // Theme buttons
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.changeTheme(e.target.dataset.theme));
        });

        // Task management controls
        document.getElementById('cancelAllTasksBtn').addEventListener('click', () => this.cancelAllRunningTasks());
        document.getElementById('refreshTaskStatusBtn').addEventListener('click', () => this.refreshAllTaskStatus());

        // Agent card
        document.getElementById('getAgentCardBtn').addEventListener('click', () => this.loadAgentCard());

        // Notification controls
        document.getElementById('notificationsEnabled').addEventListener('change', (e) => this.toggleNotifications(e.target.checked));
        document.getElementById('taskCompletedNotifications').addEventListener('change', (e) => this.updateNotificationPreferences());
        document.getElementById('taskFailedNotifications').addEventListener('change', (e) => this.updateNotificationPreferences());

        // Agent panel
        document.getElementById('closePanelBtn').addEventListener('click', () => this.hideAgentPanel());
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }

    // JSON-RPC communication methods (using root endpoint)
    async sendJSONRPCRequest(method, params) {
        try {
            const jsonrpcRequest = {
                jsonrpc: "2.0",
                method: method,
                params: params,
                id: this.generateMessageId()
            };

            const response = await fetch(`${this.apiEndpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(jsonrpcRequest)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Check for JSON-RPC errors
            if (data.error) {
                const errorMessage = this.getJSONRPCErrorMessage(data.error);
                this.showToast(errorMessage, 'error');
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error('Error sending JSON-RPC request:', error);
            throw error;
        }
    }

    // Get error message from JSON-RPC error
    getJSONRPCErrorMessage(error) {
        return error.message || 'Unknown error';
    }

    // Get task status using A2A's tasks/get method
    async getTaskStatus(taskId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/get', {
                task_id: taskId
            });
            return response;
        } catch (error) {
            console.error('Error getting task status:', error);
            throw error;
        }
    }

    // Cancel a running task using A2A's tasks/cancel method
    async cancelTask(taskId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/cancel', {
                task_id: taskId
            });
            return response;
        } catch (error) {
            console.error('Error canceling task:', error);
            throw error;
        }
    }

    // Set push notification config using A2A's tasks/pushNotificationConfig/set method
    async setPushNotificationConfig(taskId, config) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/pushNotificationConfig/set', {
                task_id: taskId,
                config: config
            });
            return response;
        } catch (error) {
            console.error('Error setting push notification config:', error);
            throw error;
        }
    }

    // Get push notification config using A2A's tasks/pushNotificationConfig/get method
    async getPushNotificationConfig(taskId, configId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/pushNotificationConfig/get', {
                task_id: taskId,
                config_id: configId
            });
            return response;
        } catch (error) {
            console.error('Error getting push notification config:', error);
            throw error;
        }
    }

    // List push notification configs using A2A's tasks/pushNotificationConfig/list method
    async listPushNotificationConfigs(taskId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/pushNotificationConfig/list', {
                task_id: taskId
            });
            return response;
        } catch (error) {
            console.error('Error listing push notification configs:', error);
            throw error;
        }
    }

    // Delete push notification config using A2A's tasks/pushNotificationConfig/delete method
    async deletePushNotificationConfig(taskId, configId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/pushNotificationConfig/delete', {
                task_id: taskId,
                config_id: configId
            });
            return response;
        } catch (error) {
            console.error('Error deleting push notification config:', error);
            throw error;
        }
    }

    // Resubscribe to task updates using A2A's tasks/resubscribe method
    async resubscribeToTasks(subscriptionId) {
        try {
            const response = await this.sendJSONRPCRequest('tasks/resubscribe', {
                subscription_id: subscriptionId
            });
            return response;
        } catch (error) {
            console.error('Error resubscribing to tasks:', error);
            throw error;
        }
    }

    // Send streaming message using A2A's message/stream method
    async sendStreamingMessage(message, onChunk) {
        try {
            const response = await this.sendJSONRPCRequest('message/stream', {
                message: message,
                onChunk: onChunk
            });
            return response;
        } catch (error) {
            console.error('Error sending streaming message:', error);
            throw error;
        }
    }


    // Get authenticated agent card using A2A's agent/getAuthenticatedExtendedCard method
    async getAgentCard() {
        try {
            const response = await this.sendJSONRPCRequest('agent/getAuthenticatedExtendedCard', {});
            return response;
        } catch (error) {
            console.error('Error getting agent card:', error);
            throw error;
        }
    }

    // Stream JSON-RPC request according to A2A streaming spec (message/stream, tasks/resubscribe, etc.)
    async streamJsonRpcRequest({ method, params, sessionId, resumeContext = null, requestId = null }) {
        const id = requestId || this.generateMessageId();
        const payload = {
            jsonrpc: "2.0",
            method,
            params,
            id
        };

        const controller = new AbortController();
        const headers = {
            'Content-Type': 'application/json',
            'Accept': this.streamingEnabled ? 'text/event-stream, application/json' : 'application/json'
        };

        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            if (!response.ok) {
                const error = `HTTP error! status: ${response.status}`;
                this.showToast(error, 'error');
                throw new Error(error);
            }

            const context = {
                streamId: id,
                sessionId,
                method,
                controller,
                resumeContext
            };

            this.streamContexts.set(id, context);

            const consumption = this.consumeStreamResponse(response, context)
                .catch(err => {
                    if (err.name === 'AbortError') return;
                    console.error(`Stream ${id} failed:`, err);
                    this.showToast('Streaming channel interrupted', 'warning');
                })
                .finally(() => {
                    this.streamContexts.delete(id);
                });

            context.consumePromise = consumption;

            return { streamId: id, controller };
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error(`Error starting stream for ${method}:`, error);
                this.showToast('Failed to open streaming channel', 'error');
            }
            throw error;
        }
    }

    async consumeStreamResponse(response, context) {
        const contentType = response.headers.get('content-type') || '';

        if (!response.body || !response.body.getReader) {
            const data = await response.json();
            this.handleStreamPayload(data, context);
            return;
        }

        const reader = response.body.getReader();

        if (contentType.includes('text/event-stream')) {
            await this.consumeSseStream(reader, context);
        } else {
            await this.consumeNdjsonStream(reader, context);
        }
    }

    async consumeSseStream(reader, context) {
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            buffer = this.processSseBuffer(buffer, context);
        }

        if (buffer.trim().length > 0) {
            this.processSseBuffer(buffer + '\n\n', context);
        }
    }

    processSseBuffer(buffer, context) {
        let delimiter;
        while ((delimiter = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, delimiter);
            buffer = buffer.slice(delimiter + 2);

            const lines = rawEvent.split(/\r?\n/);
            const dataLines = lines
                .filter(line => line.startsWith('data:'))
                .map(line => line.slice(5).trim());

            if (dataLines.length === 0) continue;

            const payload = dataLines.join('\n');
            this.handleStreamChunk(payload, context);
        }
        return buffer;
    }

    async consumeNdjsonStream(reader, context) {
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            buffer = this.processNdjsonBuffer(buffer, context);
        }

        if (buffer.trim().length > 0) {
            this.handleStreamChunk(buffer.trim(), context);
        }
    }

    processNdjsonBuffer(buffer, context) {
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
            const chunk = buffer.slice(0, newlineIndex).trim();
            buffer = buffer.slice(newlineIndex + 1);
            if (chunk) {
                this.handleStreamChunk(chunk, context);
            }
        }
        return buffer;
    }

    handleStreamChunk(chunk, context) {
        if (!chunk) return;
        const trimmed = chunk.trim();
        if (!trimmed) return;

        const payloads = this.extractJsonPayloads(trimmed);
        payloads.forEach(payloadStr => {
            if (!payloadStr) return;
            try {
                const payload = JSON.parse(payloadStr);
                this.handleStreamPayload(payload, context);
            } catch (error) {
                console.warn('Failed to parse stream chunk:', payloadStr, error);
            }
        });
    }

    extractJsonPayloads(chunk) {
        const payloads = [];

        const trySingle = chunk => {
            try {
                JSON.parse(chunk);
                payloads.push(chunk);
                return true;
            } catch (e) {
                return false;
            }
        };

        if (trySingle(chunk)) {
            return payloads;
        }

        const segments = [];
        let depth = 0;
        let start = null;
        let inString = false;
        let escapeNext = false;

        for (let i = 0; i < chunk.length; i++) {
            const char = chunk[i];

            if (escapeNext) {
                escapeNext = false;
                continue;
            }

            if (char === '\\') {
                escapeNext = true;
                continue;
            }

            if (char === '"') {
                inString = !inString;
                continue;
            }

            if (inString) {
                continue;
            }

            if (char === '{' || char === '[') {
                if (depth === 0) {
                    start = i;
                }
                depth++;
            } else if (char === '}' || char === ']') {
                depth = Math.max(0, depth - 1);
                if (depth === 0 && start !== null) {
                    segments.push(chunk.slice(start, i + 1));
                    start = null;
                }
            }
        }

        if (segments.length > 0) {
            return segments;
        }

        // Fallback: split on newlines that look like JSON boundaries
        const fallback = chunk.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
        return fallback.length > 0 ? fallback : [chunk];
    }

    handleStreamPayload(payload, context) {
        if (!payload) return;

        if (payload.error) {
            const message = this.getJSONRPCErrorMessage(payload.error);
            this.showToast(message, 'error');
            if (context.sessionId) {
                this.updateTypingIndicatorForSession(context.sessionId, false);
            }
            return;
        }

        const normalized = this.normalizeTaskPayload(payload);
        if (normalized) {
            this.handleAgentResponse(normalized, context.sessionId);
            this.trackTaskSubscription(normalized.result, context);
        } else {
            console.debug('Streaming payload without task result:', payload);
        }
    }

    normalizeTaskPayload(payload) {
        if (!payload) return null;

        if (payload.result && payload.result.kind === 'task') {
            return payload;
        }

        if (payload.result && payload.result.kind === 'status-update') {
            return payload;
        }

        if (payload.result && payload.result.kind === 'artifact-update') {
            return payload;
        }

        if (payload.result && payload.result.task) {
            return {
                jsonrpc: '2.0',
                result: payload.result.task
            };
        }

        if (payload.method && payload.params && payload.params.task) {
            return {
                jsonrpc: '2.0',
                result: payload.params.task
            };
        }

        return null;
    }

    trackTaskSubscription(task, context) {
        if (!task || !task.id) return;

        const subscriptionInfo = this.extractSubscriptionInfo(task);

        if (!subscriptionInfo) {
            if (this.isTerminalTaskState(task.status?.state)) {
                this.completeTaskSubscription(task.id);
            }
            return;
        }

        const record = {
            taskId: task.id,
            subscriptionId: subscriptionInfo.subscriptionId,
            sessionId: context.sessionId,
            lastEventId: subscriptionInfo.lastEventId || null,
            lastState: task.status?.state || null,
            updatedAt: new Date().toISOString()
        };

        this.persistActiveSubscriptionRecord(record);

        if (this.isTerminalTaskState(task.status?.state)) {
            this.completeTaskSubscription(task.id);
        }
    }

    extractSubscriptionInfo(task) {
        if (!task) return null;

        const candidates = [
            task.subscription,
            task.subscriptionInfo,
            task.subscription_details,
            task.status?.subscription,
            task.status?.subscriptionInfo
        ];

        let subscriptionId = task.subscriptionId || task.subscription_id || null;
        let lastEventId = task.lastEventId || task.last_event_id || null;

        for (const candidate of candidates) {
            if (!candidate) continue;
            subscriptionId = subscriptionId || candidate.subscriptionId || candidate.subscription_id || candidate.id;
            lastEventId = lastEventId || candidate.lastEventId || candidate.last_event_id || candidate.checkpoint;
        }

        if (!subscriptionId && task.status?.subscriptionId) {
            subscriptionId = task.status.subscriptionId;
        }

        if (subscriptionId) {
            return {
                subscriptionId,
                lastEventId: lastEventId || null
            };
        }

        return null;
    }

    persistActiveSubscriptionRecord(record) {
        if (!record.taskId || !record.subscriptionId) return;
        this.activeTaskSubscriptions.set(record.taskId, record);
        this.saveActiveTaskSubscriptions();
    }

    completeTaskSubscription(taskId) {
        if (!taskId) return;
        if (this.activeTaskSubscriptions.has(taskId)) {
            this.activeTaskSubscriptions.delete(taskId);
            this.saveActiveTaskSubscriptions();
        }
    }

    loadActiveTaskSubscriptionsFromStorage() {
        try {
            const stored = JSON.parse(localStorage.getItem(this.activeTaskStorageKey) || '{}');
            Object.values(stored).forEach(record => {
                if (record.taskId && record.subscriptionId) {
                    this.activeTaskSubscriptions.set(record.taskId, record);
                }
            });
        } catch (error) {
            console.warn('Failed to parse active task subscription store:', error);
            localStorage.removeItem(this.activeTaskStorageKey);
            this.activeTaskSubscriptions.clear();
        }
    }

    saveActiveTaskSubscriptions() {
        const payload = {};
        this.activeTaskSubscriptions.forEach((value, key) => {
            payload[key] = value;
        });
        localStorage.setItem(this.activeTaskStorageKey, JSON.stringify(payload));
    }

    async resumeActiveTaskStreams() {
        if (this.activeTaskSubscriptions.size === 0) {
            return;
        }

        for (const record of Array.from(this.activeTaskSubscriptions.values())) {
            if (!record.subscriptionId) continue;
            if (record.lastState && this.isTerminalTaskState(record.lastState)) {
                this.activeTaskSubscriptions.delete(record.taskId);
                continue;
            }

            try {
                await this.streamJsonRpcRequest({
                    method: 'tasks/resubscribe',
                    params: {
                        subscription_id: record.subscriptionId,
                        after_event_id: record.lastEventId || undefined
                    },
                    sessionId: record.sessionId,
                    resumeContext: record
                });
                console.log(`Resubscribed to task ${record.taskId}`);
            } catch (error) {
                console.error(`Failed to resume subscription ${record.subscriptionId}:`, error);
                this.activeTaskSubscriptions.delete(record.taskId);
            }
        }

        this.saveActiveTaskSubscriptions();
    }

    isTerminalTaskState(state) {
        if (!state) return false;
        return TERMINAL_TASK_STATES.has(state.toLowerCase());
    }

    // Initialize push notifications
    async initializePushNotifications() {
        try {
            // Check if browser supports notifications
            if (!('Notification' in window)) {
                console.warn('This browser does not support notifications');
                return;
            }

            // Check if this is the first time the user is visiting (empty session storage)
            const hasVisitedBefore = sessionStorage.getItem('hasVisitedBefore');

            if (!hasVisitedBefore && Notification.permission === 'default') {
                // Show notification permission modal for first-time users
                this.showNotificationPermissionModal();
            } else if (Notification.permission === 'granted') {
                // User already granted permission, set up notifications
                this.setupNotificationPreferences();
            }

        } catch (error) {
            console.error('Error initializing push notifications:', error);
        }
    }

    // Show notification permission modal
    showNotificationPermissionModal() {
        const modal = document.getElementById('notificationPermissionModal');
        if (modal) {
            modal.style.display = 'flex';

            // Handle enable button
            const enableBtn = document.getElementById('notificationEnableBtn');
            const skipBtn = document.getElementById('notificationSkipBtn');

            if (enableBtn) {
                enableBtn.addEventListener('click', async () => {
                    try {
                        const permission = await Notification.requestPermission();
                        if (permission === 'granted') {
                            this.setupNotificationPreferences();
                            this.showToast('Notifications enabled!', 'success');
                        } else {
                            this.showToast('Notification permission denied', 'warning');
                        }
                    } catch (error) {
                        console.error('Error requesting notification permission:', error);
                        this.showToast('Failed to enable notifications', 'error');
                    }
                    this.hideNotificationPermissionModal();
                });
            }

            if (skipBtn) {
                skipBtn.addEventListener('click', () => {
                    this.hideNotificationPermissionModal();
                });
            }
        }
    }

    // Hide notification permission modal
    hideNotificationPermissionModal() {
        const modal = document.getElementById('notificationPermissionModal');
        if (modal) {
            modal.style.display = 'none';
        }

        // Mark that user has visited before
        sessionStorage.setItem('hasVisitedBefore', 'true');
    }

    // Set up notification preferences
    setupNotificationPreferences() {
        const preferences = {
            enabled: true,
            task_completed: true,
            task_failed: true,
            task_cancelled: true
        };

        // Note: Push notification config requires a task ID
        // For now, we'll just log the preferences
        console.log('Push notification preferences:', preferences);
        console.log('Push notifications initialized');
    }

    // Show notification for task updates
    showTaskNotification(task, type = 'info') {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }

        const title = `Task ${type.charAt(0).toUpperCase() + type.slice(1)}`;
        const body = `Task ${task.task_id}: ${task.status?.message || 'Status updated'}`;

        const notification = new Notification(title, {
            body: body,
            icon: '/favicon.ico',
            tag: `task-${task.task_id}`
        });

        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
    }

    // Cancel all running tasks
    async cancelAllRunningTasks() {
        try {
            const activeTasks = Array.from(this.activeTaskSubscriptions.values());
            
            if (activeTasks.length === 0) {
                this.showToast('No active tasks to cancel', 'info');
                return;
            }

            // Confirm before cancelling all
            if (!confirm(`Are you sure you want to cancel all ${activeTasks.length} running task(s)?`)) {
                return;
            }

            this.showToast(`Cancelling ${activeTasks.length} task(s)...`, 'info');
            
            let cancelledCount = 0;
            let failedCount = 0;

            // Cancel each active task
            for (const record of activeTasks) {
                try {
                    await this.cancelTask(record.taskId);
                    
                    // Remove from active subscriptions
                    this.activeTaskSubscriptions.delete(record.taskId);
                    cancelledCount++;
                } catch (error) {
                    console.error(`Failed to cancel task ${record.taskId}:`, error);
                    failedCount++;
                }
            }

            // Save updated subscriptions
            this.saveActiveTaskSubscriptions();

            // Show result
            if (failedCount === 0) {
                this.showToast(`Successfully cancelled ${cancelledCount} task(s)`, 'success');
            } else {
                this.showToast(`Cancelled ${cancelledCount} task(s), ${failedCount} failed`, 'warning');
            }
        } catch (error) {
            console.error('Error canceling all tasks:', error);
            this.showToast('Failed to cancel all tasks', 'error');
        }
    }

    // Refresh all task status
    async refreshAllTaskStatus() {
        try {
            this.showToast('Refreshing task status...', 'info');
            // This would need to be implemented based on your task tracking
            // For now, we'll show a placeholder
            setTimeout(() => {
                this.showToast('Task status refreshed', 'success');
            }, 1000);
        } catch (error) {
            console.error('Error refreshing task status:', error);
            this.showToast('Failed to refresh task status', 'error');
        }
    }

    // Toggle notifications
    async toggleNotifications(enabled) {
        try {
            if (enabled) {
                // Check if browser supports notifications
                if (!('Notification' in window)) {
                    this.showToast('This browser does not support notifications', 'warning');
                    document.getElementById('notificationsEnabled').checked = false;
                    return;
                }

                // Request permission if not already granted
                if (Notification.permission === 'default') {
                    const permission = await Notification.requestPermission();
                    if (permission !== 'granted') {
                        this.showToast('Notification permission denied', 'warning');
                        document.getElementById('notificationsEnabled').checked = false;
                        return;
                    }
                } else if (Notification.permission === 'denied') {
                    this.showToast('Notifications are blocked. Please enable them in your browser settings.', 'warning');
                    document.getElementById('notificationsEnabled').checked = false;
                    return;
                }

                this.showToast('Notifications enabled!', 'success');
            } else {
                this.showToast('Notifications disabled', 'info');
            }

            // Save preferences
            const preferences = {
                enabled: enabled,
                task_completed: document.getElementById('taskCompletedNotifications').checked,
                task_failed: document.getElementById('taskFailedNotifications').checked,
                task_cancelled: true
            };

            localStorage.setItem('notificationsEnabled', enabled);
            console.log('Push notification preferences:', preferences);
        } catch (error) {
            console.error('Error toggling notifications:', error);
            this.showToast('Failed to update notification settings', 'error');
            document.getElementById('notificationsEnabled').checked = !enabled; // Revert checkbox
        }
    }

    // Update notification preferences
    async updateNotificationPreferences() {
        try {
            const enabled = document.getElementById('notificationsEnabled').checked;
            const taskCompleted = document.getElementById('taskCompletedNotifications').checked;
            const taskFailed = document.getElementById('taskFailedNotifications').checked;

            const preferences = {
                enabled: enabled,
                task_completed: taskCompleted,
                task_failed: taskFailed,
                task_cancelled: true
            };

            // Save to localStorage
            localStorage.setItem('notificationsEnabled', enabled);
            localStorage.setItem('taskCompletedNotifications', taskCompleted);
            localStorage.setItem('taskFailedNotifications', taskFailed);

            console.log('Push notification preferences updated:', preferences);
        } catch (error) {
            console.error('Error updating notification preferences:', error);
        }
    }

    // Load and display agent card
    async loadAgentCard() {
        try {
            this.showToast('Loading agent card...', 'info');
            const response = await this.getAgentCard();
            const agentCard = response.result || response;

            // You could also display this in a modal or dedicated section
            this.displayAgentCard(agentCard);
        } catch (error) {
            console.error('Error loading agent card:', error);
            this.showToast('Failed to load agent card', 'error');
        }
    }

    // Display agent card information
    displayAgentCard(agentCard) {
        const section = document.getElementById('agentCardSection');
        const content = document.getElementById('agentCardContent');

        // Create a structured display of the agent card
        const cardHTML = `
            <div class="agent-info-section">
                <div class="agent-info-item">
                    <i class="fas fa-robot info-icon"></i>
                    <div class="info-content">
                        <div class="info-label">Agent Name</div>
                        <div class="info-value">${agentCard.name || 'N/A'}</div>
                    </div>
                </div>
                
                <div class="agent-info-item">
                    <i class="fas fa-info-circle info-icon"></i>
                    <div class="info-content">
                        <div class="info-label">Description</div>
                        <div class="info-value">${agentCard.description || 'N/A'}</div>
                    </div>
                </div>
                
                <div class="agent-info-item">
                    <i class="fas fa-tag info-icon"></i>
                    <div class="info-content">
                        <div class="info-label">Version</div>
                        <div class="info-value">${agentCard.version || 'N/A'}</div>
                    </div>
                </div>
                
                <div class="agent-info-item">
                    <i class="fas fa-cogs info-icon"></i>
                    <div class="info-content">
                        <div class="info-label">Capabilities</div>
                        <div class="info-value">
                            ${agentCard.capabilities && agentCard.capabilities.length > 0
                ? `<div class="capabilities-list">
                                    ${agentCard.capabilities.map(cap => `<span class="capability-tag">${cap}</span>`).join('')}
                                   </div>`
                : 'N/A'
            }
                        </div>
                    </div>
                </div>
            </div>
        `;

        content.innerHTML = cardHTML;
        section.style.display = 'block';

        // Show success message
        this.showToast('Agent card loaded successfully', 'success');
    }

    async sendMessage() {
        // Check if agent is online before allowing message sending
        const statusDot = document.querySelector('.agent-indicator .status-dot');
        const isAgentOnline = statusDot && statusDot.classList.contains('online');

        if (!isAgentOnline) {
            this.showToast('Cannot send message - agent is offline', 'error');
            return;
        }

        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();

        if (!content && this.attachments.length === 0) return;

        console.log('=== SENDING MESSAGE ===');
        console.log('Current sessionId before sending:', this.sessionId);
        console.log('🚀 SENDMESSAGE CALLED - This should appear for every message sent');

        // Ensure we have a session before adding messages
        if (!this.sessionId) {
            console.log('No sessionId found, creating new chat');
            this.createNewChat();
        } else {
            console.log('Using existing sessionId:', this.sessionId);
        }

        const activeInputTaskId = this.activeInputContext?.taskId || null;
        const targetSessionId = this.activeInputContext?.sessionId || this.sessionId;
        const contextIdForMessage = this.activeInputContext?.contextId || this.sessionId;

        // Save a copy of attachments before clearing (needed for both chat display and message sending)
        let attachmentsCopy = [...this.attachments];

        // Add user message to chat
        this.addMessageToChat({
            id: this.generateMessageId(),
            type: 'user',
            content: content,
            attachments: [...attachmentsCopy], // Create another copy for chat message
            timestamp: new Date().toISOString(),
            taskId: activeInputTaskId || undefined
        }, true, targetSessionId);

        // Clear input and attachments preview immediately (after copying to message)
        messageInput.value = '';
        messageInput.style.height = 'auto';
        document.getElementById('sendBtn').disabled = true;
        
        // Clear attachments from input preview (chat message already has its own copy)
        this.clearAttachments();

        // Hide welcome message if visible
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }

        // Show typing indicator for current session
        this.showTypingIndicator(targetSessionId);

        // Send via JSON-RPC streaming using A2A's message/stream method
        try {
            // Build message parts (text + any attached files)
        const parts = [{
            kind: 'text',
            text: content
        }];
        const artifactRefsAdded = [];

            // Add attached files as DataPart with artifact references (A2A compliant)
            // Use the saved copy since this.attachments was cleared for UI
            for (const attachment of attachmentsCopy) {
                if (attachment.uploaded && attachment.filename) {
                const artifactRef = {
                    app: "agent-platform",
                    user: this.userId,
                    session: contextIdForMessage,
                    filename: attachment.filename,
                    mime: attachment.type || 'application/octet-stream'
                };
                parts.push({
                    kind: 'data',
                    data: {
                        artifactRef
                    }
                });
                artifactRefsAdded.push(artifactRef);
                } else if (!attachment.uploaded) {
                    // Skip files that haven't finished uploading
                    this.showToast(`File "${attachment.name}" is still uploading. Please wait.`, 'warning');
                    return;
                }
            }
            
        if (artifactRefsAdded.length > 0) {
            this.registerSessionArtifacts(contextIdForMessage, artifactRefsAdded);
        }

        const hasArtifactParts = parts.some(
            part => part.kind === 'data' && part.data && part.data.artifactRef
        );

        if (!hasArtifactParts) {
            const storedArtifactRefs = this.getStoredArtifactsForSession(contextIdForMessage);
            storedArtifactRefs.forEach(ref => {
                parts.push({
                    kind: 'data',
                    data: {
                        artifactRef: { ...ref }
                    }
                });
            });
        }

            // Clear attachmentsCopy after using it to build message parts
            attachmentsCopy = [];

            // Build message object - always create new task for each message
            const messageObj = {
                message_id: this.generateMessageId(),
                role: 'user',
                parts: parts,
                context_id: contextIdForMessage
            };

            if (activeInputTaskId) {
                messageObj.task_id = activeInputTaskId;
            }

            // Capture sessionId at time of sending to prevent cross-contamination
            const sendingSessionId = contextIdForMessage;
            console.log('Captured sessionId for this message:', sendingSessionId);

            await this.streamJsonRpcRequest({
                method: 'message/stream',
                params: {
                    message: messageObj,
                    context: {
                        session_id: sendingSessionId,
                        user_id: this.userId
                    }
                },
                sessionId: sendingSessionId
            });

            // Ensure attachments are cleared after the stream is established (cleanup)
            this.clearAttachments();

            if (activeInputTaskId) {
                this.markInputRequestResponded(activeInputTaskId);
            }
        } catch (error) {
            console.error('Error sending message:', error);

            // streamJsonRpcRequest already shows toast for JSON-RPC errors
            // Only show toast for network/connection errors
            if (error.message && error.message.includes('HTTP error!')) {
                this.showToast('Failed to send message', 'error');
            }

            // Clear attachments even on error (message was attempted to be sent)
            this.clearAttachments();

            // Remove session from processing set on error
            if (this.processingSessions.has(sendingSessionId)) {
                this.processingSessions.delete(sendingSessionId);
            }
            this.hideTypingIndicator(sendingSessionId);
        }
    }






    handleAgentResponse(data, capturedSessionId = null) {
        console.log('Raw A2A response:', data);

        // Check for JSON-RPC errors first
        if (data.jsonrpc === "2.0" && data.error) {
            const errorMessage = this.getJSONRPCErrorMessage(data.error);
            this.showToast(errorMessage, 'error');
            this.addMessageToChat({
                id: data.id || this.generateMessageId(),
                type: 'agent',
                content: `❌ **Error**: ${errorMessage}`,
                timestamp: new Date().toISOString(),
                agent: this.currentAgentName
            }, true, capturedSessionId);
            if (capturedSessionId) {
                this.updateTypingIndicatorForSession(capturedSessionId, false);
            }
            return;
        }

        // Handle A2A protocol response format according to specification
        if (data.jsonrpc === "2.0" && data.result) {
            const result = data.result;

            // Check if this is a task response
            if (result.kind === "status-update") {
                this.handleStatusUpdate(result, capturedSessionId);
                return;
            }

            // Handle artifact-update events (streaming artifact content)
            if (result.kind === "artifact-update") {
                this.handleArtifactUpdate(result, capturedSessionId);
                return;
            }

            if (result.kind === "task" && result.status) {
                const task = result;
                const taskId = task.id;
                const taskStatus = task.status;

                console.log('Task ID:', taskId);
                console.log('Task Status:', taskStatus);
                console.log('Task Artifacts:', result.artifacts);
                console.log('Task History:', result.history);

                // Store task ID for session tracking
                if (taskId) {
                    console.log('Task ID from A2A response:', taskId);

                    // Store task_id for later use in session management
                    this.lastTaskId = taskId;

                    // Associate this task ID with the correct session (using capturedSessionId to prevent race conditions)
                    this.saveMessageToSession(null, taskId, capturedSessionId);
                }

                // Check if we have artifacts to avoid duplicate messages
                console.log('🔍 Checking for artifacts. result.artifacts:', result.artifacts);
                const hasArtifacts = result.artifacts && Array.isArray(result.artifacts) && result.artifacts.length > 0;
                console.log('🔍 hasArtifacts:', hasArtifacts, 'count:', hasArtifacts ? result.artifacts.length : 0);

                // Handle different task states
                if (taskStatus.state === "completed") {
                    console.log('📋 Task state: completed, hasArtifacts:', hasArtifacts);
                    // Only call handler if no artifacts (to avoid duplicate messages)
                    if (!hasArtifacts) {
                        console.log('⚠️ Calling handleTaskComplete (no artifacts)');
                        this.handleTaskComplete(task, capturedSessionId);
                    } else {
                        console.log('✅ Skipping handleTaskComplete (has artifacts)');
                    }
                    this.updateTypingIndicatorForSession(capturedSessionId, false);
                } else if (taskStatus.state === "failed") {
                    this.handleTaskFailed(task, capturedSessionId);
                    this.updateTypingIndicatorForSession(capturedSessionId, false);
                } else if (taskStatus.state === "running") {
                    // Only call handler if no artifacts (to avoid duplicate messages)
                    if (!hasArtifacts) {
                        this.handleTaskRunning(task, capturedSessionId);
                    }
                    this.updateTypingIndicatorForSession(capturedSessionId, true);
                } else if (taskStatus.state === "waiting") {
                    // Only call handler if no artifacts (to avoid duplicate messages)
                    if (!hasArtifacts) {
                        this.handleTaskWaiting(task, capturedSessionId);
                    }
                    this.updateTypingIndicatorForSession(capturedSessionId, true);
                } else if (taskStatus.state === "input-required") {
                    this.handleTaskInputRequired(task, capturedSessionId);
                }

                // Handle artifacts (the actual response content)
                if (hasArtifacts) {
                    console.log(`Processing ${result.artifacts.length} artifacts for task ${taskId}`);
                    // Get or create the set of processed artifacts for this task
                    if (!this.processedTaskArtifacts.has(taskId)) {
                        this.processedTaskArtifacts.set(taskId, new Set());
                        console.log(`Created new artifact tracking set for task ${taskId}`);
                    }
                    const processedArtifacts = this.processedTaskArtifacts.get(taskId);
                    console.log(`Current processed artifacts count for task ${taskId}:`, processedArtifacts.size);
                    
                    result.artifacts.forEach(artifact => {
                        console.log('Processing artifact:', artifact.artifactId);
                        // Skip if this artifact has already been displayed (by artifactId)
                        if (artifact.artifactId && this.displayedArtifactIds.has(artifact.artifactId)) {
                            console.log('Skipping artifact with ID already displayed:', artifact.artifactId);
                            return;
                        }
                        
                        // For artifacts without IDs, use content-based deduplication
                        if (artifact.parts && Array.isArray(artifact.parts)) {
                            artifact.parts.forEach(part => {
                                if (part.kind === "text" && part.text) {
                                    // Create a hash of the FULL content to detect duplicates (not just first 100 chars)
                                    const contentHash = `${taskId}:text:${part.text}`;
                                    console.log(`Checking content hash (first 50 chars): ${contentHash.substring(0, 50)}...`);
                                    
                                    // Skip if we've already processed this exact content for this task
                                    if (processedArtifacts.has(contentHash)) {
                                        console.log('✅ Skipping duplicate artifact content for task', taskId);
                                        return;
                                    }
                                    console.log('➕ Adding new content hash to processed set');
                                    processedArtifacts.add(contentHash);
                                    
                                    this.addMessageToChat({
                                        id: artifact.artifactId || this.generateMessageId(),
                                        type: 'agent',
                                        content: part.text,
                                        timestamp: taskStatus.timestamp || new Date().toISOString(),
                                        agent: this.currentAgentName,
                                        taskId: taskId
                                    }, true, capturedSessionId);
                                } else if (part.kind === "data" && part.data) {
                                    // Check if this is artifactRef - handle as attachment
                                    if (part.data.artifactRef) {
                                        const artifactRef = part.data.artifactRef;
                                        this.addMessageToChat({
                                            id: artifact.artifactId || this.generateMessageId(),
                                            type: 'agent',
                                            content: '', // No text content for artifact-only messages
                                            attachments: [{
                                                name: artifactRef.filename || 'Attachment',
                                                filename: artifactRef.filename,
                                                type: artifactRef.mime || 'application/octet-stream',
                                                uploaded: true
                                            }],
                                            timestamp: taskStatus.timestamp || new Date().toISOString(),
                                            agent: this.currentAgentName,
                                            taskId: taskId
                                        }, true, capturedSessionId);
                                    } else if (this.isToolCallData(part.data)) {
                                        // Handle tool call data - format as JSON string for detection
                                        const toolCallContent = JSON.stringify(part.data);
                                        this.addMessageToChat({
                                            id: part.data.id || artifact.artifactId || this.generateMessageId(),
                                            type: 'agent',
                                            content: toolCallContent,
                                            timestamp: taskStatus.timestamp || new Date().toISOString(),
                                            agent: this.currentAgentName,
                                            taskId: taskId
                                        }, true, capturedSessionId);
                                    }
                                }
                            });
                        }
                    });
                }

                // Don't process history messages if we already have artifacts
                // The artifacts contain the actual response content

                // Update task status
                this.updateTaskStatus(taskId, taskStatus);

            } else if (result.history && Array.isArray(result.history)) {
                // Handle history-based response (fallback)
                console.log('📜 Using history-based response fallback, history length:', result.history.length);
                const latestMessage = result.history[result.history.length - 1];
                if (capturedSessionId) {
                    this.updateTypingIndicatorForSession(capturedSessionId, false);
                }
                if (latestMessage && latestMessage.kind === "message") {
                    // Extract artifactRef attachments
                    const attachments = this.extractArtifactRefs(latestMessage);
                    this.addMessageToChat({
                        id: latestMessage.messageId || this.generateMessageId(),
                        type: latestMessage.role === 'user' ? 'user' : 'agent',
                        content: this.formatA2AMessage(latestMessage),
                        attachments: attachments.length > 0 ? attachments : undefined,
                        timestamp: new Date().toISOString(),
                        agent: latestMessage.role === 'agent' ? this.currentAgentName : null
                    }, true, capturedSessionId);
                }
            }
        } else {
            // Fallback for non-standard responses
            console.warn('Non-standard A2A response format:', data);
            this.showToast('Received unexpected response format', 'warning');
            this.addMessageToChat({
                id: data.id || this.generateMessageId(),
                type: 'agent',
                content: '⚠️ **Warning**: Received unexpected response format. Check console for details.',
                timestamp: new Date().toISOString(),
                agent: this.currentAgentName
            }, true, capturedSessionId);
            if (capturedSessionId) {
                this.updateTypingIndicatorForSession(capturedSessionId, false);
            }
        }
    }

    // Format A2A message according to protocol specification
    formatA2AMessage(message) {
        if (!message || !message.parts) {
            return 'No message content';
        }

        let content = '';
        message.parts.forEach(part => {
            if (part.kind === 'text') {
                content += part.text;
            } else if (part.kind === 'artifact') {
                content += `\n📎 Artifact: ${part.artifact?.filename || 'Unknown file'}`;
            } else if (part.kind === 'data') {
                // Check if this is a tool call - if so, format it as JSON for detection
                if (this.isToolCallData(part.data)) {
                    // Return just the JSON so extractToolCallFromContent can detect it
                    content += JSON.stringify(part.data);
                } else if (part.data && part.data.artifactRef) {
                    // artifactRef will be handled as attachment, don't add to content
                    // This will be extracted separately
                } else {
                    content += `\n📊 Data: ${JSON.stringify(part.data, null, 2)}`;
                }
            }
        });

        return content || '';
    }

    // Extract artifactRef attachments from A2A message
    extractArtifactRefs(message) {
        if (!message || !message.parts) {
            return [];
        }

        const attachments = [];
        message.parts.forEach(part => {
            if (part.kind === 'data' && part.data && part.data.artifactRef) {
                const artifactRef = part.data.artifactRef;
                attachments.push({
                    name: artifactRef.filename || 'Attachment',
                    filename: artifactRef.filename,
                    type: artifactRef.mime || 'application/octet-stream',
                    uploaded: true // Already uploaded since it's a reference
                });
            }
        });

        return attachments;
    }

    registerSessionArtifacts(sessionId, artifacts) {
        if (!sessionId || !artifacts || artifacts.length === 0) {
            return;
        }
        const existing = this.sessionArtifactRefs.get(sessionId) || [];
        const existingKeys = new Set(existing.map(ref => this.getArtifactKey(ref)));
        let updated = false;

        artifacts.forEach(ref => {
            const key = this.getArtifactKey(ref);
            if (!existingKeys.has(key)) {
                existing.push({ ...ref });
                existingKeys.add(key);
                updated = true;
            }
        });

        if (updated || !this.sessionArtifactRefs.has(sessionId)) {
            this.sessionArtifactRefs.set(sessionId, existing);
        }
    }

    getStoredArtifactsForSession(sessionId) {
        if (!sessionId) {
            return [];
        }
        return this.sessionArtifactRefs.get(sessionId) || [];
    }

    clearSessionArtifacts(sessionId) {
        if (!sessionId) {
            return;
        }
        this.sessionArtifactRefs.delete(sessionId);
    }

    getArtifactKey(ref) {
        if (!ref) {
            return '';
        }
        const app = ref.app || '';
        const user = ref.user || '';
        const session = ref.session || '';
        const filename = ref.filename || '';
        return `${app}:${user}:${session}:${filename}`;
    }

    // Check if data object represents a tool call
    isToolCallData(data) {
        if (!data || typeof data !== 'object') return false;
        // Tool calls have 'name' and 'args' fields, or 'id' and 'name' fields
        return (data.name && (data.args !== undefined || data.id !== undefined)) ||
               (data.id && data.name);
    }

    // Handle task completion
    handleTaskComplete(task, sessionId = null) {
        console.log('Task completed:', task);
        this.showToast(`Task ${task.id} completed successfully!`, 'success');

        this.resolveInputRequest(task.id);

        // Add completion message to chat if there's a status message
        if (task.status && task.status.message) {
            const attachments = this.extractArtifactRefs(task.status.message);
            this.addMessageToChat({
                id: task.status.message.messageId || this.generateMessageId(),
                type: 'agent',
                content: `✅ **Task Completed**\n\n${this.formatA2AMessage(task.status.message)}`,
                attachments: attachments.length > 0 ? attachments : undefined,
                timestamp: task.status.timestamp || new Date().toISOString(),
                agent: this.currentAgentName,
                taskId: task.id
            }, true, sessionId);
        }
    }

    // Handle task failure
    handleTaskFailed(task, sessionId = null) {
        console.log('Task failed:', task);
        this.showToast(`Task ${task.id} failed`, 'error');

        this.resolveInputRequest(task.id);

        // Add error message to chat
        if (task.status.message) {
            const attachments = this.extractArtifactRefs(task.status.message);
            this.addMessageToChat({
                id: task.status.message.messageId || this.generateMessageId(),
                type: 'agent',
                content: `❌ **Task Failed**\n\n${this.formatA2AMessage(task.status.message)}`,
                attachments: attachments.length > 0 ? attachments : undefined,
                timestamp: task.status.timestamp || new Date().toISOString(),
                agent: this.currentAgentName,
                taskId: task.id
            }, true, sessionId);
        }
    }

    // Handle task running
    handleTaskRunning(task, sessionId = null) {
        console.log('Task running:', task);
        this.showToast(`Task ${task.id} is running...`, 'info');

        this.resolveInputRequest(task.id);

        // Add running status message to chat if there's a status message
        if (task.status && task.status.message) {
            this.updateToolCallStatusFromMessage(task.status.message, 'running');
            const attachments = this.extractArtifactRefs(task.status.message);
            this.addMessageToChat({
                id: task.status.message.messageId || this.generateMessageId(),
                type: 'agent',
                content: `🔄 **Task Running**\n\n${this.formatA2AMessage(task.status.message)}`,
                attachments: attachments.length > 0 ? attachments : undefined,
                timestamp: task.status.timestamp || new Date().toISOString(),
                agent: this.currentAgentName,
                taskId: task.id
            }, true, sessionId);
        }
    }

    // Handle task waiting
    handleTaskWaiting(task, sessionId = null) {
        console.log('Task waiting:', task);
        this.showToast(`Task ${task.id} is waiting...`, 'info');

        this.resolveInputRequest(task.id);

        // Add waiting status message to chat if there's a status message
        if (task.status && task.status.message) {
            this.updateToolCallStatusFromMessage(task.status.message, 'waiting');
            const attachments = this.extractArtifactRefs(task.status.message);
            this.addMessageToChat({
                id: task.status.message.messageId || this.generateMessageId(),
                type: 'agent',
                content: `⏳ **Task Waiting**\n\n${this.formatA2AMessage(task.status.message)}`,
                attachments: attachments.length > 0 ? attachments : undefined,
                timestamp: task.status.timestamp || new Date().toISOString(),
                agent: this.currentAgentName,
                taskId: task.id
            }, true, sessionId);
        }
    }

    handleTaskInputRequired(task, sessionId = null) {
        if (!task || !task.id) {
            console.warn('Input-required event missing task info:', task);
            return;
        }

        const taskId = task.id;
        const status = task.status || {};
        this.updateToolCallStatusFromMessage(status.message, 'input-required');
        const targetSessionId = sessionId || status.contextId || this.sessionId;
        const attachments = this.extractArtifactRefs(status.message);
        const formattedContent = status.message
            ? this.formatA2AMessage(status.message)
            : 'The agent needs additional information to continue.';
        const timestamp = status.timestamp || new Date().toISOString();
        const messageId = status.message?.messageId || null;
        const existing = this.pendingInputRequests.get(taskId);

        if (existing && messageId && existing.messageId === messageId) {
            if (targetSessionId === this.sessionId) {
                this.setActiveInputRequest(taskId);
            }
            if (task.status) {
                this.updateTaskStatus(taskId, status);
            }
            this.updateTypingIndicatorForSession(targetSessionId, false);
            return;
        }

        const requestEntry = {
            taskId,
            sessionId: targetSessionId,
            contextId: targetSessionId,
            prompt: formattedContent,
            timestamp,
            messageId
        };

        this.pendingInputRequests.set(taskId, requestEntry);

        this.addMessageToChat({
            id: messageId || this.generateMessageId(),
            type: 'agent',
            content: `⚠️ **Input Required**\n\n${formattedContent}`,
            attachments: attachments.length > 0 ? attachments : undefined,
            timestamp,
            agent: this.currentAgentName,
            taskId: taskId,
            inputRequiredTaskId: taskId,
            inputRequiredContextId: targetSessionId,
            inputRequiredPrompt: formattedContent
        }, true, targetSessionId);

        this.showToast(`Task ${this.formatTaskId(taskId)} needs more info`, 'warning');

        if (task.status) {
            this.updateTaskStatus(taskId, status);
        }

        if (targetSessionId === this.sessionId) {
            this.setActiveInputRequest(taskId);
        }

        this.updateTypingIndicatorForSession(targetSessionId, false);
    }

    setActiveInputRequest(taskId, fallbackContextId = null, fallbackPrompt = null) {
        if (!taskId) {
            return;
        }

        let request = this.pendingInputRequests.get(taskId);
        if (!request && fallbackContextId) {
            request = {
                taskId,
                sessionId: fallbackContextId,
                contextId: fallbackContextId,
                prompt: fallbackPrompt || 'Provide the requested information for this task.',
                timestamp: new Date().toISOString()
            };
            this.pendingInputRequests.set(taskId, request);
        }

        if (!request) {
            this.showToast('This task is no longer waiting for input.', 'warning');
            return;
        }

        if (request.sessionId && this.sessionId && request.sessionId !== this.sessionId) {
            this.showToast('Switch to the original session to respond to this task.', 'warning');
            return;
        }

        this.activeInputContext = request;
        this.showInputContextBanner(request);
    }

    showInputContextBanner(request) {
        if (!request) {
            return;
        }

        if (this.inputContextBanner) {
            this.inputContextBanner.style.display = 'flex';
            this.inputContextBanner.setAttribute('data-task-id', request.taskId);
        }

        if (this.inputContextDetails) {
            const preview = this.truncateText(request.prompt || '', 140);
            const taskLabel = this.formatTaskId(request.taskId);
            this.inputContextDetails.textContent = taskLabel
                ? `Task ${taskLabel} • ${preview}`
                : preview;
        }

        const messageInput = document.getElementById('messageInput');
        if (messageInput && !messageInput.disabled) {
            messageInput.placeholder = this.getInputContextPlaceholder(request);
        }
    }

    clearActiveInputContext() {
        this.activeInputContext = null;

        if (this.inputContextBanner) {
            this.inputContextBanner.style.display = 'none';
            this.inputContextBanner.removeAttribute('data-task-id');
        }

        if (this.inputContextDetails) {
            this.inputContextDetails.textContent = '';
        }

        const messageInput = document.getElementById('messageInput');
        if (messageInput && !messageInput.disabled) {
            messageInput.placeholder = this.defaultInputPlaceholder;
        }
    }

    getInputContextPlaceholder(request) {
        if (!request) {
            return this.defaultInputPlaceholder;
        }
        const taskLabel = this.formatTaskId(request.taskId);
        return taskLabel
            ? `Provide additional input for task ${taskLabel}...`
            : 'Provide the requested input...';
    }

    markInputRequestResponded(taskId) {
        if (!taskId) {
            this.clearActiveInputContext();
            return;
        }
        const request = this.pendingInputRequests.get(taskId);
        if (request) {
            request.lastResponseAt = new Date().toISOString();
        }
        if (this.activeInputContext && this.activeInputContext.taskId === taskId) {
            this.clearActiveInputContext();
        }
    }

    resolveInputRequest(taskId) {
        if (!taskId) {
            return;
        }
        if (this.pendingInputRequests.has(taskId)) {
            this.pendingInputRequests.delete(taskId);
        }
        if (this.activeInputContext && this.activeInputContext.taskId === taskId) {
            this.clearActiveInputContext();
        }
    }

    removeInputRequestsForSession(sessionId) {
        if (!sessionId) {
            return;
        }
        let removed = false;
        for (const [taskId, request] of Array.from(this.pendingInputRequests.entries())) {
            if (request.sessionId === sessionId) {
                this.pendingInputRequests.delete(taskId);
                removed = true;
            }
        }
        if (removed && this.activeInputContext && this.activeInputContext.sessionId === sessionId) {
            this.clearActiveInputContext();
        }
    }

    restoreInputContextForSession(sessionId) {
        if (!sessionId) {
            this.clearActiveInputContext();
            return;
        }
        for (const request of this.pendingInputRequests.values()) {
            if (request.sessionId === sessionId) {
                this.activeInputContext = request;
                this.showInputContextBanner(request);
                return;
            }
        }
        this.clearActiveInputContext();
    }

    truncateText(text, maxLength = 140) {
        if (!text) {
            return '';
        }
        if (text.length <= maxLength) {
            return text;
        }
        return `${text.slice(0, maxLength - 3)}...`;
    }

    handleStatusUpdate(statusUpdate, sessionId = null) {
        if (!statusUpdate || !statusUpdate.status) {
            console.warn('Status update payload missing status object:', statusUpdate);
            return;
        }

        const statusPayload = statusUpdate.status;
        const normalizedState = (statusPayload.state || '').toLowerCase();
        const awaitingLongRunningTool =
            normalizedState === 'input-required' &&
            this.isAwaitingLongRunningTool(statusPayload);
        const displayStatusPayload = awaitingLongRunningTool
            ? {
                ...statusPayload,
                state: 'working'
            }
            : statusPayload;
        const displayStatusUpdate = awaitingLongRunningTool
            ? { ...statusUpdate, status: displayStatusPayload }
            : statusUpdate;
        // Use displayState for toast type to maintain consistency with displayed UI state
        const displayState = (displayStatusPayload.state || '').toLowerCase();

        const targetSessionId = sessionId || statusUpdate.contextId || this.sessionId;
        const attachments = this.extractArtifactRefs(displayStatusPayload.message);

        // Update tool call status tracking for all status transitions
        this.updateToolCallStatusFromMessage(statusPayload.message, normalizedState);

        if (normalizedState === 'input-required' && statusUpdate.taskId && !awaitingLongRunningTool) {
            this.handleTaskInputRequired(
                { id: statusUpdate.taskId, status: statusPayload },
                targetSessionId
            );
            return;
        }

        const heading = this.buildStatusUpdateHeading(displayStatusUpdate);
        
        // Show status updates as toast by default (submitted, completed, working, etc.)
        // Only render as card if there's meaningful message content beyond the status
        const messageContent = displayStatusPayload.message
            ? this.formatA2AMessage(displayStatusPayload.message)
            : '';
        const hasSubstantiveContent = messageContent.trim().length > 0 && 
            messageContent.trim() !== 'Status update received.';
        
        // Always show toast for status updates
        // Use displayState for toast type to match the displayed UI state (e.g., 'working' instead of 'input-required' for long-running tools)
        this.showToast(heading || 'Status update received.', this.getToastTypeForState(displayState));
        
        // Don't add messages from status-update if there's a taskId
        // Those messages will be delivered via artifact-update events to avoid duplicates
        const shouldSkipMessageFromStatus = statusUpdate.taskId && hasSubstantiveContent;
        console.log('🚫 Status-update message check:', {
            taskId: statusUpdate.taskId,
            hasSubstantiveContent,
            shouldSkip: shouldSkipMessageFromStatus,
            messagePreview: messageContent.substring(0, 50)
        });
        
        // Only render card if there's actual content beyond the status heading
        // Show card if there's substantive content OR attachments (not requiring both)
        // BUT: Skip if this is a task with substantive content (will come via artifact-update)
        if ((hasSubstantiveContent || attachments.length > 0) && !shouldSkipMessageFromStatus) {
            this.addMessageToChat({
                id: displayStatusPayload.message?.messageId || this.generateMessageId(),
                type: 'agent',
                content: messageContent || 'Status update received.',
                attachments: attachments.length > 0 ? attachments : undefined,
                timestamp: displayStatusPayload.timestamp || statusUpdate.timestamp || new Date().toISOString(),
                taskId: statusUpdate.taskId || null
            }, true, targetSessionId);
        }

        if (statusUpdate.taskId) {
            // Use displayStatusPayload to preserve the modified state (e.g., 'working' for long-running tools)
            this.updateTaskStatus(statusUpdate.taskId, displayStatusPayload);
        }

        if (typeof statusUpdate.final === 'boolean') {
            this.updateTypingIndicatorForSession(targetSessionId, !statusUpdate.final);
        }

        if (statusUpdate.taskId && normalizedState && normalizedState !== 'input-required') {
            this.resolveInputRequest(statusUpdate.taskId);
        }
    }

    // Handle artifact-update events from A2A streaming
    handleArtifactUpdate(artifactUpdate, sessionId = null) {
        if (!artifactUpdate || !artifactUpdate.artifact) {
            console.warn('Artifact update missing artifact object:', artifactUpdate);
            return;
        }

        const artifact = artifactUpdate.artifact;
        const taskId = artifactUpdate.taskId;
        const targetSessionId = sessionId || artifactUpdate.contextId || this.sessionId;

        // Extract text content from artifact parts
        let textContent = '';
        if (artifact.parts && Array.isArray(artifact.parts)) {
            artifact.parts.forEach(part => {
                if (part.kind === 'text' && part.text) {
                    textContent += part.text;
                }
            });
        }

        // Only add message if there's actual text content and this is the last chunk
        if (textContent && artifactUpdate.lastChunk) {
            // Deduplicate based on content hash
            if (!this.processedTaskArtifacts.has(taskId)) {
                this.processedTaskArtifacts.set(taskId, new Set());
            }
            const processedArtifacts = this.processedTaskArtifacts.get(taskId);
            const contentHash = `${taskId}:artifact:${textContent}`;
            
            console.log('🎨 Artifact-update:', {
                taskId,
                artifactId: artifact.artifactId,
                contentPreview: textContent.substring(0, 50),
                alreadyProcessed: processedArtifacts.has(contentHash)
            });
            
            if (processedArtifacts.has(contentHash)) {
                console.log('⏭️  Skipping duplicate artifact content');
                return;
            }
            
            processedArtifacts.add(contentHash);
            
            this.addMessageToChat({
                id: artifact.artifactId || this.generateMessageId(),
                type: 'agent',
                content: textContent,
                timestamp: new Date().toISOString(),
                agent: this.currentAgentName,
                taskId: taskId
            }, true, targetSessionId);
        }
    }

    buildStatusUpdateHeading(statusUpdate) {
        if (!statusUpdate || !statusUpdate.status) {
            return '';
        }

        const state = statusUpdate.status.state;
        const author = statusUpdate.metadata?.adk_author;
        const formattedAuthor = author ? this.formatAgentName(author) : null;
        const segments = [];

        segments.push(`${this.getStatusStateIcon(state)} Status Update`);

        if (state) {
            const normalizedState = state.charAt(0).toUpperCase() + state.slice(1);
            segments.push(normalizedState);
        }

        if (formattedAuthor) {
            segments.push(`by ${formattedAuthor}`);
        }

        if (statusUpdate.taskId) {
            segments.push(`task ${this.formatTaskId(statusUpdate.taskId)}`);
        }

        return segments.join(' • ');
    }

    parseCustomMetadataValue(customMetadata) {
        if (customMetadata === undefined || customMetadata === null) {
            return null;
        }

        if (typeof customMetadata === 'object') {
            return customMetadata;
        }

        if (typeof customMetadata === 'string') {
            return this.tryParseJsonLike(customMetadata);
        }

        return null;
    }

    formatStatusMetadata(metadata) {
        if (!metadata || typeof metadata !== 'object') {
            return '';
        }

        const sections = [];
        const customMetadata = this.stringifyCustomMetadata(metadata.adk_custom_metadata);

        if (customMetadata) {
            sections.push(`Custom Metadata:\n${customMetadata}`);
        }

        return sections.join('\n\n').trim();
    }

    getStatusToastInstruction(customMetadata, statusPayload, normalizedState, heading) {
        if (!customMetadata || typeof customMetadata !== 'object') {
            return null;
        }

        const toBool = (value) => {
            if (typeof value === 'boolean') {
                return value;
            }
            if (typeof value === 'string') {
                const normalized = value.trim().toLowerCase();
                if (normalized === 'true') {
                    return true;
                }
                if (normalized === 'false') {
                    return false;
                }
            }
            return undefined;
        };

        const displayHint = (customMetadata.display || customMetadata.displayMode || customMetadata.renderAs || '').toLowerCase();
        const toastMessageCandidate = [
            customMetadata.toastMessage,
            customMetadata.toast_message,
            customMetadata.message
        ].find(value => typeof value === 'string' && value.trim().length > 0);

        const explicitToastMessage = typeof customMetadata.toastMessage === 'string' && customMetadata.toastMessage.trim().length > 0;
        const alternateToastMessage = typeof customMetadata.toast_message === 'string' && customMetadata.toast_message.trim().length > 0;

        const showAsToastFlag = toBool(customMetadata.showAsToast);
        const toastOnlyFlag = toBool(customMetadata.toastOnly);

        const shouldShowToast =
            showAsToastFlag === true ||
            toastOnlyFlag === true ||
            displayHint === 'toast' ||
            explicitToastMessage ||
            alternateToastMessage;

        if (!shouldShowToast) {
            return null;
        }

        const fallbackContent = statusPayload?.message
            ? this.formatA2AMessage(statusPayload.message)
            : '';

        const toastMessage = (toastMessageCandidate || heading || fallbackContent || 'Status update received.').trim();

        if (!toastMessage) {
            return null;
        }

        const toastType =
            customMetadata.toastType ||
            customMetadata.toast_type ||
            customMetadata.toastVariant ||
            customMetadata.level ||
            customMetadata.type ||
            this.getToastTypeForState(normalizedState);

        const skipCard =
            toastOnlyFlag !== false &&
            (toastOnlyFlag === true || showAsToastFlag === true || displayHint === 'toast' || explicitToastMessage || alternateToastMessage);

        return {
            message: toastMessage,
            type: toastType || 'info',
            skipCard
        };
    }

    stringifyCustomMetadata(customMetadata) {
        if (customMetadata === undefined || customMetadata === null) {
            return '';
        }

        if (typeof customMetadata === 'string') {
            const parsed = this.tryParseJsonLike(customMetadata);
            if (parsed) {
                return JSON.stringify(parsed, null, 2);
            }
            return customMetadata;
        }

        if (typeof customMetadata === 'object') {
            return JSON.stringify(customMetadata, null, 2);
        }

        return String(customMetadata);
    }

    tryParseJsonLike(value) {
        if (typeof value !== 'string') {
            return null;
        }

        const trimmed = value.trim();
        if (!trimmed) {
            return null;
        }

        const attemptParse = (input) => {
            try {
                return JSON.parse(input);
            } catch (e) {
                return null;
            }
        };

        let parsed = attemptParse(trimmed);
        if (parsed) {
            return parsed;
        }

        if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
            return null;
        }

        const sanitized = trimmed
            .replace(/<[^:>]+:\s*'([^']*)'>/g, '"$1"')
            .replace(/([{,]\s*)'([^']+?)'\s*:/g, '$1"$2":')
            .replace(/:\s*'([^']*?)'(\s*[},])/g, ': "$1"$2')
            .replace(/\bNone\b/g, 'null')
            .replace(/\bTrue\b/g, 'true')
            .replace(/\bFalse\b/g, 'false');

        return attemptParse(sanitized);
    }

    getToastTypeForState(state) {
        if (!state || typeof state !== 'string') {
            return 'info';
        }

        const normalized = state.toLowerCase();

        if (normalized === 'completed' || normalized === 'success') {
            return 'success';
        }

        if (normalized === 'failed' || normalized === 'error') {
            return 'error';
        }

        if (normalized === 'input-required') {
            return 'warning';
        }

        return 'info';
    }

    formatMetadataLabel(label) {
        if (!label || typeof label !== 'string') {
            return '';
        }

        return label
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (char) => char.toUpperCase());
    }

    isAwaitingLongRunningTool(statusPayload) {
        const parts = statusPayload?.message?.parts;
        if (!Array.isArray(parts) || parts.length === 0) {
            return false;
        }

        return parts.some(part =>
            part.kind === 'data' &&
            part.metadata &&
            part.metadata.adk_is_long_running === true
        );
    }

    getStatusStateIcon(state) {
        if (!state) {
            return '📡';
        }

        const iconMap = {
            completed: '✅',
            success: '✅',
            failed: '❌',
            error: '⚠️',
            waiting: '⏳',
            queued: '⏳',
            running: '🔄',
            working: '🔄',
            planning: '🧠',
            thinking: '🧠',
            'input-required': '✋'
        };

        const key = state.toLowerCase();
        return iconMap[key] || '📡';
    }

    formatAgentResponse(result) {
        let content = '';

        if (result.analysis) {
            content += `**Analysis:**\n`;
            content += `- Task Type: ${result.analysis.task_type || 'General'}\n`;
            content += `- Priority: ${result.analysis.priority || 'Medium'}\n`;
            content += `- Complexity: ${result.analysis.complexity || 'Moderate'}\n\n`;
        }

        if (result.assigned_to) {
            content += `**Assigned to:** ${result.assigned_to}\n\n`;
        }

        if (result.recommendations) {
            content += `**Recommendations:**\n`;
            result.recommendations.forEach(rec => {
                content += `• ${rec}\n`;
            });
            content += '\n';
        }

        if (result.threats) {
            content += `**Security Analysis:**\n`;
            result.threats.forEach(threat => {
                content += `⚠️ ${threat.type}: ${threat.description}\n`;
            });
            content += '\n';
        }

        if (result.configurations) {
            content += `**Generated Configurations:**\n`;
            Object.keys(result.configurations).forEach(key => {
                content += `• ${key} configuration ready\n`;
            });
        }

        return content || 'Task is being processed...';
    }


    addMessageToChat(message, saveToSession = true, sessionId = null) {
        console.log('💬 addMessageToChat called:', {
            type: message.type,
            contentPreview: message.content?.substring(0, 50),
            taskId: message.taskId,
            saveToSession,
            sessionId
        });
        const messagesContainer = document.getElementById('chatMessages');

        // Hide welcome message when first message is added
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (welcomeMessage && welcomeMessage.style.display !== 'none') {
            welcomeMessage.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        const isToolCall = this.extractToolCallFromContent(message.content) !== null;
        messageDiv.className = `message ${message.type}${isToolCall ? ' tool-call-message' : ''}`;

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = `message-avatar${isToolCall ? ' tool-call-avatar' : ''}`;
        if (isToolCall) {
            avatar.innerHTML = '<i class="fas fa-cog"></i>';
        } else {
            avatar.innerHTML = message.type === 'user' ?
                '<i class="fas fa-user"></i>' :
                '<i class="fas fa-robot"></i>';
        }

        // Content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Header
        const header = document.createElement('div');
        header.className = 'message-header';
        header.innerHTML = `
            <span class="message-author">${isToolCall ? 'Tool Call' : (message.type === 'user' ? 'You' : 'Agent')}</span>
            <span class="message-time">${this.formatTime(message.timestamp)}</span>
        `;

        // Bubble
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        // Check if this message contains tool call data
        const toolCallData = this.extractToolCallFromContent(message.content);
        
        if (toolCallData) {
            const toolCallId = toolCallData.id;
            
            // Check if we already have a tool call with this ID
            if (toolCallId && this.toolCallMessages.has(toolCallId)) {
                // Update existing tool call card with response
                const existingCard = this.toolCallMessages.get(toolCallId);
                this.updateToolCallCard(existingCard, toolCallData);
                // Don't create a new message, just update the existing one
                return;
            } else {
                // Create new tool call card
                const toolCallCard = this.createToolCallCard(toolCallData);
                bubble.appendChild(toolCallCard);
                // Store reference to update later if response comes in
                if (toolCallId) {
                    this.toolCallMessages.set(toolCallId, toolCallCard);
                    // Store message div reference for potential removal/update
                    messageDiv.setAttribute('data-tool-call-id', toolCallId);
                }
            }
        } else {
            const text = document.createElement('div');
            text.className = 'message-text';

            // Check if content contains markdown code blocks and process them
            if (this.containsMarkdownCodeBlocks(message.content)) {
                this.formatMarkdownContent(text, message.content);
            } else {
                text.textContent = message.content;
            }

            bubble.appendChild(text);
        }

        // Attachments
        if (message.attachments && message.attachments.length > 0) {
            const attachmentsDiv = document.createElement('div');
            attachmentsDiv.className = 'message-attachments';

            message.attachments.forEach(attachment => {
                const attachmentItem = document.createElement('div');
                attachmentItem.className = 'attachment-item';
                attachmentItem.innerHTML = `
                    <i class="fas fa-file"></i>
                    <span>${attachment.name || 'Attachment'}</span>
                `;
                attachmentsDiv.appendChild(attachmentItem);
            });

            bubble.appendChild(attachmentsDiv);
        }

        if (message.inputRequiredTaskId) {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            const actionBtn = document.createElement('button');
            actionBtn.className = 'message-action-btn';
            actionBtn.innerHTML = '<i class="fas fa-reply"></i><span>Provide Required Input</span>';
            actionBtn.addEventListener('click', () => this.setActiveInputRequest(
                message.inputRequiredTaskId,
                message.inputRequiredContextId || this.sessionId,
                message.inputRequiredPrompt || message.content
            ));
            actionsDiv.appendChild(actionBtn);
            bubble.appendChild(actionsDiv);
        }

        contentDiv.appendChild(header);
        contentDiv.appendChild(bubble);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Save to session with task_id if available (only if saveToSession is true)
        if (saveToSession) {
            // Use passed sessionId or fall back to current sessionId
            const targetSessionId = sessionId || this.sessionId;
            // Only save if we have a valid task ID for this specific message
            // Don't use this.lastTaskId as it might be from a previous message/session
            this.saveMessageToSession(message, message?.taskId || null, targetSessionId);
        }
    }

    generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Extract tool call data from message content
    extractToolCallFromContent(content) {
        if (!content || typeof content !== 'string') return null;
        
        // Try to parse JSON from content that might contain tool call data
        try {
            let jsonStr = content.trim();
            
            // Check if content starts with "📊 Data: " or contains JSON
            if (content.includes('📊 Data:')) {
                jsonStr = content.split('📊 Data:')[1].trim();
            } else if (!jsonStr.startsWith('{')) {
                // Try to find JSON object in the content
                const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    jsonStr = jsonMatch[0];
                } else {
                    return null;
                }
            }
            
            const data = JSON.parse(jsonStr);
            // Check if it looks like a tool call (has name and args/id)
            if (this.isToolCallData(data)) {
                return data;
            }
        } catch (e) {
            // Not JSON or not a tool call
        }
        
        return null;
    }

    // Create tool call card element
    createToolCallCard(toolCall) {
        const card = document.createElement('div');
        card.className = 'tool-call-card';

        const toolName = toolCall.name || 'Unknown Tool';
        const toolId = toolCall.id || 'N/A';
        const toolArgs = toolCall.args || {};
        const toolResponse = toolCall.response;
        const pendingState = (toolId && this.toolCallStatusById?.get(toolId)) || 'running';

        // Special handling for transfer_to_agent
        if (toolName === 'transfer_to_agent' && toolArgs.agent_name) {
            // Simplified card for agent transfers
            const formattedAgentName = this.formatAgentName(toolArgs.agent_name);
            const header = document.createElement('div');
            header.className = 'tool-call-header tool-call-header-no-border';
            header.innerHTML = `
                <div class="tool-call-name">
                    <i class="fas fa-exchange-alt"></i>
                    <span>Transferring to Agent</span>
                </div>
                <div class="tool-call-simple-content" style="display: inline-flex; align-items: center; gap: 0.75rem; margin-left: 1rem;">
                    <i class="fas fa-robot"></i>
                    <span class="agent-name">${formattedAgentName}</span>
                </div>
            `;

            card.appendChild(header);
            // No response section for transfer_to_agent (always null)
            return card;
        }

        // Standard tool call card for other tools
        // Tool header
        const header = document.createElement('div');
        header.className = 'tool-call-header';
        header.innerHTML = `
            <div class="tool-call-name">
                <i class="fas fa-wrench"></i>
                <span>${this.formatToolName(toolName)}</span>
            </div>
            <div class="tool-call-id">ID: ${toolId}</div>
        `;

        // Arguments section
        const argsSection = document.createElement('div');
        argsSection.className = 'tool-call-section';
        argsSection.innerHTML = `
            <div class="tool-call-label">Arguments:</div>
            <div class="tool-call-content">
                <pre>${JSON.stringify(toolArgs, null, 2)}</pre>
            </div>
        `;

        card.appendChild(header);
        card.appendChild(argsSection);

        // Response section (only show if response is not null and not a transfer_to_agent)
        if (toolResponse !== null && toolResponse !== undefined) {
            const responseSection = document.createElement('div');
            responseSection.className = 'tool-call-section tool-call-response';
            responseSection.innerHTML = `
                <div class="tool-call-label">Response:</div>
                <div class="tool-call-content">
                    <pre>${JSON.stringify(toolResponse, null, 2)}</pre>
                </div>
            `;
            card.appendChild(responseSection);
        } else if (toolName !== 'transfer_to_agent') {
            // Only show pending for non-transfer tools
            const pendingSection = document.createElement('div');
            pendingSection.className = 'tool-call-section tool-call-pending';
            pendingSection.innerHTML = `
                <div class="tool-call-label">Status:</div>
                <div class="tool-call-content">
                    <i class="tool-call-status-icon ${this.getToolCallStatusIcon(pendingState)}"></i>
                    <span class="tool-call-status-text">${this.getToolCallStatusLabel(pendingState)}</span>
                </div>
            `;
            card.appendChild(pendingSection);
        }

        return card;
    }

    getToolCallStatusLabel(state) {
        switch (state) {
            case 'input-required':
                return 'Waiting for user input';
            case 'waiting':
                return 'Waiting...';
            case 'failed':
                return 'Failed';
            case 'completed':
                return 'Completed';
            case 'running':
                return 'Executing...';
            default:
                return 'Pending...';
        }
    }

    getToolCallStatusIcon(state) {
        switch (state) {
            case 'input-required':
                return 'fas fa-question-circle';
            case 'waiting':
                return 'fas fa-hourglass-half';
            case 'failed':
                return 'fas fa-times-circle';
            case 'completed':
                return 'fas fa-check-circle';
            case 'running':
                return 'fas fa-spinner fa-spin';
            default:
                return 'fas fa-spinner fa-spin';
        }
    }

    updateToolCallPendingState(toolCallId, state) {
        if (!toolCallId || !state) {
            return;
        }
        if (!this.toolCallStatusById) {
            this.toolCallStatusById = new Map();
        }
        this.toolCallStatusById.set(toolCallId, state);

        const card = this.toolCallMessages?.get(toolCallId);
        if (!card) {
            return;
        }
        const pendingSection = card.querySelector('.tool-call-pending');
        if (!pendingSection) {
            return;
        }
        const content = pendingSection.querySelector('.tool-call-content');
        if (!content) {
            return;
        }
        const iconElement = content.querySelector('.tool-call-status-icon');
        const textElement = content.querySelector('.tool-call-status-text');
        if (iconElement) {
            iconElement.className = `tool-call-status-icon ${this.getToolCallStatusIcon(state)}`;
        }
        if (textElement) {
            textElement.textContent = this.getToolCallStatusLabel(state);
        }
    }

    updateToolCallStatusFromMessage(message, state) {
        if (!message || !Array.isArray(message.parts) || !state) {
            return;
        }
        message.parts.forEach(part => {
            if (part.kind === 'data' && this.isToolCallData(part.data) && part.data.id) {
                this.updateToolCallPendingState(part.data.id, state);
            }
        });
    }

    // Format agent name for display
    formatAgentName(agentName) {
        // Convert snake_case or kebab-case to Title Case
        return agentName
            .replace(/[-_]/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    formatTaskId(taskId) {
        if (!taskId) {
            return '';
        }

        return taskId.length > 16
            ? `${taskId.slice(0, 8)}…${taskId.slice(-4)}`
            : taskId;
    }

    // Update existing tool call card with response
    updateToolCallCard(card, toolCall) {
        const toolName = toolCall.name;
        const toolResponse = toolCall.response;
        
        // For transfer_to_agent, response is always null, so no need to update
        if (toolName === 'transfer_to_agent') {
            return; // Keep the simplified card as is
        }
        
        // Remove pending section if it exists
        const pendingSection = card.querySelector('.tool-call-pending');
        if (pendingSection) {
            pendingSection.remove();
        }
        
        // Add or update response section (only if response is not null)
        if (toolResponse !== null && toolResponse !== undefined) {
            if (toolCall.id && this.toolCallStatusById) {
                this.toolCallStatusById.delete(toolCall.id);
            }
            let responseSection = card.querySelector('.tool-call-response');
            if (!responseSection) {
                responseSection = document.createElement('div');
                responseSection.className = 'tool-call-section tool-call-response';
                card.appendChild(responseSection);
            }
            
            responseSection.innerHTML = `
                <div class="tool-call-label">Response:</div>
                <div class="tool-call-content">
                    <pre>${JSON.stringify(toolResponse, null, 2)}</pre>
                </div>
            `;
        }
    }

    // Format tool name for display
    formatToolName(toolName) {
        return toolName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    containsMarkdownCodeBlocks(content) {
        if (typeof content !== 'string') return false;
        return /```[\s\S]*?```/.test(content);
    }

    formatMarkdownContent(container, content) {
        if (window.marked) {
            try {
                // Use Marked.js to process the markdown with syntax highlighting
                const html = marked.parse(content);
                container.innerHTML = html;

                // Add custom styling to code blocks
                const codeBlocks = container.querySelectorAll('pre code');
                codeBlocks.forEach(block => {
                    const pre = block.parentElement;
                    pre.classList.add('code-container');

                    // Add language badge if available
                    const language = block.className.match(/language-(\w+)/);
                    if (language) {
                        const badge = document.createElement('span');
                        badge.className = 'code-language-badge';
                        badge.textContent = language[1].toUpperCase();
                        pre.insertBefore(badge, block);
                    }
                });
            } catch (error) {
                console.error('Error processing markdown:', error);
                container.textContent = content;
            }
        } else {
            // Fallback to plain text if Marked.js is not available
            container.textContent = content;
        }
    }


    showTypingIndicator(sessionId = null) {
        this.updateTypingIndicatorForSession(sessionId || this.sessionId, true);
    }

    hideTypingIndicator(sessionId = null) {
        this.updateTypingIndicatorForSession(sessionId || this.sessionId, false);
    }

    updateTypingIndicatorForSession(sessionId, isProcessing) {
        const targetSessionId = sessionId || this.sessionId;
        if (!targetSessionId) {
            return;
        }

        if (isProcessing) {
            this.processingSessions.add(targetSessionId);
        } else {
            this.processingSessions.delete(targetSessionId);
        }

        if (targetSessionId === this.sessionId) {
            const indicator = document.getElementById('typingIndicator');
            if (!indicator) {
                return;
            }

            if (isProcessing) {
                indicator.style.display = 'flex';
                this.isTyping = true;
                const container = document.querySelector('.chat-container');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            } else if (!this.processingSessions.has(this.sessionId)) {
                indicator.style.display = 'none';
                this.isTyping = false;
            }
        }
    }

    async handleFileAttachment(event) {
        const files = event.target.files;
        if (!files.length) return;

        for (let file of files) {
            // Check file size (limit to 50MB for A2A upload)
            if (file.size > 50 * 1024 * 1024) {
                this.showToast(`File ${file.name} is too large (max 50MB)`, 'error');
                continue;
            }

            // Ensure we have a session before uploading
            if (!this.sessionId) {
                this.createNewChat();
            }

            try {
                // Show upload progress
                this.showToast(`📤 Uploading "${file.name}"...`, 'info');

                // Upload file using A2A upload service
                const uploadResult = await this.uploadService.uploadFile(
                    file,
                    this.sessionId,
                    this.userId,
                    (progress) => {
                        // Update progress in UI
                        this.updateUploadProgress(file.name, progress);
                    }
                );

                // Add to attachments with upload result
                this.attachments.push({
                    name: file.name,
                    size: file.size,
                    type: file.type || 'application/octet-stream',
                    filename: uploadResult.filename,
                    namespace: uploadResult.namespace,
                    uploaded: true,
                    uploadResult: uploadResult
                });

                this.showToast(`✅ File "${file.name}" uploaded successfully`, 'success');

            } catch (error) {
                console.error('Error uploading file:', error);
                this.showToast(`Failed to upload file ${file.name}: ${error.message}`, 'error');
            }
        }

        this.updateAttachmentsPreview();

        // Reset file input
        event.target.value = '';
    }

    updateUploadProgress(filename, progress) {
        // Find the attachment and update its progress
        const attachment = this.attachments.find(att => att.name === filename);
        if (attachment) {
            attachment.uploadProgress = progress;
            this.updateAttachmentsPreview();
        }
    }

    updateAttachmentsPreview() {
        const preview = document.getElementById('attachmentsPreview');

        if (this.attachments.length === 0) {
            preview.style.display = 'none';
            return;
        }

        preview.style.display = 'flex';
        preview.innerHTML = '';

        this.attachments.forEach((attachment, index) => {
            const item = document.createElement('div');
            item.className = 'attachment-preview';

            let status = 'attached';
            let statusClass = 'attachment-status';

            if (attachment.uploaded) {
                status = 'uploaded';
                statusClass += ' uploaded';
            } else if (attachment.uploadProgress !== undefined) {
                status = `uploading ${Math.round(attachment.uploadProgress)}%`;
                statusClass += ' uploading';
            }

            item.innerHTML = `
                <i class="fas fa-file"></i>
                <span>${attachment.name}</span>
                <span class="${statusClass}">(${status})</span>
                <button onclick="app.removeAttachment(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            preview.appendChild(item);
        });
    }

    removeAttachment(index) {
        const attachment = this.attachments[index];
        if (attachment && attachment.uploaded) {
            // Note: In a production app, you might want to call an abort endpoint
            // to clean up the uploaded file on the server
            console.log(`Removed uploaded file: ${attachment.filename}`);
        }
        this.attachments.splice(index, 1);
        this.updateAttachmentsPreview();
    }

    clearAttachments() {
        this.attachments = [];
        this.updateAttachmentsPreview();
    }

    // Extract sub-agent information from orchestrator card
    extractSubAgents(orchestratorCard) {
        this.agents = [];
        this.parentAgents = [];

        // Extract sub-agent information from skills section
        const skills = orchestratorCard.skills || [];

        // Group skills by agent ID
        const agentGroups = {};

        for (const skill of skills) {
            // Skip the orchestrator's own skill (orchestration)
            if (skill.id === 'orchestration') {
                continue;
            }

            // Don't skip tools - they should be included as skills of subagents

            // Extract sub-agent info from skill tags
            const subAgentTag = skill.tags?.find(tag => tag.startsWith('sub_agent:'));
            if (subAgentTag) {
                const agentId = subAgentTag.replace('sub_agent:', '');
                console.log(`Skill "${skill.name}" belongs to agent: ${agentId}`, skill);

                if (!agentGroups[agentId]) {
                    agentGroups[agentId] = [];
                }
                agentGroups[agentId].push(skill);
            }
        }

        // First, identify which agents are actually subagents by looking at their skill names
        const subagentAgents = new Set();
        for (const [agentId, agentSkills] of Object.entries(agentGroups)) {
            // If an agent's skills have names like "something: model", it's likely a subagent
            const hasSubagentNaming = agentSkills.some(skill =>
                skill.name.includes(':') && skill.name !== 'model'
            );
            if (hasSubagentNaming) {
                subagentAgents.add(agentId);
            }
        }

        console.log('Detected subagent agents:', Array.from(subagentAgents));

        // Process each agent group
        for (const [agentId, agentSkills] of Object.entries(agentGroups)) {
            console.log(`Processing agent: ${agentId}`, agentSkills);

            // Skip if this is a subagent - we'll handle it later
            if (subagentAgents.has(agentId)) {
                console.log(`Skipping subagent: ${agentId}`);
                continue;
            }

            // Find the main skill (usually named 'model' or matches agent ID)
            const mainSkill = agentSkills.find(skill =>
                skill.name === 'model' ||
                skill.name === agentId ||
                skill.name === agentId.replace('-', '_')
            );

            console.log(`Main skill for ${agentId}:`, mainSkill);

            if (mainSkill) {
                // This is a parent agent - collect only skills that belong to THIS agent
                // Skills can have multiple sub_agent tags (one for sub-agent, one for parent)
                const allSkills = [...agentSkills];

                // Add all skills that have THIS parent agent in their sub_agent tags
                for (const skill of skills) {
                    // Skip if already included
                    if (allSkills.includes(skill)) continue;
                    
                    // Check if this skill has a sub_agent tag matching this parent agent
                    const hasParentTag = skill.tags?.some(tag => 
                        tag.startsWith('sub_agent:') && tag === `sub_agent:${agentId}`
                    );
                    
                    if (hasParentTag) {
                        allSkills.push(skill);
                    }
                }

                const parentAgent = {
                    agent_id: agentId,
                    status: 'online',
                    capabilities: mainSkill.tags || [],
                    skills: allSkills,
                    subagents: [],
                    agent_card: {
                        name: mainSkill.name,
                        description: mainSkill.description,
                        skills: [mainSkill]
                    }
                };

                // Group skills by subagent name to collect all tools for each subagent
                // Skills have format "subagent_name: tool_name" or "subagent_name: model"
                const subagentGroups = {};
                const subagentSkills = allSkills.filter(skill => {
                    // Skip the main skill
                    if (skill === mainSkill) return false;
                    
                    // Only include skills with colon notation (subagent: tool format)
                    // Exclude "planning" skills as they're not sub-agents
                    return skill.name.includes(':') && 
                           skill.name !== 'model' && 
                           !skill.name.endsWith(': planning');
                });

                // Group skills by subagent name (the part before the colon)
                for (const skill of subagentSkills) {
                    const subagentName = skill.name.split(':')[0].trim();
                    if (!subagentGroups[subagentName]) {
                        subagentGroups[subagentName] = [];
                    }
                    subagentGroups[subagentName].push(skill);
                }

                console.log(`Subagent groups for ${agentId}:`, subagentGroups);

                // Create subagent objects with all their skills/tools
                for (const [subagentName, skills] of Object.entries(subagentGroups)) {
                    // Find the main skill (usually the one with 'model' in the name)
                    const mainSubagentSkill = skills.find(skill =>
                        skill.name.includes(': model') ||
                        skill.name.endsWith(': model')
                    ) || skills[0]; // Fallback to first skill if no model found

                    console.log(`Adding subagent: ${subagentName} with skills:`, skills);

                    parentAgent.subagents.push({
                        agent_id: subagentName,
                        capabilities: mainSubagentSkill.tags || [],
                        skills: skills, // All skills including tools
                        agent_card: {
                            name: mainSubagentSkill.name,
                            description: mainSubagentSkill.description,
                            skills: skills
                        }
                    });
                }

                this.parentAgents.push(parentAgent);
            } else {
                // This is a standalone agent (no main skill and not a detected subagent)
                const standaloneAgent = {
                    agent_id: agentId,
                    status: 'online',
                    capabilities: agentSkills[0]?.tags || [],
                    skills: agentSkills,
                    agent_card: {
                        name: agentSkills[0]?.name || agentId,
                        description: agentSkills[0]?.description || 'Specialized agent',
                        skills: agentSkills
                    }
                };
                this.agents.push(standaloneAgent);
            }
        }

        // Debug logging
        console.log('Parent agents:', this.parentAgents);
        console.log('Standalone agents:', this.agents);

        this.updateAgentsList();
        const totalAgents = this.parentAgents.length + this.agents.length;
        this.showToast(`Connected to Agent Platform (${totalAgents} agents)`, 'success');
    }


    updateAgentsList() {
        const agentsList = document.getElementById('agentsList');
        agentsList.innerHTML = '';

        // Display parent agents (simple list, no expandable functionality)
        this.parentAgents.forEach(parentAgent => {
            const parentLi = document.createElement('li');
            parentLi.className = 'agent-item';
            const description = parentAgent.agent_card?.description || 'Specialized agent';
            parentLi.innerHTML = `
                <div class="agent-info">
                    <div class="agent-icon" style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-color); display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; color: white; font-size: 0.875rem;">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <div class="agent-name">${parentAgent.agent_id}</div>
                        <div class="agent-description" 
                             style="word-wrap: break-word; white-space: normal; max-width: 200px; font-size: 0.85em; color: #666; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; ">${description}</div>
                    </div>
                </div>
                <span class="status-dot ${parentAgent.status === 'online' ? 'online' : 'offline'}" style="width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: auto; flex-shrink: 0;"></span>
            `;

            // Add tooltip functionality
            this.addTooltipToAgent(parentLi, description);

            parentLi.addEventListener('click', () => {
                console.log('Parent agent clicked:', parentAgent);
                this.showAgentDetails(parentAgent);
            });
            agentsList.appendChild(parentLi);
        });

        // Display standalone agents (agents without subagents)
        this.agents.forEach(agent => {
            const li = document.createElement('li');
            li.className = 'agent-item';
            const description = agent.agent_card?.description || 'Specialized agent';
            li.innerHTML = `
                <div class="agent-info">
                    <div class="agent-icon" style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-color); display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; color: white; font-size: 0.875rem;">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <div class="agent-name">${agent.agent_id}</div>
                        <div class="agent-description" 
                             style="word-wrap: break-word; white-space: normal; max-width: 200px; font-size: 0.85em; color: #666; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; ">${description}</div>
                    </div>
                </div>
                <span class="status-dot ${agent.status === 'online' ? 'online' : 'offline'}" style="width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: auto; flex-shrink: 0;"></span>
            `;

            // Add tooltip functionality
            this.addTooltipToAgent(li, description);

            li.addEventListener('click', () => {
                console.log('Agent clicked:', agent);
                this.showAgentDetails(agent);
            });
            agentsList.appendChild(li);
        });
    }

    addTooltipToAgent(agentElement, description) {
        let tooltip = null;

        agentElement.addEventListener('mouseenter', (e) => {
            // Create tooltip if it doesn't exist
            if (!tooltip) {
                tooltip = document.createElement('div');
                tooltip.className = 'agent-tooltip';
                tooltip.textContent = description;
                document.body.appendChild(tooltip);
            }

            // Position tooltip to the right of the agent card
            const rect = agentElement.getBoundingClientRect();
            tooltip.style.left = (rect.right + 12) + 'px';
            tooltip.style.top = (rect.top + rect.height / 2) + 'px';
            tooltip.style.transform = 'translateY(-50%)';

            // Show tooltip
            tooltip.classList.add('show');
        });

        agentElement.addEventListener('mouseleave', () => {
            if (tooltip) {
                tooltip.classList.remove('show');
            }
        });

        // Clean up tooltip when agent element is removed
        agentElement.addEventListener('DOMNodeRemoved', () => {
            if (tooltip && tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        });
    }

    showAgentDetails(agent) {
        const panel = document.getElementById('agentPanel');
        const details = document.getElementById('agentDetails');

        // Debug logging
        console.log('Showing details for agent:', agent);
        console.log('Agent subagents:', agent.subagents);

        let subagentsHtml = '';
        if (agent.subagents && agent.subagents.length > 0) {
            subagentsHtml = `
                <div class="agent-detail">
                    <h4><i class="fas fa-sitemap" style="margin-right: 8px; color: var(--primary-color);"></i>Sub-agents (${agent.subagents.length})</h4>
                    <div class="subagents-grid">
                        ${agent.subagents.map(subagent => `
                            <div class="subagent-card" data-description="${subagent.agent_card?.description || 'Specialized sub-agent'}">
                                <h5 class="subagent-title">${subagent.agent_id}</h5>
                                
                                <p class="subagent-description">${subagent.agent_card?.description || 'Specialized sub-agent'}</p>
                                
                                ${subagent.skills && subagent.skills.filter(skill => !skill.name.includes(': model')).length > 0 ? `
                                    <div class="subagent-tools">
                                        <h6 class="tools-title">Tools:</h6>
                                        <div class="tools-list">
                                            ${subagent.skills
                        .filter(skill => !skill.name.includes(': model'))
                        .map(skill => {
                            // Extract just the tool name (part after the colon)
                            const toolName = skill.name.includes(':') ? skill.name.split(':')[1].trim() : skill.name;
                            const toolDescription = skill.description || '';
                            return `<span class="tool-tag" data-hide-tooltip="true">${toolName}: ${toolDescription}</span>`;
                        }).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                                
                                <div class="subagent-overlay"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        details.innerHTML = `
            <div class="agent-detail">
                <h4>Agent ID</h4>
                <p>${agent.agent_id}</p>
            </div>
            <div class="agent-detail">
                <h4>Description</h4>
                <p style="word-wrap: break-word; white-space: normal; max-width: 100%; line-height: 1.4; font-size: 0.9em; color: #666;">${agent.agent_card?.description || 'Specialized agent'}</p>
            </div>
            <div class="agent-detail">
                <h4>Capabilities</h4>
                <ul>
                    ${(agent.capabilities || [])
                .filter(cap => !cap.includes(`sub_agent:${agent.agent_id}`))
                .map(cap => `<li>${cap}</li>`).join('')}
                </ul>
            </div>
            ${subagentsHtml}
        `;

        // No click handlers needed for subagent cards

        panel.style.display = 'flex';
    }

    hideAgentPanel() {
        document.getElementById('agentPanel').style.display = 'none';
    }


    createNewChat() {
        console.log('=== CREATING NEW CHAT ===');
        console.log('Previous sessionId:', this.sessionId);
        // Generate a new session ID for the new session
        this.sessionId = this.generateSessionId();
        console.log('New sessionId:', this.sessionId);
        this.sessionArtifactRefs.set(this.sessionId, []);

        // Generate a new session with the new session ID
        const session = this.generateSessionData();

        // Add to sessions array
        this.sessions.push(session);
        console.log('➕ Added new session to sessions array:', { id: session.id, taskIds: session.taskIds });
        console.log('📊 Current sessions count:', this.sessions.length);

        this.clearActiveInputContext();

        // Store in localStorage
        const sessionData = JSON.parse(localStorage.getItem('sessionData') || '{}');
        sessionData[session.id] = {
            id: session.id,
            sessionId: session.sessionId,
            taskIds: session.taskIds,
            title: session.title,
            created_at: session.created_at
        };
        localStorage.setItem('sessionData', JSON.stringify(sessionData));
        console.log('💾 Saved session to localStorage:', { id: session.id, taskIds: session.taskIds });
        console.log('📦 Current localStorage state:', JSON.stringify(sessionData, null, 2));

        // No need for currentSessionId since it's always equal to sessionId

        // Update sessions list UI
        this.updateSessionsList();

        // Clear chat messages
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        } else {
            console.warn('chatMessages element not found');
        }

        // Clear tool call messages map to prevent stale references
        this.toolCallMessages.clear();
        
        // Clear processed artifacts tracking for fresh start
        this.processedTaskArtifacts.clear();
        this.displayedArtifactIds.clear();
        this.toolCallStatusById.clear();

        // Hide typing indicator from previous session (new chat means no processing for this session)
        this.hideTypingIndicator();
        // Note: Don't clear processingSessions Set - other sessions may still be processing

        // Show welcome message for new session
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'block';
        } else {
            console.warn('welcomeMessage element not found');
        }

        // Update chat title
        const chatTitle = document.getElementById('chatTitle');
        if (chatTitle) {
            chatTitle.textContent = 'New Session';
        } else {
            console.warn('chatTitle element not found');
        }

        this.showToast('New session started', 'success');
    }

    clearChat() {
        this.showConfirmModal(
            'Clear Chat',
            'Are you sure you want to clear this chat? This action cannot be undone.',
            () => {
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                }
                // Clear tool call messages map to prevent stale references
                this.toolCallMessages.clear();
                this.toolCallStatusById.clear();
                this.showToast('Chat cleared', 'success');
            }
        );
    }

    async exportChat() {
        try {
            // Export current session from in-memory data
            const session = this.sessions.find(s => s.id === this.sessionId);

            if (!session) {
                this.showToast('No session to export', 'warning');
                return;
            }

            // Create export data with session info
            const exportData = {
                session_id: this.sessionId,
                user_id: this.userId,
                title: session.title,
                created_at: session.created_at,
                exported_at: new Date().toISOString(),
                messages: session.messages,
                note: "This export contains the session data currently in memory. Full session history is managed by the A2A protocol."
            };

            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chat_export_${this.sessionId}.json`;
            a.click();

            this.showToast('Chat exported successfully', 'success');
        } catch (error) {
            console.error('Error exporting chat:', error);
            this.showToast('Failed to export chat', 'error');
        }
    }

    async loadSessions() {
        // Load session data from localStorage
        const sessionData = JSON.parse(localStorage.getItem('sessionData') || '{}');

        // Create session objects with task_ids
        this.sessions = Object.values(sessionData).map(conv => {
            return {
                id: conv.id,
                sessionId: conv.sessionId,
                taskIds: conv.taskIds || [], // Array of task_ids for this session
                title: conv.title,
                messages: [], // Messages will be loaded when session is clicked
                created_at: conv.created_at,
                lastMessageAt: conv.lastMessageAt || conv.created_at
            };
        });
        this.sessions.forEach(session => {
            if (!this.sessionArtifactRefs.has(session.id)) {
                this.sessionArtifactRefs.set(session.id, []);
            }
        });

        this.updateSessionsList();

        // Don't create a session automatically - wait for user to send first message

        // Show session info in console for debugging
        console.log('Loaded sessions:', this.sessions.length);
    }

    updateSessionsList() {
        const list = document.getElementById('sessionsList');
        if (!list) {
            console.error('Sessions list element not found');
            return;
        }

        // Store reference to container for event delegation
        this.sessionsListContainer = list;

        // Remove existing event listeners by cloning the container
        const newList = list.cloneNode(false);
        list.parentNode.replaceChild(newList, list);
        this.sessionsListContainer = newList;


        this.sessions.forEach(session => {
            const li = document.createElement('li');
            li.className = 'session-item';
            const createdDate = session.created_at ? new Date(session.created_at).toLocaleDateString() : '';
            li.innerHTML = `
                <a href="#" data-id="${session.id}" class="session-link">
                    <div class="session-title">${session.title}</div>
                    ${createdDate ? `<div class="session-date">${createdDate}</div>` : ''}
                </a>
                <button class="btn-delete-session" data-id="${session.id}" title="Delete session">
                    <i class="fas fa-trash"></i>
                </button>
            `;

            newList.appendChild(li);
        });

        // If no sessions, show a message
        if (this.sessions.length === 0) {
            const emptyLi = document.createElement('li');
            emptyLi.className = 'session-item empty';
            emptyLi.innerHTML = '<div class="empty-sessions">No sessions yet</div>';
            newList.appendChild(emptyLi);
        }

        // Show/hide delete all button based on whether there are sessions
        const deleteAllBtn = document.getElementById('deleteAllBtn');
        if (deleteAllBtn) {
            deleteAllBtn.style.display = this.sessions.length > 0 ? 'flex' : 'none';
        }

        // Set up event delegation on the container
        this.setupSessionsListEventDelegation();
    }

    setupSessionsListEventDelegation() {
        if (!this.sessionsListContainer) return;

        // Remove any existing event listeners
        this.sessionsListContainer.removeEventListener('click', this.handleSessionsListClick);

        // Add event delegation for all clicks within the sessions list
        this.sessionsListContainer.addEventListener('click', this.handleSessionsListClick.bind(this));
    }

    handleSessionsListClick(event) {
        const target = event.target;

        // Handle session link clicks
        if (target.closest('.session-link')) {
            const sessionLink = target.closest('.session-link');
            const sessionId = sessionLink.getAttribute('data-id');

            if (sessionId) {
                console.log('🖱️ Session link clicked:', sessionId, event);
                event.preventDefault();
                this.loadSession(sessionId);
            }
        }

        // Handle delete button clicks
        if (target.closest('.btn-delete-session')) {
            const deleteBtn = target.closest('.btn-delete-session');
            const sessionId = deleteBtn.getAttribute('data-id');

            if (sessionId) {
                console.log('🗑️ Delete button clicked:', sessionId, event);
                event.preventDefault();
                event.stopPropagation();
                this.deleteSession(sessionId);
            }
        }
    }

    saveMessageToSession(message, taskId = null, targetSessionId = null) {
        // A2A Protocol Understanding:
        // - Each message creates a NEW task (task_id)
        // - Tasks are in terminal state after completion
        // - Sessions track all task_ids for history loading
        // - We use tasks/get to load history for each task_id

        // Use targetSessionId if provided, otherwise fall back to current sessionId
        const sessionIdToUse = targetSessionId || this.sessionId;

        console.log('=== SAVING MESSAGE TO SESSION ===');
        console.log('Target sessionId:', sessionIdToUse);
        console.log('TaskId to save:', taskId);

        // Find existing session by targetSessionId
        let current = this.sessions.find(s => s.id === sessionIdToUse);
        console.log('Found current session:', current ? { id: current.id, title: current.title, taskIds: current.taskIds } : 'NOT FOUND');

        if (current) {
            // Only store messages in-memory if we don't have task_ids (fallback for new sessions)
            if (current.taskIds.length === 0) {
                current.messages.push(message);
            }
            current.lastMessageAt = new Date().toISOString();

            // Add task_id to session if provided
            if (taskId && !current.taskIds.includes(taskId)) {
                current.taskIds.push(taskId);
                console.log('Added task_id to session:', taskId, 'Session now has taskIds:', current.taskIds);

                // Clear in-memory messages since we now have task_ids (can load from A2A protocol)
                current.messages = [];

                // Update localStorage with the new task_id
                const sessionData = JSON.parse(localStorage.getItem('sessionData') || '{}');
                if (sessionData[current.id]) {
                    sessionData[current.id].taskIds = current.taskIds;
                    localStorage.setItem('sessionData', JSON.stringify(sessionData));
                } else {
                    console.warn('⚠️ Session not found in localStorage:', current.id);
                }
            }
        } else {
            // This should not happen anymore since we create session in createNewChat
            console.warn('No session found for sessionId:', sessionIdToUse);
            console.warn('Available sessions:', this.sessions.map(c => c.id));

            // Fallback: create new session (shouldn't happen in normal flow)
            let title = message.content.substring(0, 50);
            if (message.content.length > 50) {
                title += '...';
            }
            if (!title.trim()) {
                title = 'New Session';
            }

            const newSession = this.generateSessionData();
            newSession.title = title;
            newSession.messages = [message];

            // Add task_id if provided
            if (taskId) {
                newSession.taskIds.push(taskId);
                console.log('Created fallback session with task_id:', taskId);
            }

            this.sessions.push(newSession);
            this.sessionArtifactRefs.set(newSession.id, []);

            // Store session data in localStorage
            const sessionData = JSON.parse(localStorage.getItem('sessionData') || '{}');
            sessionData[newSession.id] = {
                id: newSession.id,
                sessionId: newSession.sessionId,
                taskIds: newSession.taskIds,
                title: newSession.title,
                created_at: newSession.created_at
            };
            localStorage.setItem('sessionData', JSON.stringify(sessionData));
        }

        // Update the sessions list UI
        this.updateSessionsList();

        // Update chat title if this is a new session
        if (!current) {
            const chatTitle = document.getElementById('chatTitle');
            if (chatTitle) {
                chatTitle.textContent = this.sessions.find(s => s.id === this.sessionId)?.title || 'New Session';
            }
        }
    }

    async loadSession(sessionId) {
        console.log('=== LOADING SESSION ===');
        console.log('Requested sessionId:', sessionId);

        const session = this.sessions.find(s => s.id === sessionId);


        if (session) {
            // Set the session ID to the session ID (they're the same)
            this.sessionId = sessionId;
            this.restoreInputContextForSession(sessionId);

            // Clear chat messages completely
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                // More robust clearing - remove all child nodes
                while (chatMessages.firstChild) {
                    chatMessages.removeChild(chatMessages.firstChild);
                }
            } else {
                console.error('chatMessages element not found');
            }

            // Clear tool call messages map to prevent stale references
            this.toolCallMessages.clear();
            this.toolCallStatusById.clear();

            // Show typing indicator if this session is still processing
            // Hide it if switching to a different session that's not processing
            if (this.processingSessions.has(sessionId)) {
                // This session is still processing, show typing indicator
                this.showTypingIndicator(sessionId);
            } else {
                // This session is not processing, hide typing indicator
                this.hideTypingIndicator();
            }

            // Hide welcome message
            const welcomeMessage = document.getElementById('welcomeMessage');
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }

            // Update chat title
            const chatTitle = document.getElementById('chatTitle');
            if (chatTitle) {
                chatTitle.textContent = session.title;
            }

            // Small delay to ensure clearing is complete
            await new Promise(resolve => setTimeout(resolve, 10));

            // Load messages from task_ids using A2A protocol
            if (session.taskIds && session.taskIds.length > 0) {
                this.showToast('Loading session history...', 'info');

                try {
                    const allMessages = [];

                    // Load history for each task_id
                    for (const taskId of session.taskIds) {

                        const response = await this.sendJSONRPCRequest('tasks/get', {
                            id: taskId,
                            historyLength: 50
                        });

                        if (response.result && response.result.history) {
                            // Add messages from this task
                            response.result.history.forEach(msg => {
                                const attachments = this.extractArtifactRefs(msg);
                                allMessages.push({
                                    id: msg.messageId || this.generateMessageId(),
                                    type: msg.role === 'user' ? 'user' : 'agent',
                                    content: this.formatA2AMessage(msg),
                                    attachments: attachments.length > 0 ? attachments : undefined,
                                    timestamp: new Date().toISOString(),
                                    agent: msg.role === 'agent' ? this.currentAgentName : null,
                                    taskId: taskId
                                });
                            });
                        }
                    }

                    // Sort messages by timestamp and display them
                    allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

                    // Deduplicate messages by ID to avoid showing the same message twice
                    const seenIds = new Set();
                    const uniqueMessages = allMessages.filter(msg => {
                        if (seenIds.has(msg.id)) {
                            return false;
                        }
                        seenIds.add(msg.id);
                        return true;
                    });

                    console.log('Loading', uniqueMessages.length, 'messages for session:', sessionId);
                    uniqueMessages.forEach(msg => {
                        this.addMessageToChat(msg, false, sessionId); // Don't save to session (already loaded)
                    });

                    this.showToast(`Loaded ${uniqueMessages.length} messages from ${session.taskIds.length} tasks`, 'success');

                } catch (error) {
                    console.error('Error loading session history:', error);
                    this.showToast('Error loading session history', 'error');

                    // Show fallback message
                    this.addMessageToChat({
                        id: 'error_' + Date.now(),
                        type: 'agent',
                        content: '⚠️ **Error Loading History**\n\nCould not load session history. You can continue chatting from here.',
                        timestamp: new Date().toISOString(),
                        agent: 'system'
                    }, false);
                }
            } else if (session.messages && session.messages.length > 0) {
                // Load messages from in-memory session (fallback for sessions without task_ids)
                session.messages.forEach(msg => {
                    this.addMessageToChat(msg, false, sessionId); // Don't save to session (already loaded)
                });
                this.showToast('Session loaded from memory', 'success');
            } else {
                // No task_ids and no in-memory messages, show info message
                this.addMessageToChat({
                    id: 'info_' + Date.now(),
                    type: 'agent',
                    content: '💬 **New Session**\n\nThis is a new session. Start chatting to begin!',
                    timestamp: new Date().toISOString(),
                    agent: 'system'
                }, false);

                this.showToast('New session started', 'info');
            }
        }
    }

    deleteSession(sessionId) {
        // Show confirmation dialog
        const session = this.sessions.find(s => s.id === sessionId);
        const sessionTitle = session ? session.title : 'this session';

        this.showConfirmModal(
            'Delete Session',
            `Are you sure you want to delete "${sessionTitle}"? This action cannot be undone.`,
            () => {
                this.performDeleteSession(sessionId);
            }
        );
    }

    performDeleteSession(sessionId) {
        console.log('Deleting session:', sessionId);
        console.log('Sessions before deletion:', this.sessions.length);

        // Remove session from array
        this.sessions = this.sessions.filter(c => c.id !== sessionId);
        console.log('Sessions after deletion:', this.sessions.length);

        this.removeInputRequestsForSession(sessionId);
        this.clearSessionArtifacts(sessionId);

        // Remove session from localStorage
        const sessionData = JSON.parse(localStorage.getItem('sessionData') || '{}');
        delete sessionData[sessionId];
        localStorage.setItem('sessionData', JSON.stringify(sessionData));
        console.log('Removed from localStorage:', sessionId);

        // If we're deleting the current session, clear the current session
        if (this.sessionId === sessionId) {
            console.log('Deleting current session, clearing current session');
            // Generate new session ID for new session
            this.sessionId = this.generateSessionId();
            this.sessionArtifactRefs.set(this.sessionId, []);

            // Clear the chat area and recreate welcome message
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.innerHTML = this.getWelcomeMessageHTML();
                console.log('Recreated welcome message after single session deletion');
            } else {
                console.warn('chatMessages element not found after single session deletion');
            }

            // Update chat title
            const chatTitle = document.getElementById('chatTitle');
            if (chatTitle) {
                chatTitle.textContent = 'New Session';
            }
        }

        // Update the sessions list UI
        console.log('Updating sessions list UI');
        this.updateSessionsList();

        // Show success message
        this.showToast('Session deleted successfully', 'success');
    }

    deleteAllSessions() {
        // Check if there are any sessions to delete
        if (this.sessions.length === 0) {
            this.showToast('No sessions to delete', 'info');
            return;
        }

        // Show confirmation dialog
        const count = this.sessions.length;
        this.showConfirmModal(
            'Delete All Sessions',
            `Are you sure you want to delete all ${count} session${count > 1 ? 's' : ''}? This action cannot be undone.`,
            () => {
                this.performDeleteAllSessions(count);
            }
        );
    }

    performDeleteAllSessions(count) {

        console.log('Deleting all sessions, count:', count);

        // Clear all sessions (in-memory only)
        this.sessions = [];

        this.pendingInputRequests.clear();
        this.clearActiveInputContext();
        this.sessionArtifactRefs.clear();

        // Clear session data from localStorage
        localStorage.removeItem('sessionData');

        // Generate new session ID for new session
        this.sessionId = this.generateSessionId();
        console.log('🆕 Generated new sessionId after clear all:', this.sessionId);
        this.sessionArtifactRefs.set(this.sessionId, []);

        // Clear the chat area and recreate welcome message
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = this.getWelcomeMessageHTML();
            console.log('Recreated welcome message after clear all');
        } else {
            console.warn('chatMessages element not found after clear all');
        }

        // Update chat title
        const chatTitle = document.getElementById('chatTitle');
        if (chatTitle) {
            chatTitle.textContent = 'New Session';
        }

        console.log('Sessions cleared, new length:', this.sessions.length);

        // Update the sessions list
        this.updateSessionsList();

        // Show success message
        this.showToast(`All ${count} session${count > 1 ? 's' : ''} deleted successfully`, 'success');
    }

    showSettings() {
        document.getElementById('settingsModal').style.display = 'flex';

        // Load current settings
        document.getElementById('apiEndpoint').value = this.apiEndpoint;

        // Load retry configuration
        document.getElementById('retryAttempts').value = localStorage.getItem('retryAttempts') || '3';
        document.getElementById('retryInterval').value = localStorage.getItem('retryInterval') || '2';

        // Load toast behavior
        const toastBehaviorSelect = document.getElementById('toastBehavior');
        if (toastBehaviorSelect) {
            toastBehaviorSelect.value = localStorage.getItem('toastBehavior') || 'stack';
        }

        // Load notification preferences - check actual permission status
        const notificationsEnabled = localStorage.getItem('notificationsEnabled') === 'true';
        const hasPermission = 'Notification' in window && Notification.permission === 'granted';

        // Only enable if user preference is true AND permission is granted
        document.getElementById('notificationsEnabled').checked = notificationsEnabled && hasPermission;
        document.getElementById('taskCompletedNotifications').checked = localStorage.getItem('taskCompletedNotifications') !== 'false';
        document.getElementById('taskFailedNotifications').checked = localStorage.getItem('taskFailedNotifications') !== 'false';
    }

    hideSettings() {
        document.getElementById('settingsModal').style.display = 'none';
    }

    saveSettings() {
        const endpoint = document.getElementById('apiEndpoint').value;

        localStorage.setItem('apiEndpoint', endpoint);

        // Save retry configuration
        const retryAttempts = document.getElementById('retryAttempts').value;
        const retryInterval = document.getElementById('retryInterval').value;

        localStorage.setItem('retryAttempts', retryAttempts);
        localStorage.setItem('retryInterval', retryInterval);

        // Save toast behavior
        const toastBehaviorSelect = document.getElementById('toastBehavior');
        if (toastBehaviorSelect) {
            const toastBehavior = toastBehaviorSelect.value;
            localStorage.setItem('toastBehavior', toastBehavior);
            this.toastBehavior = toastBehavior;
        }

        // Save notification preferences
        const notificationsEnabled = document.getElementById('notificationsEnabled').checked;
        const taskCompletedNotifications = document.getElementById('taskCompletedNotifications').checked;
        const taskFailedNotifications = document.getElementById('taskFailedNotifications').checked;

        localStorage.setItem('notificationsEnabled', notificationsEnabled);
        localStorage.setItem('taskCompletedNotifications', taskCompletedNotifications);
        localStorage.setItem('taskFailedNotifications', taskFailedNotifications);

        this.apiEndpoint = endpoint;

        // Update upload service endpoint
        this.uploadService.apiEndpoint = endpoint;

        // Update orchestrator header with new endpoint (this will also reload sub-agents)
        this.updateOrchestratorHeader();

        this.hideSettings();
        this.showToast('Settings saved successfully', 'success');
    }

    changeTheme(theme) {
        localStorage.setItem('theme', theme);
        this.applyTheme();
    }

    toggleStreaming() {
        this.streamingEnabled = !this.streamingEnabled;
        localStorage.setItem('streamingEnabled', this.streamingEnabled);
        this.updateStreamingIcon();
        this.showToast(
            `Streaming ${this.streamingEnabled ? 'enabled' : 'disabled'}`,
            'info'
        );
    }

    updateStreamingIcon() {
        const streamingIcon = document.getElementById('streamingIcon');
        const streamingBtn = document.getElementById('streamingToggleBtn');
        if (streamingIcon) {
            streamingIcon.className = 'fas fa-rss';
            streamingIcon.style.color = this.streamingEnabled ? '#10b981' : '#ef4444'; // Green when enabled, red when disabled
            streamingIcon.style.fontSize = '18px';
        }
        if (streamingBtn) {
            streamingBtn.title = `Streaming: ${this.streamingEnabled ? 'Enabled' : 'Disabled'}`;
            streamingBtn.style.backgroundColor = 'transparent';
        }
    }

    toggleTheme() {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.changeTheme(newTheme);
        this.updateThemeIcon(newTheme);
    }

    updateThemeIcon(theme) {
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    applyTheme() {
        const theme = localStorage.getItem('theme') || 'dark';
        document.body.className = `theme-${theme}`;

        // Update theme toggle icon
        this.updateThemeIcon(theme);

        // Update button states to match the applied theme
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-theme="${theme}"]`).classList.add('active');

        if (theme === 'light') {
            // Light theme CSS variables
            document.documentElement.style.setProperty('--bg-primary', '#ffffff');
            document.documentElement.style.setProperty('--bg-secondary', '#f5f5f5');
            document.documentElement.style.setProperty('--bg-tertiary', '#e5e5e5');
            document.documentElement.style.setProperty('--bg-hover', '#e8e8e8');
            document.documentElement.style.setProperty('--text-primary', '#1a1a1a');
            document.documentElement.style.setProperty('--text-secondary', '#4a4a4a');
            document.documentElement.style.setProperty('--text-tertiary', '#7a7a7a');
            document.documentElement.style.setProperty('--text-muted', 'rgba(26, 26, 26, 0.6)');
            document.documentElement.style.setProperty('--border-color', '#e0e0e0');
            document.documentElement.style.setProperty('--error-hover', '#b91c1c');
            document.documentElement.style.setProperty('--modal-backdrop', 'rgba(0, 0, 0, 0.5)');
            // Light theme shadows (more prominent for light backgrounds)
            document.documentElement.style.setProperty('--shadow-sm', '0 2px 4px rgba(0, 0, 0, 0.15)');
            document.documentElement.style.setProperty('--shadow-md', '0 4px 6px rgba(0, 0, 0, 0.15)');
            document.documentElement.style.setProperty('--shadow-lg', '0 10px 15px rgba(0, 0, 0, 0.15)');
            document.documentElement.style.setProperty('--shadow-xl', '0 20px 25px rgba(0, 0, 0, 0.15)');
        } else {
            // Dark theme CSS variables (reset to default values)
            document.documentElement.style.setProperty('--bg-primary', '#1a1a1a');
            document.documentElement.style.setProperty('--bg-secondary', '#2a2a2a');
            document.documentElement.style.setProperty('--bg-tertiary', '#3a3a3a');
            document.documentElement.style.setProperty('--bg-hover', '#2d2d3a');
            document.documentElement.style.setProperty('--text-primary', '#ffffff');
            document.documentElement.style.setProperty('--text-secondary', '#b0b0b0');
            document.documentElement.style.setProperty('--text-tertiary', '#808080');
            document.documentElement.style.setProperty('--text-muted', 'rgba(255, 255, 255, 0.8)');
            document.documentElement.style.setProperty('--border-color', '#404040');
            document.documentElement.style.setProperty('--error-hover', '#dc2626');
            document.documentElement.style.setProperty('--modal-backdrop', 'rgba(0, 0, 0, 0.8)');
            // Dark theme shadows (original values)
            document.documentElement.style.setProperty('--shadow-sm', '0 2px 4px rgba(0, 0, 0, 0.1)');
            document.documentElement.style.setProperty('--shadow-md', '0 4px 6px rgba(0, 0, 0, 0.1)');
            document.documentElement.style.setProperty('--shadow-lg', '0 10px 15px rgba(0, 0, 0, 0.1)');
            document.documentElement.style.setProperty('--shadow-xl', '0 20px 25px rgba(0, 0, 0, 0.1)');
        }
    }

    showToast(message, type = 'info') {
        if (this.toastBehavior === 'replace') {
            // Replace mode: clear existing toasts
            const existingContainer = document.getElementById('toastContainer');
            if (existingContainer) {
                existingContainer.remove();
            }
        }
        
        // Create a new toast element
        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        
        const toastContent = document.createElement('div');
        toastContent.className = 'toast-content';
        
        const icon = document.createElement('i');
        icon.className = type === 'success' ? 'fas fa-check-circle' :
            type === 'error' ? 'fas fa-exclamation-circle' :
                type === 'warning' ? 'fas fa-exclamation-triangle' :
                    'fas fa-info-circle';
        
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        
        toastContent.appendChild(icon);
        toastContent.appendChild(messageSpan);
        toast.appendChild(toastContent);
        
        // Create or get toast container
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 10000; display: flex; flex-direction: column-reverse; gap: 10px;';
            document.body.appendChild(toastContainer);
        }
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Show confirmation modal
    showConfirmModal(title, message, onConfirm, onCancel = null) {
        const modal = document.getElementById('confirmModal');
        const titleEl = document.getElementById('confirmTitle');
        const messageEl = document.getElementById('confirmMessage');
        const okBtn = document.getElementById('confirmOkBtn');
        const cancelBtn = document.getElementById('confirmCancelBtn');
        const closeBtn = document.getElementById('confirmCloseBtn');

        if (!modal || !titleEl || !messageEl || !okBtn || !cancelBtn || !closeBtn) {
            console.error('Confirmation modal elements not found');
            return;
        }

        // Set content
        titleEl.textContent = title;
        messageEl.textContent = message;

        // Clear existing event listeners by cloning elements
        const newOkBtn = okBtn.cloneNode(true);
        const newCancelBtn = cancelBtn.cloneNode(true);
        const newCloseBtn = closeBtn.cloneNode(true);

        okBtn.parentNode.replaceChild(newOkBtn, okBtn);
        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);

        // Add event listeners
        newOkBtn.addEventListener('click', () => {
            this.hideConfirmModal();
            if (onConfirm) onConfirm();
        });

        newCancelBtn.addEventListener('click', () => {
            this.hideConfirmModal();
            if (onCancel) onCancel();
        });

        newCloseBtn.addEventListener('click', () => {
            this.hideConfirmModal();
            if (onCancel) onCancel();
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideConfirmModal();
                if (onCancel) onCancel();
            }
        });

        // Show modal
        modal.style.display = 'flex';
    }

    // Hide confirmation modal
    hideConfirmModal() {
        const modal = document.getElementById('confirmModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }


    updateTaskStatus(taskId, status) {
        console.log(`Task ${taskId} status:`, status);

        // Update task status display if we have a task status modal or indicator
        const taskStatusElement = document.getElementById('taskStatus');
        if (taskStatusElement) {
            taskStatusElement.innerHTML = `
                <div class="task-status">
                    <h4>Task Status</h4>
                    <p><strong>Task ID:</strong> ${taskId}</p>
                    <p><strong>State:</strong> <span class="status-${status.state}">${status.state}</span></p>
                    <p><strong>Timestamp:</strong> ${status.timestamp || 'N/A'}</p>
                    ${status.message ? `<p><strong>Message:</strong> ${this.formatA2AMessage(status.message)}</p>` : ''}
                </div>
            `;
        }

        // Store task status for potential polling
        if (!this.taskStatuses) {
            this.taskStatuses = new Map();
        }
        this.taskStatuses.set(taskId, status);
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new AgentPlatform();

    // Make app globally available for inline event handlers
    window.app = app;

    // Add click event to sidebar header to reload page
    const sidebarHeader = document.querySelector('.sidebar-header');
    if (sidebarHeader) {
        sidebarHeader.addEventListener('click', () => {
            window.location.reload();
        });
        sidebarHeader.style.cursor = 'pointer';
    }
});
