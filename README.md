
# 🚀 FormFiller: Automatica Form Filling with Personal Knowledge Base 🧙‍♂️

(the whole readme is written by Claude, so don't mind the dramatic language here 😅)

Ever dreamed of a personal assistant that remembers everything and fills out your forms in a snap? Well, dream no more! Welcome to the AI-Powered Form Filler and Knowledge Wizard – your new best friend in the digital world! 

![test](https://github.com/user-attachments/assets/18300be0-6690-4d24-a449-c173a429ca50)

## ✨ What's This Sorcery?

Imagine having a brilliant secretary who:
- 📚 Remembers everything you've ever read or uploaded
- 📝 Fills out boring PDF forms for you (ugh, paperwork!)
- 🌐 Magically completes web forms while you sip your coffee
- 💬 Chats with you about all that stored knowledge

Sounds like science fiction? Nope, it's just our AI wizard at work! 🧙‍♂️✨

## 🛠 Setting Up Your Magical Workshop

### 🧰 What You'll Need

- Python 3.7+ (🐍 Slytherin approved!)
- Node.js and npm (For brewing our web potions)
- An OpenAI API key (The secret ingredient)

### 🪄 Casting the Setup Spell

1. Summon the code with `git clone`

2. Conjure the Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Whisper your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_super_secret_key_here
   ```

4. Prepare the Chrome/Edge extension elixir:
   - Follow instructions here https://learn.microsoft.com/en-us/deployedge/microsoft-edge-manage-extensions-webstore
   - You want to enable developer mode, go to the extensions and install from unpacked source
   - When using plugin, you need to start the `tornado-server.py`

## 🧠 Unleashing the Knowledge Kraken

Fire up the knowledge console:

```
python KnowledgeConsole.py
```

Command your Kraken:
- `file <path> <comment>`: Feed it a document
- `update <info>`: Teach it a new trick
- `search <query>`: Ask it to remember something
- `all`: See all its tentacles (memories)
- `del <query>`: Make it forget (use responsibly!)

## 📄 Battling the PDF Dragon

Summon the form-filling dragon slayer:

```
python FormFillerConsole.py
```

Defeat PDFs with: `fill <path>`

## 🏰 Fortifying Your Digital Castle

Raise the server shields:

```
python tornado-server.py
```

Your fortress will stand tall at `http://localhost:8888`.

## 🌈 Unleashing the Chrome Rainbow

1. Gallop to `chrome://extensions/`
2. Flip the "Developer mode" switch
3. Click "Load unpacked" and choose your `chrome-extension` treasure chest

## 🎭 Mastering Your New Powers

1. Summon the sidebar with the extension icon
2. "Fill Forms" to watch web forms complete themselves like magic
3. "Upload Documents" to expand your knowledge empire
4. Chat with your AI familiar for instant knowledge retrieval

## 🧬 The Science Behind the Magic

1. **Document Sorcery**: LLMs devour documents, extracting their essence.

2. **Knowledge Alchemy**: 
   - Information is transmuted into wisdom nuggets.
   - Each nugget is carefully placed in the grand tapestry of knowledge.

3. **PDF Enchantment**:
   - Forms are deciphered into mystical questions.
   - Memories are summoned from the knowledge realm.
   - A wise LLM oracle provides the answers.

4. **Web Form Telepathy**:
   - Form whispers are instantly understood.
   - Answers materialize faster than you can say "Abracadabra!"

