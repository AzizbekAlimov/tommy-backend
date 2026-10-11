require('dotenv').config();
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fetch = (...args) => import('node-fetch').then(({ default: f }) => f(...args));
const FormData = require('form-data');

const app = express();

app.use(cors({ origin: '*', methods: ['POST', 'GET'] }));

const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 5 * 1024 * 1024 }
});

const BOT_TOKEN = process.env.BOT_TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;

app.get('/', (req, res) => {
    res.send('✅ Tommy Feedback Backend is running!');
});

app.post('/send-feedback', upload.single('photo'), async (req, res) => {
    try {
        if (!req.file) return res.status(400).json({ ok: false, description: 'Photo kerak!' });
        const caption = req.body.caption || '';
        if (!caption) return res.status(400).json({ ok: false, description: 'Caption kerak!' });

        const form = new FormData();
        form.append('chat_id', CHANNEL_ID);
        form.append('caption', caption);
        form.append('photo', req.file.buffer, {
            filename: 'screenshot.jpg',
            contentType: req.file.mimetype
        });

        const tgRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
            method: 'POST',
            body: form,
            headers: form.getHeaders()
        });

        const result = await tgRes.json();
        return res.status(tgRes.status).json(result);
    } catch (err) {
        console.error('Server xatosi:', err);
        return res.status(500).json({ ok: false, description: 'Server xatosi: ' + err.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log('✅ Server ishga tushdi! Port: ' + PORT);
});
