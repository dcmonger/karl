require("dotenv").config();

const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");

const token = process.env.TELEGRAM_TOKEN;
const geminiKey = process.env.GEMINI_KEY;
const bot = new TelegramBot(token, { polling: true });



// simple memory (replace later with DB)
let inventory = [];

bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  // very basic commands
  if (text.startsWith("add ")) {
    const item = text.replace("add ", "");
    inventory.push(item);
    return bot.sendMessage(chatId, `Added: ${item}`);
  }

  if (text === "inventory") {
    return bot.sendMessage(chatId, inventory.join(", ") || "Empty");
  }

  // AI call (Gemini Flash example)
  const response = await axios.post(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + geminiKey,
    {
      contents: [
        {
          parts: [
            {
              text: `You are a kitchen assistant. Inventory: ${inventory.join(", ")}. User: ${text}`
            }
          ]
        }
      ]
    }
  );

  const reply =
    response.data.candidates?.[0]?.content?.parts?.[0]?.text ||
    "No response";

  bot.sendMessage(chatId, reply);
});