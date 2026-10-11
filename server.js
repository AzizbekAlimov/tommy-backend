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
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

app.get('/', (req, res) => {
    res.send('✅ Tommy Feedback Backend is running with AI!');
});

/* ============================================================
   🤖 GEMINI AI — rasmni tahlil qilish
   ============================================================ */
async function analyzeScreenshotWithAI(imageBuffer, mimeType) {
    try {
        const base64Image = imageBuffer.toString('base64');

        const prompt = `You are a PUBG Mobile screenshot analyzer. Analyze this screenshot carefully and extract the following information in STRICT JSON format ONLY (no extra text, no markdown):

{
  "player_id": "11-digit UID or null if not visible",
  "classic_rank": "Bronze/Silver/Gold/Platinum/Diamond/Crown/Ace/Ace Master/Ace Dominator/Conqueror or null",
  "ultimate_rank": "Vanguard/Exceed/Supreme/Peerless/Legend or null",
  "kills": "number or null",
  "map": "map name or null"
}

RULES:
- player_id must be exactly 11 digits starting with 5 or 6
- Look for UID in top-left corner or in profile section
- Look for rank badges and text labels
- kills should be the number shown in the match result (number next to kill icon)
- Return ONLY the JSON object, nothing else`;

        const response = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_KEY}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{
                        parts: [
                            { text: prompt },
                            {
                                inline_data: {
                                    mime_type: mimeType || 'image/jpeg',
                                    data: base64Image
                                }
                            }
                        ]
                    }],
                    generationConfig: {
                        temperature: 0.1,
                        maxOutputTokens: 500
                    }
                })
            }
        );

        const result = await response.json();

        if (!result.candidates || !result.candidates[0]) {
            console.error('AI error:', JSON.stringify(result));
            return null;
        }

        let text = result.candidates[0].content.parts[0].text.trim();

        // Markdown kod bloklarini tozalash
        text = text.replace(/```json/g, '').replace(/```/g, '').trim();

        // JSON ni topish
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            console.error('No JSON found in AI response:', text);
            return null;
        }

        const data = JSON.parse(jsonMatch[0]);
        console.log('✅ AI tahlil natijasi:', data);
        return data;

    } catch (err) {
        console.error('AI xatosi:', err.message);
        return null;
    }
}

/* ============================================================
   📤 /send-feedback
   ============================================================ */
app.post('/send-feedback', upload.single('photo'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ ok: false, description: 'Photo kerak!' });
        }

        // AI orqali rasmni tahlil qilish
        const aiData = await analyzeScreenshotWithAI(req.file.buffer, req.file.mimetype);

        const ownerInfo = req.body.owner || 'Unknown';
        const ownerUsername = req.body.owner_username || '';

        // AI natijalarini olish (yoki default qiymatlar)
        let playerId = aiData?.player_id || req.body.player_id || '';
        const classicRank = aiData?.classic_rank || req.body.classic_rank || 'Unknown';
        const ultimateRank = aiData?.ultimate_rank || req.body.ultimate_rank || 'Unknown';
        const kills = aiData?.kills || req.body.kills || '0';

        // Player ID ni maskalash
        let hiddenId = 'Unknown';
        if (playerId && playerId.length === 11) {
            hiddenId = playerId.substring(0, 3) + '***' + playerId.substring(9);
        } else if (playerId) {
            hiddenId = playerId;
        }

        // Vaqt
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const year = now.getFullYear();
        const timeStr = `${hours}:${minutes}  ${day}.${month}.${year}`;

        // Caption yasash
        const caption =
            `👤 OWNER: ${ownerInfo}\n` +
            `🎮 Player ID: ${hiddenId}\n` +
            `🏆 CLASSIC RANK: ${classicRank}\n` +
            `🏆 ULTIMATE ROYALE RANK: ${ultimateRank}\n` +
            `🕒 TIME: ${timeStr}\n` +
            `💀 KILL: ${kills}\n` +
            `\n` +
            `👤 OWNER: @Tommy_1727 ✅`;

        // Telegramga yuborish
        const form = new FormData();
        form.append('chat_id', CHANNEL_ID);
        form.append('caption', caption);
        form.append('photo', req.file.buffer, {
            filename: 'screenshot.jpg',
            contentType: req.file.mimetype
        });

        const tgRes = await fetch(
            `https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`,
            { method: 'POST', body: form, headers: form.getHeaders() }
        );

        const tgResult = await tgRes.json();

        // Natijani qaytarish
        return res.status(tgRes.status).json({
            ok: tgResult.ok,
            description: tgResult.description,
            ai_data: aiData
        });

    } catch (err) {
        console.error('Server xatosi:', err);
        return res.status(500).json({
            ok: false,
            description: 'Server xatosi: ' + err.message
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ Server ishga tushdi! Port:', PORT);
    console.log('📢 Kanal:', CHANNEL_ID);
    console.log('🤖 Gemini AI:', GEMINI_API_KEY ? 'Ulandi ✅' : 'Yo\'q ❌');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
});
