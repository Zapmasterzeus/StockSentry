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

// Backend warmup function
async function warmupBackend() {
    try {
        console.log('Attempting to warm up backend...');
        await axios.get(`${BACKEND_URL}/health`, {
            timeout: 60000 // 60 second timeout for cold start
        });
        console.log('✓ Backend is ready');
        return true;
    } catch (error) {
        console.log('Backend warmup in progress or failed:', error.message);
        return false;
    }
}

// Warm up backend on startup
warmupBackend();

// Keep backend alive with periodic pings (every 10 minutes)
setInterval(() => {
    warmupBackend();
}, 10 * 60 * 1000);

// Routes
app.get('/', (req, res) => {
    res.render('index', { error: null });
});

app.post('/analyze', async (req, res) => {
    const { ticker } = req.body;

    if (!ticker) {
        return res.render('index', {
            error: 'Please enter a stock ticker symbol'
        });
    }

    try {
        console.log(`Analyzing ticker: ${ticker}`);

        // Show loading state and warm up backend if needed
        console.log('Ensuring backend is awake...');

        const response = await axios.post(
            `${BACKEND_URL}/analyze`,
            { ticker },
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 180000 // 3 minute timeout (includes cold start time)
            }
        );

        res.render('results', { data: response.data });
    } catch (error) {
        console.error('Analysis error:', error.response?.data || error.message);

        let errorMessage;
        if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
            errorMessage = 'Request timed out. The backend service may be starting up. Please try again in a moment.';
        } else {
            errorMessage = error.response?.data?.detail
                || error.message
                || 'Analysis failed. Please try again.';
        }

        res.render('index', { error: errorMessage });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy' });
});

// 404 handler
app.use((req, res) => {
    res.status(404).render('index', {
        error: 'Page not found'
    });
});

// Error handler
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).render('index', {
        error: 'An unexpected error occurred'
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Frontend running on port ${PORT}`);
    console.log(`Backend URL: ${BACKEND_URL}`);
});