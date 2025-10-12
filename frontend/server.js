const express = require('express');
const axios = require('axios');
const path = require('path');
const app = express();

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../public')));  // For custom CSS if needed
app.use('/charts', express.static(path.join(__dirname, '../charts')));  // Serve charts

app.get('/', (req, res) => {
    res.render('index');
});

app.post('/analyze', async (req, res) => {
    const { ticker } = req.body;
    try {
        const response = await axios.post('http://localhost:8000/analyze', 
            { ticker }, 
            { 
                headers: { 'Content-Type': 'application/json' },
                timeout: 60000 // 60 second timeout for analysis
            }
        );
        res.render('results', { data: response.data });
    } catch (error) {
        console.error('Analysis error:', error.response?.data || error.message);
        res.render('index', { 
            error: error.response?.data?.detail || error.message || 'Analysis failed' 
        });
    }
});

app.listen(3000, () => console.log('Frontend running on http://localhost:3000'));