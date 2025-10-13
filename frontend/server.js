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

// Static files - serve from 'public' folder in frontend directory
app.use(express.static(path.join(__dirname, 'public')));

// Backend API URL - use environment variable for production
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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

        const response = await axios.post(
            `${BACKEND_URL}/analyze`,
            { ticker },
            {
                headers: { 'Content-Type': 'application/json' },
                timeout: 120000 // 2 minute timeout for analysis
            }
        );

        res.render('results', { data: response.data });
    } catch (error) {
        console.error('Analysis error:', error.response?.data || error.message);

        const errorMessage = error.response?.data?.detail
            || error.message
            || 'Analysis failed. Please try again.';

        res.render('index', { error: errorMessage });
    }
});

// Health check endpoint for Render
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