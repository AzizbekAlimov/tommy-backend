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

/* ============================================================
   🤖 GEMINI AI — rasmni tahlil qilish
   ============================================================ */
async function analyzeWithAI(imageBuffer, mimeType) {
    if (!GEMINI_API_KEY) {
        console.log('⚠️ GEMINI_API_KEY yo\'q, AI o\'chirilgan');
        return null;
    }

    try {
        const base64Image = imageBuffer.toString('base64');

        const prompt = `You are a PUBG Mobile screenshot analyzer. Carefully analyze this screenshot and extract information. Return ONLY a valid JSON object with no markdown, no extra text.

{
  "player_id": "11-digit UID (look in top-left corner or profile section) or null",
  "classic_rank": "Bronze/Silver/Gold/Platinum/Diamond/Crown/Ace/Ace Master/Ace Dominator/Conqueror or null",
  "ultimate_rank": "Vanguard/Exceed/Supreme/Peerless/Legend or null",
  "kills": "number of kills shown in match result or null",
  "map": "map name or null"
}

RULES:
- player_id: exactly 11 digits, starts with 5 or 6
- classic_rank: look for rank badge and text (e.g. "Conqueror", "Ace Master")
- ultimate_rank: look for Ultimate Royale section (e.g. "Legend", "Supreme")
- kills: number next to skull icon in match stats
- If not visible, set to null
- Return ONLY the JSON, no other text`;

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
            console.error('❌ AI xato:', JSON.stringify(result).substring(0, 300));
            return null;
        }

        let text = result.candidates[0].content.parts[0].text.trim();
        text = text.replace(/```json/g, '').replace(/```/g, '').trim();

        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            console.error('❌ JSON topilmadi:', text);
            return null;
        }

        const data = JSON.parse(jsonMatch[0]);
        console.log('✅ AI natijasi:', data);
        return data;

    } catch (err) {
        console.error('❌ AI xatosi:', err.message);
        return null;
    }
}

/* ============================================================
   Health check
   ============================================================ */
app.get('/', (req, res) => {
    res.send('✅ Tommy Backend with AI is running!');
});

/* ============================================================
   📤 /send-feedback — rasmni AI bilan tahlil qilib yuborish
   ============================================================ */
app.post('/send-feedback', upload.single('photo'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ ok: false, description: 'Photo kerak!' });
        }

        const frontendCaption = req.body.caption || '';

        console.log('📸 Rasm qabul qilindi, AI tahlil boshlanmoqda...');

        // 🤖 AI ORQALI RASMNI TAHLIL QILISH
        const aiData = await analyzeWithAI(req.file.buffer, req.file.mimetype);

        let finalCaption;

        if (aiData) {
            // AI natijalarini olish
            let playerId = aiData.player_id || '';
            const classicRank = aiData.classic_rank || 'Unknown';
            const ultimateRank = aiData.ultimate_rank || 'Unknown';
            const kills = aiData.kills || '0';

            // ID masking: 52412345619 -> 524***19
            let hiddenId = 'Unknown';
            if (playerId && String(playerId).length === 11) {
                playerId = String(playerId);
                hiddenId = playerId.substring(0, 3) + '***' + playerId.substring(9);
            } else if (playerId) {
                hiddenId = String(playerId);
            }

            // Owner — frontend'dan olish
            const ownerLine = frontendCaption.split('\n')[0] || '👤 OWNER: Unknown';
            const ownerName = ownerLine.replace('👤 OWNER: ', '').trim();

            // Vaqt
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, '0');
            const mm = String(now.getMinutes()).padStart(2, '0');
            const dd = String(now.getDate()).padStart(2, '0');
            const mo = String(now.getMonth() + 1).padStart(2, '0');
            const yy = now.getFullYear();
            const timeStr = `${hh}:${mm}  ${dd}.${mo}.${yy}`;

            finalCaption =
                `👤 OWNER: ${ownerName}\n` +
                `🎮 Player ID: ${hiddenId}\n` +
                `🏆 CLASSIC RANK: ${classicRank}\n` +
                `🏆 ULTIMATE ROYALE RANK: ${ultimateRank}\n` +
                `🕒 TIME: ${timeStr}\n` +
                `💀 KILL: ${kills}\n` +
                `\n` +
                `👤 OWNER: @Tommy_1727 ✅`;

            console.log('✅ AI caption yasaldi');

        } else {
            // AI ishlamadi — frontend'dan kelgan caption ishlatiladi
            console.log('⚠️ AI ishlamadi, frontend captioni ishlatiladi');
            finalCaption = frontendCaption;
        }

        // Telegramga yuborish
        const form = new FormData();
        form.append('chat_id', CHANNEL_ID);
        form.append('caption', finalCaption);
        form.append('photo', req.file.buffer, {
            filename: 'screenshot.jpg',
            contentType: req.file.mimetype
        });

        const tgRes = await fetch(
            `https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`,
            { method: 'POST', body: form, headers: form.getHeaders() }
        );

        const result = await tgRes.json();

        return res.status(tgRes.status).json({
            ok: result.ok,
            description: result.description,
            ai_data: aiData
        });

    } catch (err) {
        console.error('❌ Server xatosi:', err);
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
