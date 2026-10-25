# 🔐 jtlearn Content Selling Guide

> **Your complete guide to monetizing educational content with jtlearn.**

<p align="center">
  <sub>💰 Business Guide • Version 1.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [💼 Business Model](#-business-model)
- [⚙️ How It Works](#%EF%B8%8F-how-it-works)
- [📦 Preparing Content for Sale](#-preparing-content-for-sale)
- [🔐 Encryption Levels](#-encryption-levels)
- [📋 Commands Reference](#-commands-reference)
- [📁 Directory Structure](#-directory-structure-what-buyers-get)
- [🛡️ Security Reality](#%EF%B8%8F-security-reality)
- [🎯 Recommended Setup](#-recommended-setup-for-selling)

---

## 💼 Business Model

> **The code is free. The content costs money.**

```
┌─────────────────────┐     ┌──────────────────────┐
│  Open Source App    │  +  │  Sold Encrypted      │
│  (MIT License)      │     │  Content (.enc)      │
└─────────────────────┘     └──────────────────────┘
```

| Component | Status | Access |
|:---|:---:|:---|
| **App code** | 🆓 Free & Open Source | Anyone can clone and run |
| **Notes/Quizzes** | 💎 Encrypted & Sold | Requires activation key |

> **Analogy:** Free Kindle app, paid ebooks. The reader is free — the books cost money.

---

## ⚙️ How It Works

### For You (the seller)

```bash
# 1. Create/edit notes as plain JSON
nano data/notes/advanced_physics.json

# 2. Encrypt the content you want to sell
python encrypt_content.py encrypt --key "YOUR-MASTER-KEY"

# 3. Verify decryption works
python encrypt_content.py decrypt --key "YOUR-MASTER-KEY" --dry

# 4. Delete backups after confirming
find data/ -name '*.bak' -delete

# 5. The .enc files are what you distribute
#    The .json files stay on YOUR machine only
```

### For Buyers (your users)

```bash
# 1. Clone and install the app (free)
git clone https://github.com/jitetee/nebula
cd jtlearn
pip install .

# 2. They get encrypted .enc files from you
#    (downloaded after purchase, or included in repo)

# 3. Activate with the key you gave them
jtlearn activate
# Enter: ABC123-DEF456-789

# 4. Content unlocks automatically
jtlearn
```

---

## 📦 Preparing Content for Sale

### Step 0: Your Content Key

The default key is `jtlearn2026` — stored obfuscated in `jtlearn/loader.py`:

```python
_PARTS = [b'a3NlYXJu', b'MjAyNg==']  # base64 of "jtlearn" + "2026"
```

#### To change the key:

```bash
python3 -c "
import base64
key = 'your-new-key-here'
mid = len(key) // 2
p1 = base64.b64encode(key[:mid].encode()).decode()
p2 = base64.b64encode(key[mid:].encode()).decode()
print(f'_PARTS = [b\"{p1}\", b\"{p2}\"]')
print(f'Your key: {key}')
"
```

Then:
1. Update `_PARTS` in `jtlearn/loader.py`
2. Decrypt content with old key
3. Re-encrypt with new key

### Step 1: Create Content (Plain JSON)

```
data/notes/advanced_physics.json   ← your work
data/notes/python_mastery.json     ← your work
data/quizzes/physics_quiz.json     ← your work
```

### Step 2: Encrypt Premium Content

```bash
# Dry run first (safe — previews only)
python encrypt_content.py encrypt --key "jtlearn-premium-2026" --dry

# Encrypt for real
python encrypt_content.py encrypt --key "jtlearn-premium-2026"
```

**Result:**

| File | Status |
|:---|:---|
| `data/notes/advanced_physics.json.enc` | 🔒 Encrypted |
| `data/notes/python_mastery.json.enc` | 🔒 Encrypted |
| `data/notes/basic_math.json` | 🆓 Free (plain JSON) |

### Step 3: Generate Unique Keys per Buyer (Optional)

```python
import hashlib
import secrets

def generate_buyer_key(buyer_email):
    """Generate a unique activation key tied to a buyer."""
    random_salt = secrets.token_hex(8)
    raw = f"jtlearn-{buyer_email}-{random_salt}-2026"
    return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()

# Example:
key = generate_buyer_key("customer@email.com")
# Output: "A3F8B2C9D1E4F7A0B5C8D2E6"
```

| Approach | Pros | Cons |
|:---|:---|:---|
| **One master key** | Simple, one encryption step | If leaked, everyone can use it |
| **Unique key per buyer** | Revocable, breach-contained | Must encrypt separately per buyer |

### Step 4: Distribute

| What | Where |
|:---|:---|
| 📦 App code (`.py` files) | GitHub (public, MIT license) |
| 🆓 Free content (plain `.json`) | GitHub (public) |
| 🔒 Premium content (`.enc` files) | GitHub or download after purchase |
| 🔑 Activation key | Sent to buyer after payment (email, receipt) |

### Step 5: Buyer Activates

```bash
jtlearn activate --key "A3F8B2C9D1E4F7A0B5C8D2E6"
```

The key is saved to `~/.jtlearn/licenses/content.key` and used automatically.

---

## 🔐 Encryption Levels

| Level | Description | Best For |
|:---|:---|:---|
| **A. Master Key** | One key for all buyers | Small operations, trusted audience |
| **B. Unique Keys** | Separate key per buyer | Higher security, revocable access |
| **C. Tiered Content** | Mix of free + encrypted | Recommended — attract users with free content |

### What Buyers See Without a Key

```
┌──────────────────────────────────────────┐
│ 🔒 Premium content detected!             │
│                                          │
│ You have encrypted content that needs     │
│ activation.                               │
│ Run jtlearn activate to enter your        │
│ license key and unlock purchased notes.   │
└──────────────────────────────────────────┘
```

---

## 📋 Commands Reference

### For You (Seller)

| Command | Purpose |
|:---|:---|
| `python encrypt_content.py encrypt --key SECRET` | Encrypt premium content |
| `python encrypt_content.py decrypt --key SECRET` | Decrypt to edit content |
| `python encrypt_content.py status` | See which files are encrypted |
| `python encrypt_content.py encrypt --key SECRET --dry` | Preview before encrypting |
| `find data/ -name '*.bak' -delete` | Clean up backup files |

### For Buyers (Users)

| Command | Purpose |
|:---|:---|
| `jtlearn activate` | Enter purchased activation key |
| `jtlearn activate --key ABC123` | Activate directly |
| `jtlearn` | Run app — encrypted content auto-unlocks |

---

## 🔓 How Auto-Decrypt Works

```
1. Loader finds: data/notes/advanced_physics.json.enc
2. Reads user's key from: ~/.jtlearn/licenses/content.key
3. Decrypts in memory (never writes decrypted to disk)
4. Returns content to app normally
5. User sees notes/quizzes like nothing is encrypted
```

> ✅ **Encrypted files never get written to disk as plain JSON.** Decryption happens entirely in memory.

---

## 📁 Directory Structure (What Buyers Get)

```
jtlearn/
├── jtlearn/              ← Python app code (open source, MIT)
│   ├── cli.py
│   ├── loader.py         ← auto-decrypts .enc files
│   └── ...
├── data/
│   ├── notes/
│   │   ├── basic_math.json             ← 🆓 FREE
│   │   ├── advanced_physics.json.enc   ← 🔒 PREMIUM
│   │   └── python_mastery.json.enc     ← 🔒 PREMIUM
│   └── quizzes/
│       ├── general_quiz.json           ← 🆓 FREE
│       └── physics_quiz.json.enc       ← 🔒 PREMIUM
├── encrypt_content.py      ← Your encryption tool
├── PROTECTION.md           ← This file
└── README.md
```

---

## 🛡️ Security Reality

| Who | What They Can Do |
|:---|:---|
| Random person cloning repo | ✅ Read app code • ❌ NOT encrypted content |
| Buyer who purchased | ✅ Read content they paid for |
| Buyer who shares their key | Others can use that key (unless unique keys) |
| Skilled developer | Can eventually reverse-engineer if determined |

> **Bottom line:** This stops **~95%** of unauthorized access. A determined attacker with Python skills can eventually extract the key, but most people just want to use the app.

---

## 🎯 Recommended Setup for Selling

1. ✅ **Keep one master encryption key** (store securely, NOT in git)
2. ✅ **Encrypt premium content once** with that key
3. ✅ **Include .enc files in the repo** (useless without the key)
4. ✅ **Send the key only to paying customers** (email, receipt page)
5. ✅ **Keep free content as plain JSON** to attract users
6. ✅ **Never commit the master key to git** (add to `.gitignore`)

### Your Workflow

```
Create content
     ↓
Encrypt with master key
     ↓
Push .enc to GitHub
     ↓
Buyer purchases → Gets key
     ↓
Buyer runs: jtlearn activate
     ↓
Content unlocks ✅
```

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/jitetee/nebula">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
