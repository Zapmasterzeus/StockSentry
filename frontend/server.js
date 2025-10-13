const express = require('express');
const axios = require('axios');
const path = require('path');
const app = express();

// View engine setup
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Backend API URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Backend status tracking
let backendStatus = {
    isAwake: false,
    lastCheck: null,
    lastError: null
};

// Backend warmup function with better status tracking
async function warmupBackend() {
    try {
        console.log('Checking backend health...');
        const response = await axios.get(`${BACKEND_URL}/health`, {
            timeout: 60000 // 60 second timeout for cold start
        });

        backendStatus = {
            isAwake: true,
            lastCheck: new Date(),
            lastError: null
        };

        console.log('✓ Backend is ready:', response.data.message);
        return true;
    } catch (error) {
        backendStatus = {
            isAwake: false,
            lastCheck: new Date(),
            lastError: error.message
        };

        console.log('Backend not ready:', error.message);
        return false;
    }
}

// Warm up backend on startup (async, don't block server start)
warmupBackend().catch(err => console.log('Initial warmup queued'));

// Keep backend alive with periodic pings (every 12 minutes to stay under 15min threshold)
setInterval(() => {
    warmupBackend();
}, 12 * 60 * 1000);

// Routes
app.get('/', (req, res) => {
    res.render('index', {
        error: null,
        backendStatus: backendStatus.isAwake ? 'ready' : 'sleeping'
    });
});

// Backend status endpoint for frontend to check
app.get('/backend-status', (req, res) => {
    res.json({
        isAwake: backendStatus.isAwake,
        lastCheck: backendStatus.lastCheck,
        message: backendStatus.isAwake
            ? 'Backend is ready'
            : 'Backend is starting up (may take 30-60 seconds)'
    });
});

app.post('/analyze', async (req, res) => {
    const { ticker } = req.body;

    if (!ticker) {
        return res.render('index', {
            error: 'Please enter a stock ticker symbol',
            backendStatus: backendStatus.isAwake ? 'ready' : 'sleeping'
        });
    }

    try {
        console.log(`Analyzing ticker: ${ticker}`);

        // If backend is asleep, pre-warm it
        if (!backendStatus.isAwake) {
            console.log('Backend appears to be sleeping, attempting to wake...');
            await warmupBackend();
        }

        const response = await axios.post(
            `${BACKEND_URL}/analyze`,
            { ticker },
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 180000 // 3 minute timeout (includes cold start time)
            }
        );

        // Mark backend as awake after successful request
        backendStatus.isAwake = true;

        res.render('results', { data: response.data });
    } catch (error) {
        console.error('Analysis error:', error.response?.data || error.message);

        let errorMessage;
        if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
            errorMessage = 'Request timed out. The backend service is waking up from sleep. Please wait 30 seconds and try again.';
        } else if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
            errorMessage = 'Cannot connect to backend service. Please try again in a moment.';
        } else {
            errorMessage = error.response?.data?.detail
                || error.message
                || 'Analysis failed. Please try again.';
        }

        res.render('index', {
            error: errorMessage,
            backendStatus: 'sleeping'
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'healthy',
        backend: backendStatus.isAwake ? 'connected' : 'disconnected'
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).render('index', {
        error: 'Page not found',
        backendStatus: backendStatus.isAwake ? 'ready' : 'sleeping'
    });
});

// Error handler
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).render('index', {
        error: 'An unexpected error occurred',
        backendStatus: backendStatus.isAwake ? 'ready' : 'sleeping'
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Frontend running on port ${PORT}`);
    console.log(`Backend URL: ${BACKEND_URL}`);
    console.log('Backend warmup initiated...');
});