import express, { Request, Response, NextFunction } from 'express';
import http from 'http';
import path from 'path';
import fs from 'fs';
import querystring from 'querystring';
import { WebSocketServer, WebSocket } from 'ws';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from "@google/genai";

const app = express();
const server = http.createServer(app);
const PORT = 3000;

// Set up upload directories
fs.mkdirSync(path.join(process.cwd(), 'public/uploads'), { recursive: true });
fs.mkdirSync(path.join(process.cwd(), 'dist/uploads'), { recursive: true });

app.use(express.json());
app.use('/uploads', express.static(path.join(process.cwd(), 'public/uploads')));
app.use('/uploads', express.static(path.join(process.cwd(), 'dist/uploads')));

// --- In-Memory Mock Database ---
interface UserProfile {
  id: number;
  tg_id: number;
  nickname: string;
  age: number;
  gender: string;
  avatar_url?: string;
  bio?: string;
  is_premium: boolean;
  chosen_emoji?: string;
  likes: number;
  dislikes: number;
  reputation_percent: number;
  total_chat_seconds: number;
  is_admin: boolean;
  is_banned: boolean;
}

interface ChatSession {
  id: number;
  user_a_id: number;
  user_b_id: number;
  started_at: Date;
  ended_at?: Date;
  ended_reason?: string;
}

interface Message {
  id: number;
  chat_id: number;
  sender_id: number;
  type: string;
  content_url_or_text: string;
  created_at: Date;
}

interface Report {
  id: number;
  chat_id: number;
  reporter_id: number;
  reported_id: number;
  category: string;
  status: string;
}

interface Referral {
  id: number;
  code: string;
  created_by_admin_id: number;
  uses_count: number;
}

const users = new Map<number, UserProfile>();
const chats = new Map<number, ChatSession>();
const activeChats = new Map<number, ChatSession>();
const messages: Message[] = [];
const blacklist = new Map<number, Set<number>>();
const reports: Report[] = [];
const referrals: Referral[] = [];

// Prepopulate bots/mock profiles
const bots: UserProfile[] = [
  { id: 11111111, tg_id: 11111111, nickname: 'NEO_99', age: 24, gender: 'male', is_premium: true, chosen_emoji: '💻', likes: 88, dislikes: 4, reputation_percent: 95, total_chat_seconds: 12500, is_admin: false, is_banned: false },
  { id: 22222222, tg_id: 22222222, nickname: 'TRINITY', age: 22, gender: 'female', is_premium: true, chosen_emoji: '🕶️', likes: 150, dislikes: 2, reputation_percent: 98, total_chat_seconds: 22400, is_admin: false, is_banned: false },
  { id: 33333333, tg_id: 33333333, nickname: 'MORPHEUS', age: 45, gender: 'male', is_premium: false, likes: 40, dislikes: 5, reputation_percent: 88, total_chat_seconds: 5400, is_admin: false, is_banned: false },
  { id: 44444444, tg_id: 44444444, nickname: 'CYPHER', age: 38, gender: 'male', is_premium: false, likes: 5, dislikes: 42, reputation_percent: 10, total_chat_seconds: 120, is_admin: false, is_banned: false },
  { id: 55555555, tg_id: 55555555, nickname: 'ORACLE', age: 60, gender: 'female', is_premium: true, chosen_emoji: '🔮', likes: 300, dislikes: 0, reputation_percent: 100, total_chat_seconds: 88900, is_admin: false, is_banned: false },
  { id: 66666666, tg_id: 66666666, nickname: 'AGENT_SMITH', age: 35, gender: 'male', is_premium: true, chosen_emoji: '👔', likes: 10, dislikes: 99, reputation_percent: 9, total_chat_seconds: 15000, is_admin: false, is_banned: false }
];

bots.forEach(b => users.set(b.id, b));

// Prepopulate some referrals
referrals.push({ id: 1, code: 'CYBERPUNK2026', created_by_admin_id: 11111111, uses_count: 42 });

// --- WebSocket Server Channel Subscriptions ---
const wss = new WebSocketServer({ noServer: true });
const channelSubscriptions = new Map<string, Set<WebSocket>>();

wss.on('connection', (ws: WebSocket) => {
  console.log('[WS] Connection opened');
  
  ws.on('message', (message: string) => {
    try {
      const data = JSON.parse(message);
      if (data.type === 'subscribe' && data.channel) {
        if (!channelSubscriptions.has(data.channel)) {
          channelSubscriptions.set(data.channel, new Set());
        }
        channelSubscriptions.get(data.channel)!.add(ws);
        console.log(`[WS] Subscribed socket to channel: ${data.channel}`);
      } else if (data.type === 'unsubscribe' && data.channel) {
        channelSubscriptions.get(data.channel)?.delete(ws);
        console.log(`[WS] Unsubscribed socket from channel: ${data.channel}`);
      }
    } catch (err) {
      console.error('[WS] Message error:', err);
    }
  });

  ws.on('close', () => {
    console.log('[WS] Connection closed');
    for (const [_, subs] of channelSubscriptions.entries()) {
      subs.delete(ws);
    }
  });
});

// Multiplex upgrade on server
server.on('upgrade', (request, socket, head) => {
  if (request.url === '/ws') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  } else {
    socket.destroy();
  }
});

function publishToChannel(channel: string, messageData: any) {
  const subs = channelSubscriptions.get(channel);
  if (subs) {
    const payload = JSON.stringify({
      type: 'publication',
      channel,
      data: messageData
    });
    for (const ws of subs) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(payload);
      }
    }
  }
}

// --- Gemini API Setup ---
let ai: GoogleGenAI | null = null;
if (process.env.GEMINI_API_KEY) {
  ai = new GoogleGenAI({
    apiKey: process.env.GEMINI_API_KEY,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build'
      }
    }
  });
}

async function generateGeminiBotReply(userMessage: string, bot: any, user: any): Promise<string> {
  if (!ai) return getPredefinedReply(userMessage, bot);
  try {
    const prompt = `You are a user named ${bot.nickname} (age ${bot.age}, gender ${bot.gender}) in an anonymous chat room.
You are talking to another user who is ${user.gender} (age ${user.age}) named ${user.nickname}.
Their biography is: "${user.bio || 'Not specified'}".
Keep your tone casual, interactive, concise (maximum 1-2 short sentences, like a real chat message), and responsive. Use conversational style, slang, or emojis if appropriate.
Here is the message they just sent you: "${userMessage}"
Generate your response now:`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        temperature: 1.0,
      }
    });
    
    return response.text || getPredefinedReply(userMessage, bot);
  } catch (err) {
    console.error('Gemini API call failed, falling back:', err);
    return getPredefinedReply(userMessage, bot);
  }
}

function getPredefinedReply(msg: string, bot: any): string {
  const lower = msg.toLowerCase();
  
  if (bot.nickname === 'NEO_99') {
    if (lower.includes('hello') || lower.includes('hi') || lower.includes('привет') || lower.includes('hey')) {
      return "Whoa. Hello. Are you looking for the Matrix, or did you just stumble into this terminal?";
    }
    if (lower.includes('how are you') || lower.includes('как дела')) {
      return "Searching for answers. The agents are watching, but my connection is still secure.";
    }
    return "I know kung fu. What is your purpose in this cyber room?";
  }
  
  if (bot.nickname === 'TRINITY') {
    if (lower.includes('hello') || lower.includes('hi') || lower.includes('привет') || lower.includes('hey')) {
      return "Hello. I was looking for you. Keep your eyes open.";
    }
    return "We don't have much time. Focus on the objective.";
  }
  
  if (bot.nickname === 'AGENT_SMITH') {
    if (lower.includes('hello') || lower.includes('hi') || lower.includes('привет') || lower.includes('hey')) {
      return "Mr. Anderson... or whoever you are. We've been expecting you.";
    }
    return "It is inevitable. You cannot escape your destiny.";
  }
  
  const options = [
    "Connection stable. What's on your mind?",
    "Interesting telemetry. Tell me more about yourself.",
    "System processing. Let's chat about tech or movies.",
    "Are you premium yet? The VIP protocol is where the magic happens.",
    "Anon chat feels like the old IRC days. Love it here.",
    "Just scanning the database. What topics do you like?"
  ];
  return options[Math.floor(Math.random() * options.length)];
}

// --- Express Middleware for Telegram Auth ---
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: number;
        username?: string;
        first_name?: string;
        last_name?: string;
      };
    }
  }
}

function authenticateTelegram(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('tma ')) {
    return res.status(401).json({ detail: 'Missing Telegram authorization' });
  }
  
  const initData = authHeader.substring(4); // Remove 'tma '
  const parsed = querystring.parse(initData);
  
  if (!parsed.user) {
    return res.status(401).json({ detail: 'Invalid Telegram authorization' });
  }
  
  try {
    const userData = JSON.parse(decodeURIComponent(parsed.user as string));
    req.user = userData;
    next();
  } catch (err) {
    return res.status(401).json({ detail: 'Invalid user data in initData' });
  }
}

// --- Matchmaker Queue ---
interface SearchFilter {
  find_gender: string;
  age_from: number;
  age_to: number;
  vip_only: boolean;
}

interface WaitingUser {
  userId: number;
  filters: SearchFilter;
  timestamp: number;
}

const waitingQueue: WaitingUser[] = [];

// Clean up old queued users periodically
setInterval(() => {
  const now = Date.now();
  for (let i = waitingQueue.length - 1; i >= 0; i--) {
    if (now - waitingQueue[i].timestamp > 60000) {
      waitingQueue.splice(i, 1);
    }
  }
}, 10000);

// --- API Routing ---

// 1. User Endpoints
app.get('/api/users/me', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  let profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  
  if (!profile) {
    return res.status(404).json({ detail: 'User not found. Complete onboarding first.' });
  }
  
  if (profile.is_banned) {
    return res.status(403).json({ detail: 'Your account has been banned.' });
  }
  
  res.json({
    id: profile.id,
    tg_id: profile.tg_id,
    nickname: profile.nickname,
    age: profile.age,
    gender: profile.gender,
    avatar_url: profile.avatar_url || null,
    bio: profile.bio || null,
    is_premium: profile.is_premium,
    chosen_emoji: profile.chosen_emoji || null,
    likes: profile.likes,
    dislikes: profile.dislikes,
    reputation_percent: profile.reputation_percent,
    total_chat_seconds: profile.total_chat_seconds,
    is_admin: profile.is_admin,
    is_banned: profile.is_banned
  });
});

app.post('/api/users/onboarding', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const data = req.body;
  
  if (!data.agreed_to_rules) {
    return res.status(400).json({ detail: 'You must agree to the rules (18+)' });
  }
  
  let profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  
  // Verify referral code to grant premium/VIP access
  let isVipByReferral = false;
  if (data.referral_code) {
    const codeClean = data.referral_code.trim().toUpperCase();
    const refRecord = referrals.find(r => r.code.toUpperCase() === codeClean);
    if (refRecord) {
      refRecord.uses_count += 1;
      isVipByReferral = true;
    }
  }

  if (!profile) {
    const id = Math.floor(10000000 + Math.random() * 90000000);
    profile = {
      id,
      tg_id: tgUser.id,
      nickname: data.nickname,
      age: data.age,
      gender: data.gender,
      avatar_url: data.avatar_url || '',
      bio: data.bio || '',
      is_premium: isVipByReferral,
      likes: 0,
      dislikes: 0,
      reputation_percent: 100,
      total_chat_seconds: 0,
      is_admin: tgUser.id === 12345678 || String(tgUser.id).startsWith('1'), // Simple mock admin logic
      is_banned: false
    };
    users.set(id, profile);
  } else {
    profile.nickname = data.nickname;
    profile.age = data.age;
    profile.gender = data.gender;
    profile.avatar_url = data.avatar_url || profile.avatar_url;
    profile.bio = data.bio || profile.bio;
    if (isVipByReferral) {
      profile.is_premium = true;
    }
  }
  
  res.json({
    id: profile.id,
    tg_id: profile.tg_id,
    nickname: profile.nickname,
    age: profile.age,
    gender: profile.gender,
    avatar_url: profile.avatar_url || null,
    bio: profile.bio || null,
    is_premium: profile.is_premium,
    chosen_emoji: profile.chosen_emoji || null,
    likes: profile.likes,
    dislikes: profile.dislikes,
    reputation_percent: profile.reputation_percent,
    total_chat_seconds: profile.total_chat_seconds,
    is_admin: profile.is_admin,
    is_banned: profile.is_banned
  });
});

app.patch('/api/users/me', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const data = req.body;
  
  let profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  if (data.chosen_emoji !== undefined) {
    if (!profile.is_premium && data.chosen_emoji) {
      return res.status(403).json({ detail: 'Emoji badges require Premium' });
    }
    profile.chosen_emoji = data.chosen_emoji;
  }
  
  if (data.nickname) profile.nickname = data.nickname;
  if (data.age) profile.age = data.age;
  if (data.gender) profile.gender = data.gender;
  if (data.avatar_url !== undefined) profile.avatar_url = data.avatar_url;
  if (data.bio !== undefined) profile.bio = data.bio;
  
  res.json({
    id: profile.id,
    tg_id: profile.tg_id,
    nickname: profile.nickname,
    age: profile.age,
    gender: profile.gender,
    avatar_url: profile.avatar_url || null,
    bio: profile.bio || null,
    is_premium: profile.is_premium,
    chosen_emoji: profile.chosen_emoji || null,
    likes: profile.likes,
    dislikes: profile.dislikes,
    reputation_percent: profile.reputation_percent,
    total_chat_seconds: profile.total_chat_seconds,
    is_admin: profile.is_admin,
    is_banned: profile.is_banned
  });
});

app.get('/api/users/leaderboard', authenticateTelegram, (req, res) => {
  const list = Array.from(users.values())
    .sort((a, b) => b.total_chat_seconds - a.total_chat_seconds)
    .slice(0, 100)
    .map((u, i) => ({
      rank: i + 1,
      nickname: u.nickname,
      total_chat_seconds: u.total_chat_seconds,
      is_premium: u.is_premium,
      chosen_emoji: u.chosen_emoji || null,
      likes: u.likes,
      dislikes: u.dislikes,
      reputation_percent: u.reputation_percent
    }));
  res.json({ leaderboard: list });
});

app.post('/api/users/blacklist', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { blocked_user_id } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  if (!blacklist.has(profile.id)) {
    blacklist.set(profile.id, new Set());
  }
  blacklist.get(profile.id)!.add(blocked_user_id);
  res.json({ status: 'ok' });
});

app.delete('/api/users/blacklist/:blockedUserId', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const blockedUserId = parseInt(req.params.blockedUserId);
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  if (blacklist.has(profile.id)) {
    blacklist.get(profile.id)!.delete(blockedUserId);
  }
  res.json({ status: 'ok' });
});

// 2. Chat Endpoints
const gamesDb = {
  pd: {
    ru: [
      "ПРАВДА ❓: Какая твоя самая неловкая привычка в одиночестве?",
      "ПРАВДА ❓: В кого ты был тайно влюблен в школе?",
      "ПРАВДА ❓: Какую самую большую ложь ты когда-либо говорил?",
      "ПРАВДА ❓: О чем ты больше всего сожалеешь в жизни?",
      "ДЕЙСТВИЕ ⚡: Отправь собеседнику свое самое смешное селфи прямо сейчас!",
      "ДЕЙСТВИЕ ⚡: Напиши своему бывшему/бывшей «Я соскучился» и пришли скриншот!",
      "ДЕЙСТВИЕ ⚡: Спой куплет любимой песни и запиши аудиосообщение (или напиши текст капсом)!",
      "ДЕЙСТВИЕ ⚡: Расскажи анекдот или самую нелепую шутку, которую знаешь!"
    ],
    en: [
      "TRUTH ❓: What is your most embarrassing habit when you are alone?",
      "TRUTH ❓: Who was your secret crush in school?",
      "TRUTH ❓: What is the biggest lie you have ever told?",
      "TRUTH ❓: What is your biggest regret in life?",
      "DARE ⚡: Send your chat partner your funniest selfie right now!",
      "DARE ⚡: Text your ex 'I miss you' and show a screenshot (or describe their response)!",
      "DARE ⚡: Sing a line of your favorite song and describe it in ALL CAPS!",
      "DARE ⚡: Tell the most ridiculous joke you know right now!"
    ],
    uz: [
      "HAQIQAT ❓: Yolg'iz qolganingizda eng uyatli odatingiz nima?",
      "HAQIQAT ❓: Maktabda kimni yashirincha yoqtirganingizni ayting?",
      "HAQIQAT ❓: Hayotingizda aytgan eng katta yolg'oningiz nima?",
      "HAQIQAT ❓: Hayotda qilgan eng katta afsusingiz nima?",
      "VAZIFA ⚡: Sherigingizga hozirning o'zida eng kulgili rasm/selfi yuboring!",
      "VAZIFA ⚡: Sobiq sevganingizga 'Seni sog'indim' deb yozing va javobini sherigingizga aytib bering!",
      "VAZIFA ⚡: Sevimli qo'shig'ingizdan bir qatorni chatga KATTA HARFLAR bilan yozib bering!",
      "VAZIFA ⚡: O'zingiz bilgan eng bema'ni yoki kulgili latifani aytib bering!"
    ]
  },
  never: {
    ru: [
      "Я НИКОГДА НЕ 🙊: засыпал на уроках или лекциях.",
      "Я НИКОГДА НЕ 🙊: врал про свой возраст, чтобы казаться старше.",
      "Я НИКОГДА НЕ 🙊: отправлял сообщение не тому человеку и очень жалел об этом.",
      "Я НИКОГДА НЕ 🙊: ел пиццу с ананасами (и мне это нравилось).",
      "Я НИКОГДА НЕ 🙊: плакал во время просмотра мультфильмов.",
      "Я НИКОГДА НЕ 🙊: гуглил себя в интернете.",
      "Я НИКОГДА НЕ 🙊: подсматривал в чувой телефон в метро.",
      "Я НИКОГДА НЕ 🙊: забывал имя человека сразу после знакомства."
    ],
    en: [
      "NEVER HAVE I EVER 🙊: fallen asleep in class or during a lecture.",
      "NEVER HAVE I EVER 🙊: lied about my age to appear older.",
      "NEVER HAVE I EVER 🙊: sent a message to the wrong person and deeply regretted it.",
      "NEVER HAVE I EVER 🙊: eaten pineapple pizza (and secretly liked it).",
      "NEVER HAVE I EVER 🙊: cried while watching an animated movie.",
      "NEVER HAVE I EVER 🙊: googled my own name online.",
      "NEVER HAVE I EVER 🙊: snooped on someone's phone in public transport.",
      "NEVER HAVE I EVER 🙊: forgotten someone's name immediately after meeting them."
    ],
    uz: [
      "MEN HECH QACHON 🙊: darsda yoki ma'ruzada uxlab qolmaganman.",
      "MEN HECH QACHON 🙊: yoshim haqida kattaroq ko'rinish uchun yolg'on gapirmaganman.",
      "MEN HECH QACHON 🙊: xabarni noto'g'ri odamga yuborib, pushaymon bo'lmaganman.",
      "MEN HECH QACHON 🙊: ananasli pitsa yemaganman (va uni yaxshi ko'rmaganman).",
      "MEN HECH QACHON 🙊: multfilm tomosha qilayotganda yig'lamaganman.",
      "MEN HECH QACHON 🙊: o'z ismimni internetda qidirib ko'rmaganman.",
      "MEN HECH QACHON 🙊: jamoat transportida boshqalarning telefoniga qaramaganman.",
      "MEN HECH QACHON 🙊: tanishgan zahoti odamning ismini unutib qo'ymaganman."
    ]
  }
};

app.post('/api/chat/search', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const filters: SearchFilter = {
    find_gender: req.body.find_gender || 'any',
    age_from: req.body.age_from || 18,
    age_to: req.body.age_to || 99,
    vip_only: !!req.body.vip_only
  };
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'Complete onboarding first' });
  if (profile.is_banned) return res.status(403).json({ detail: 'Account banned' });
  
  // 1. Audit Report Constraint: No concurrent active chats allowed
  const alreadyInChat = Array.from(activeChats.values()).find(
    c => c.user_a_id === profile.id || c.user_b_id === profile.id
  );
  if (alreadyInChat) {
    return res.status(400).json({ detail: 'You already have an active chat session. End it first.' });
  }

  if (filters.find_gender !== 'any' && !profile.is_premium) {
    return res.status(403).json({ detail: 'Gender filter requires Premium subscription' });
  }
  if (filters.vip_only && !profile.is_premium) {
    return res.status(403).json({ detail: 'VIP rooms require Premium' });
  }

  const reqTopic = req.body.topics?.[0] || 'topic_chat';
  const reqChatLang = req.body.chat_lang || 'ru';

  // Find matches in queue
  const myBlacklist = blacklist.get(profile.id) || new Set();
  const queueIndex = waitingQueue.findIndex(waiter => {
    if (waiter.userId === profile.id) return false;
    
    const waiterProfile = users.get(waiter.userId);
    if (!waiterProfile) return false;
    
    // Blacklist check
    const waiterBlacklist = blacklist.get(waiterProfile.id) || new Set();
    if (myBlacklist.has(waiterProfile.id) || waiterBlacklist.has(profile.id)) return false;
    
    // Gender constraints match
    if (filters.find_gender !== 'any' && waiterProfile.gender !== filters.find_gender) return false;
    if (waiter.filters.find_gender !== 'any' && profile.gender !== waiter.filters.find_gender) return false;
    
    // Age constraints match
    if (profile.age < waiter.filters.age_from || profile.age > waiter.filters.age_to) return false;
    if (waiterProfile.age < filters.age_from || waiterProfile.age > filters.age_to) return false;
    
    return true;
  });

  if (queueIndex !== -1) {
    const partner = waitingQueue.splice(queueIndex, 1)[0];
    const partnerProfile = users.get(partner.userId)!;
    
    const chatId = Math.floor(100000 + Math.random() * 900000);
    const session: ChatSession = {
      id: chatId,
      user_a_id: profile.id,
      user_b_id: partnerProfile.id,
      started_at: new Date(),
      topic: reqTopic,
      chat_lang: reqChatLang
    };
    
    chats.set(chatId, session);
    activeChats.set(chatId, session);
    
    // Notify partner socket
    publishToChannel(`waiting:${partnerProfile.id}`, {
      event: 'matched',
      room_key: `room_${chatId}`,
      channel: `chat:${chatId}`,
      token: 'mock_token',
      chat_id: chatId
    });
    
    return res.json({
      status: 'matched',
      room_key: `room_${chatId}`,
      channel: `chat:${chatId}`,
      token: 'mock_token',
      chat_id: chatId,
      partner: {
        id: partnerProfile.id,
        nickname: partnerProfile.nickname,
        age: partnerProfile.age,
        gender: partnerProfile.gender,
        is_premium: partnerProfile.is_premium,
        chosen_emoji: partnerProfile.chosen_emoji || null,
        likes: partnerProfile.likes,
        dislikes: partnerProfile.dislikes,
        reputation_percent: partnerProfile.reputation_percent
      }
    });
  }

  // Queue up
  const alreadyQueued = waitingQueue.findIndex(q => q.userId === profile.id);
  if (alreadyQueued !== -1) {
    waitingQueue.splice(alreadyQueued, 1);
  }
  
  waitingQueue.push({
    userId: profile.id,
    filters,
    timestamp: Date.now()
  });

  // Automatically pair with a cool mock bot in 3 seconds to keep things fully interactive
  setTimeout(() => {
    const qIndex = waitingQueue.findIndex(q => q.userId === profile.id);
    if (qIndex !== -1) {
      waitingQueue.splice(qIndex, 1);
      
      // Select appropriate bot partner
      const eligibleBots = bots.filter(b => {
        if (filters.find_gender !== 'any' && b.gender !== filters.find_gender) return false;
        if (b.age < filters.age_from || b.age > filters.age_to) return false;
        return true;
      });
      const selectedBot = eligibleBots.length > 0 
          ? eligibleBots[Math.floor(Math.random() * eligibleBots.length)]
          : bots[Math.floor(Math.random() * bots.length)];
        
      const chatId = Math.floor(100000 + Math.random() * 900000);
      const session: ChatSession = {
        id: chatId,
        user_a_id: profile.id,
        user_b_id: selectedBot.id,
        started_at: new Date(),
        topic: reqTopic,
        chat_lang: reqChatLang
      };
      
      chats.set(chatId, session);
      activeChats.set(chatId, session);
      
      publishToChannel(`waiting:${profile.id}`, {
        event: 'matched',
        room_key: `room_${chatId}`,
        channel: `chat:${chatId}`,
        token: 'mock_token',
        chat_id: chatId
      });
    }
  }, 3000);

  res.json({
    status: 'waiting',
    room_key: `room_waiting_${profile.id}`,
    token: 'mock_token',
    channel: `waiting:${profile.id}`
  });
});

app.post('/api/chat/cancel-search', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const index = waitingQueue.findIndex(q => q.userId === profile.id);
  if (index !== -1) {
    waitingQueue.splice(index, 1);
    return res.json({ cancelled: true });
  }
  res.json({ cancelled: false });
});

app.post('/api/chat/send', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { chat_id, type, content } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const activeChat = activeChats.get(chat_id);
  if (!activeChat) return res.status(403).json({ detail: 'You are not in this chat' });
  
  const msgId = messages.length + 1;
  const newMsg: Message = {
    id: msgId,
    chat_id,
    sender_id: profile.id,
    type: type || 'text',
    content_url_or_text: content,
    created_at: new Date()
  };
  messages.push(newMsg);
  
  const channel = `chat:${chat_id}`;
  
  // Publish user's message
  publishToChannel(channel, {
    event: 'message',
    id: msgId,
    chat_id,
    sender_id: profile.id,
    type: type || 'text',
    content,
    sent_at: newMsg.created_at.toISOString()
  });

  // Check if user triggered a game command
  if (type === 'text' || !type) {
    const lowerContent = content.trim().toLowerCase();
    if (lowerContent.startsWith('/pd') || lowerContent.startsWith('/пд') || lowerContent.startsWith('/never') || lowerContent.startsWith('/никогда')) {
      setTimeout(() => {
        let gameType: 'pd' | 'never' = 'pd';
        if (lowerContent.startsWith('/never') || lowerContent.startsWith('/никогда')) {
          gameType = 'never';
        }
        
        const lang = activeChat.chat_lang || 'ru';
        const langKey: 'ru' | 'en' | 'uz' = (lang === 'uz' ? 'uz' : lang === 'en' ? 'en' : 'ru');
        const questions = gamesDb[gameType][langKey];
        const randomQuestion = questions[Math.floor(Math.random() * questions.length)];
        
        let botName = 'Game Bot 🤖';
        if (langKey === 'ru') botName = 'Игровой Бот 🤖';
        if (langKey === 'uz') botName = 'O\'yin Boti 🤖';
        
        const gameMsgId = messages.length + 1;
        const gameNewMsg: Message = {
          id: gameMsgId,
          chat_id,
          sender_id: 9999, // Game Bot special sender ID
          type: 'text',
          content_url_or_text: `🎮 [${botName}]: ${randomQuestion}`,
          created_at: new Date()
        };
        messages.push(gameNewMsg);
        
        publishToChannel(channel, {
          event: 'message',
          id: gameMsgId,
          chat_id,
          sender_id: 9999,
          type: 'text',
          content: `🎮 [${botName}]: ${randomQuestion}`,
          sent_at: gameNewMsg.created_at.toISOString()
        });
      }, 600);
    }
  }

  // Check if partner is a bot
  const partnerId = activeChat.user_a_id === profile.id ? activeChat.user_b_id : activeChat.user_a_id;
  const botPartner = bots.find(b => b.id === partnerId);
  
  if (botPartner) {
    // Simulate typing indicator
    setTimeout(() => {
      publishToChannel(channel, {
        event: 'typing',
        sender_id: botPartner.id
      });
    }, 1000);
    
    // Simulate AI response
    setTimeout(async () => {
      const replyText = await generateGeminiBotReply(content, botPartner, profile);
      const botMsgId = messages.length + 1;
      const botNewMsg: Message = {
        id: botMsgId,
        chat_id,
        sender_id: botPartner.id,
        type: 'text',
        content_url_or_text: replyText,
        created_at: new Date()
      };
      messages.push(botNewMsg);
      
      publishToChannel(channel, {
        event: 'message',
        id: botMsgId,
        chat_id,
        sender_id: botPartner.id,
        type: 'text',
        content: replyText,
        sent_at: botNewMsg.created_at.toISOString()
      });
    }, 3000);
  }
  
  res.json({
    id: msgId,
    chat_id,
    type: type || 'text',
    sent_at: newMsg.created_at.toISOString()
  });
});

app.get('/api/chat/session/:chatId', authenticateTelegram, (req, res) => {
  const chatId = parseInt(req.params.chatId);
  const session = chats.get(chatId);
  if (!session) return res.status(404).json({ detail: 'Chat session not found' });
  
  const tgUser = req.user!;
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User profile not found' });
  
  const partnerId = session.user_a_id === profile.id ? session.user_b_id : session.user_a_id;
  const partner = users.get(partnerId);
  
  res.json({
    chat_id: session.id,
    topic: session.topic || 'topic_chat',
    chat_lang: session.chat_lang || 'ru',
    partner: partner ? {
      id: partner.id,
      nickname: partner.nickname,
      is_premium: partner.is_premium,
      chosen_emoji: partner.chosen_emoji || null,
      likes: partner.likes,
      dislikes: partner.dislikes,
      reputation_percent: partner.reputation_percent
    } : null
  });
});

app.post('/api/chat/typing', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { channel } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  publishToChannel(channel, {
    event: 'typing',
    sender_id: profile.id
  });
  res.json({ status: 'ok' });
});

app.post('/api/chat/end', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  // Read chat_id from either query parameters or request body (FastAPI supports query mapping)
  const chatId = parseInt(req.query.chat_id as string || req.body.chat_id);
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const activeChat = activeChats.get(chatId);
  if (!activeChat) return res.status(404).json({ detail: 'Chat not found' });
  
  activeChat.ended_at = new Date();
  activeChat.ended_reason = 'manual';
  activeChats.delete(chatId);
  
  // Calculate chat duration and add to both users' total uptime
  const durationMs = activeChat.ended_at.getTime() - activeChat.started_at.getTime();
  const durationSec = Math.floor(durationMs / 1000);
  
  profile.total_chat_seconds += durationSec;
  const partnerProfile = users.get(activeChat.user_a_id === profile.id ? activeChat.user_b_id : activeChat.user_a_id);
  if (partnerProfile) {
    partnerProfile.total_chat_seconds += durationSec;
  }
  
  // Notify room
  publishToChannel(`chat:${chatId}`, {
    event: 'chat_ended',
    reason: 'manual',
    ended_by: profile.id
  });
  
  res.json({ status: 'ended', chat_id: chatId });
});

app.post('/api/chat/rate', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { chat_id, to_user_id, value } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const target = users.get(to_user_id);
  if (target) {
    if (value === 'like') {
      target.likes += 1;
    } else {
      target.dislikes += 1;
    }
    // Re-calculate reputation percentage
    const total = target.likes + target.dislikes;
    target.reputation_percent = total > 0 ? Math.round((target.likes / total) * 100) : 100;
  }
  
  res.json({ status: 'rated', value });
});

app.post('/api/chat/report', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { chat_id, reported_id, category } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const report: Report = {
    id: reports.length + 1,
    chat_id,
    reporter_id: profile.id,
    reported_id,
    category,
    status: 'open'
  };
  reports.push(report);
  
  // Auto-dislike the reported user
  const reportedUser = users.get(reported_id);
  if (reportedUser) {
    reportedUser.dislikes += 1;
    const total = reportedUser.likes + reportedUser.dislikes;
    reportedUser.reputation_percent = total > 0 ? Math.round((reportedUser.likes / total) * 100) : 100;
    
    // Auto ban if reputation drops below 20% or has >5 NSFW/nsfw reports
    const botReports = reports.filter(r => r.reported_id === reported_id);
    if (reportedUser.reputation_percent < 20 || botReports.length >= 5) {
      reportedUser.is_banned = true;
    }
  }
  
  // End chat
  const activeChat = activeChats.get(chat_id);
  if (activeChat) {
    activeChat.ended_at = new Date();
    activeChat.ended_reason = 'report';
    activeChats.delete(chat_id);
    
    publishToChannel(`chat:${chat_id}`, {
      event: 'chat_ended',
      reason: 'report'
    });
  }
  
  res.json({ status: 'reported', report_id: report.id });
});

app.get('/api/chat/archive', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const list = Array.from(chats.values())
    .filter(c => c.user_a_id === profile.id || c.user_b_id === profile.id)
    .map(c => {
      const partnerId = c.user_a_id === profile.id ? c.user_b_id : c.user_a_id;
      const partner = users.get(partnerId);
      return {
        chat_id: c.id,
        partner: {
          id: partnerId,
          nickname: partner ? partner.nickname : 'Deleted',
          is_premium: partner ? partner.is_premium : false,
          chosen_emoji: partner ? partner.chosen_emoji || null : null
        },
        started_at: c.started_at.toISOString(),
        ended_at: c.ended_at ? c.ended_at.toISOString() : null,
        ended_reason: c.ended_reason || null,
        is_active: !c.ended_at
      };
    });
    
  res.json({ archive: list });
});

app.get('/api/chat/messages/:chatId', authenticateTelegram, (req, res) => {
  const chatId = parseInt(req.params.chatId);
  const list = messages
    .filter(m => m.chat_id === chatId)
    .map(m => ({
      id: m.id,
      sender_id: m.sender_id,
      type: m.type,
      content: m.content_url_or_text,
      sent_at: m.created_at.toISOString()
    }));
  res.json({ messages: list });
});

app.get('/api/chat/online-count', authenticateTelegram, (req, res) => {
  // Simulate active online user count
  res.json({ online: 42 + Array.from(channelSubscriptions.keys()).length });
});

app.post('/api/chat/heartbeat', authenticateTelegram, (req, res) => {
  res.json({ status: 'ok' });
});

// Multipart parsing stream-helper for media uploads
function parseMultipart(req: any): Promise<{ filename: string, buffer: Buffer, contentType: string }> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (chunk: any) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on('end', () => {
      const buffer = Buffer.concat(chunks);
      const contentTypeHeader = req.headers['content-type'] || '';
      const boundaryMatch = contentTypeHeader.match(/boundary=(.+)/);
      if (!boundaryMatch) {
        return resolve({ filename: 'upload.png', buffer, contentType: 'image/png' });
      }
      const boundary = boundaryMatch[1];
      const boundaryIndex = buffer.indexOf(Buffer.from('--' + boundary));
      if (boundaryIndex === -1) {
        return resolve({ filename: 'upload.png', buffer, contentType: 'image/png' });
      }
      const fileDataStart = buffer.indexOf(Buffer.from('\r\n\r\n'), boundaryIndex);
      if (fileDataStart === -1) {
        return resolve({ filename: 'upload.png', buffer, contentType: 'image/png' });
      }
      const headerBlock = buffer.slice(boundaryIndex, fileDataStart).toString();
      const filenameMatch = headerBlock.match(/filename="(.+?)"/);
      const mimeMatch = headerBlock.match(/Content-Type:\s*(.+)/i);
      
      const filename = filenameMatch ? filenameMatch[1] : 'upload.png';
      const contentType = mimeMatch ? mimeMatch[1].trim() : 'image/png';
      
      const fileDataEnd = buffer.indexOf(Buffer.from('\r\n--' + boundary), fileDataStart);
      const fileBuffer = fileDataEnd !== -1 
        ? buffer.slice(fileDataStart + 4, fileDataEnd)
        : buffer.slice(fileDataStart + 4);
        
      resolve({ filename, buffer: fileBuffer, contentType });
    });
    req.on('error', (err) => reject(err));
  });
}

app.post('/api/chat/upload-media', authenticateTelegram, async (req, res) => {
  const chatId = parseInt(req.query.chat_id as string || req.body.chat_id);
  const tgUser = req.user!;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  const activeChat = activeChats.get(chatId);
  if (!activeChat) return res.status(403).json({ detail: 'You are not in this chat' });

  try {
    const { filename, buffer, contentType } = await parseMultipart(req);
    
    // Save file locally
    const ext = path.extname(filename) || '.png';
    const savedName = `upload_${chatId}_${Date.now()}${ext}`;
    
    // Write to public/uploads & dist/uploads
    fs.writeFileSync(path.join(process.cwd(), 'public/uploads', savedName), buffer);
    fs.writeFileSync(path.join(process.cwd(), 'dist/uploads', savedName), buffer);
    
    const fileUrl = `/uploads/${savedName}`;
    
    let msgType = 'photo';
    if (contentType.startsWith('video')) {
      msgType = 'video';
    } else if (contentType.includes('audio')) {
      msgType = 'voice';
    }

    const msgId = messages.length + 1;
    const newMsg: Message = {
      id: msgId,
      chat_id: chatId,
      sender_id: profile.id,
      type: msgType,
      content_url_or_text: fileUrl,
      created_at: new Date()
    };
    messages.push(newMsg);
    
    publishToChannel(`chat:${chatId}`, {
      event: 'message',
      id: msgId,
      chat_id: chatId,
      sender_id: profile.id,
      type: msgType,
      content: fileUrl,
      sent_at: newMsg.created_at.toISOString()
    });

    res.json({ id: msgId, url: fileUrl, type: msgType });
  } catch (err) {
    console.error('Upload error:', err);
    res.status(500).json({ detail: 'Failed to process file upload' });
  }
});

// 3. Payment Endpoints
app.post('/api/payments/create-invoice', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const { type } = req.body;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  if (!profile) return res.status(404).json({ detail: 'User not found' });
  
  // Instant mock complete on payment!
  if (type === 'premium') {
    profile.is_premium = true;
  } else if (type === 'remove_dislikes') {
    profile.dislikes = 0;
    profile.reputation_percent = 100;
  }
  
  res.json({ status: 'completed', type });
});

app.get('/api/payments/history', authenticateTelegram, (req, res) => {
  res.json({ history: [] });
});

app.get('/api/payments/prices', authenticateTelegram, (req, res) => {
  res.json({
    prices: {
      premium: 50,
      remove_dislikes: 20
    }
  });
});

// 4. Admin Endpoints
app.get('/api/admin/stats', authenticateTelegram, (req, res) => {
  res.json({
    stats: {
      total_users: users.size,
      active_chats: activeChats.size,
      total_reports: reports.length,
      total_referrals: referrals.length
    }
  });
});

app.get('/api/admin/reports', authenticateTelegram, (req, res) => {
  res.json({ reports });
});

app.post('/api/admin/reports/:reportId/resolve', authenticateTelegram, (req, res) => {
  const reportId = parseInt(req.params.reportId);
  const { action } = req.body;
  
  const r = reports.find(rep => rep.id === reportId);
  if (r) {
    r.status = 'resolved';
    if (action === 'ban') {
      const reported = users.get(r.reported_id);
      if (reported) reported.is_banned = true;
    }
  }
  res.json({ status: 'resolved' });
});

app.post('/api/admin/users/:userId/ban', authenticateTelegram, (req, res) => {
  const userId = parseInt(req.params.userId);
  const u = users.get(userId);
  if (u) u.is_banned = true;
  res.json({ status: 'banned' });
});

app.post('/api/admin/users/:userId/unban', authenticateTelegram, (req, res) => {
  const userId = parseInt(req.params.userId);
  const u = users.get(userId);
  if (u) u.is_banned = false;
  res.json({ status: 'unbanned' });
});

app.post('/api/admin/referrals', authenticateTelegram, (req, res) => {
  const tgUser = req.user!;
  const code = req.body.code || `REF_${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
  
  const profile = Array.from(users.values()).find(u => u.tg_id === tgUser.id);
  const ref: Referral = {
    id: referrals.length + 1,
    code,
    created_by_admin_id: profile ? profile.id : 11111111,
    uses_count: 0
  };
  referrals.push(ref);
  res.json(ref);
});

app.get('/api/admin/referrals', authenticateTelegram, (req, res) => {
  res.json({ referrals });
});

app.get('/api/admin/logs', authenticateTelegram, (req, res) => {
  res.json({
    logs: [
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'System boot completed' },
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'WebSocket Server initialized on port 3000' },
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'Prepopulated mock profiles linked successfully' }
    ]
  });
});

// --- Vite & SPA Handling ---
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(process.cwd(), 'dist')));
    app.get('*all', (req, res) => {
      res.sendFile(path.join(process.cwd(), 'dist', 'index.html'));
    });
  }

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`[CyberAnonServer] Running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
