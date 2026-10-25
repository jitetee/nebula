# 🌌 KSL Ecosystem — Complete Feature Documentation

> **The KashSight platform connecting the jtlearn terminal app with a web ecosystem for content discovery, community submissions, rewards, and engagement.**

<p align="center">
  <sub>🌐 Ecosystem Guide • Version 1.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [📊 Overview](#-overview)
- [📎 KSL Link Submission](#-ksl-link-submission-submit-kslhtml)
- [⭐ Ratings System](#-ratings-system-ratekslfile)
- [💰 Buying Flow](#-buying-flow-submittransaction)
- [💬 Contact / Suggestions](#-contact--suggestions-contacthtml)
- [🏆 LearnQuest](#-learnquest-learnquesthtml--jtlearn-cli)
- [🛠️ Admin Dashboard Functions](#%EF%B8%8F-admin-dashboard-functions)
- [🌳 Complete RTDB Tree](#-complete-rtdb-tree)
- [📋 jtlearn Menu Structure](#-jtlearn-menu-structure-v12)
- [🌐 Website Pages](#-website-pages)
- [📁 Files Changed / Created](#-files-changed--created)

---

## 📊 Overview

| Component | Purpose |
|:---|:---|
| **jtlearn CLI** | Terminal-based learning application |
| **Web Ecosystem** | Firebase-hosted website for community features |
| **Connection** | RTDB (Realtime Database) syncs data between terminal and web |

---

## 📎 KSL Link Submission (`submit-ksl.html`)

> **Purpose:** Users submit KSL content links for the community. Approved submissions appear in the KSL Market.

### User Flow

```
1. User signs in → goes to /submit-ksl.html
2. Fills in: title, description, category, download link, type, price, tags
3. Submits → saved to kslSubmissions/ with status "pending"
4. Admin reviews → approves → appears in KSL Market
```

### RTDB Structure

```
kslSubmissions/
  └── {pushId}/
      ├── id: "KSL-1712345678901"
      ├── uid, email, name
      ├── title, description, category
      ├── driveLink, type (free/paid), price
      ├── tags: ["python", "beginner"]
      ├── status: "pending" | "approved" | "rejected"
      ├── createdAt, approvedAt, rejectionReason
```

### Firebase Helpers

| Function | Purpose |
|:---|:---|
| `submitKslLink(data)` | User submits a KSL link (requires auth) |
| `approveKslLink(linkKey)` | Admin approves → shows in market |
| `rejectKslLink(linkKey, reason)` | Admin rejects with reason |

---

## ⭐ Ratings System (`rateKslFile`)

> **Purpose:** Users rate KSL files with 1-5 stars and optional review text.

### RTDB Structure

```
kslRatings/
  └── {fileId}/
      └── {pushId}/
          ├── uid, name, rating (1-5), review, createdAt

kslRatingsAgg/
  └── {fileId}/
      ├── rating: 4.5
      └── count: 12
```

### Firebase Helpers

| Function | Purpose |
|:---|:---|
| `rateKslFile(fileId, rating, review)` | Rate a file (1-5 stars + text) |

---

## 💰 Buying Flow (`submitTransaction`)

> **Purpose:** Users pay for premium KSL content. Admin confirms payment, sends email with download link.

### User Flow

```
1. User selects premium KSL file → clicks "Buy"
2. Submits payment proof (screenshot, M-Pesa code, etc.)
3. Saved to transactions/ with status "pending"
4. Admin verifies payment → approves → sets download link + custom message
5. User receives email notification with download link unlocked
```

### RTDB Structure

```
transactions/
  └── {pushId}/
      ├── id, uid, email
      ├── itemId, itemName, amount
      ├── paymentMethod, paymentRef, paymentScreenshot
      ├── status: "pending" | "approved" | "rejected"
      ├── submittedAt, approvedBy, approvedAt
      ├── downloadLink, customMessage
```

### Firebase Helpers

| Function | Purpose |
|:---|:---|
| `submitTransaction(data)` | User submits payment proof |
| `approveTransaction(txnKey, downloadLink, customMessage)` | Admin approves + unlocks download |

### Email Flow

Admin sends email manually with:

| Field | Format |
|:---|:---|
| **To** | `txn.email` |
| **Subject** | `"Your KSL content is ready — {itemName}"` |
| **Body** | `customMessage` + `downloadLink` |

---

## 💬 Contact / Suggestions (`contact.html`)

> **Purpose:** Anyone (including anonymous visitors) can send suggestions, feedback, bug reports, or support requests.

### User Flow

```
1. Go to /contact.html
2. Optional: enter name + email (anonymous OK)
3. Select type: Suggestion, Feedback, Bug, Content Request, Support, Other
4. Enter subject + message
5. Submit → saved to contactMessages/
```

### RTDB Structure

```
contactMessages/
  └── {pushId}/
      ├── id, uid ("anonymous"), email, name
      ├── type: "suggestion" | "feedback" | "bug" | "request" | "support" | "other"
      ├── subject, message
      ├── status: "unread" | "read" | "replied"
      └── createdAt
```

### Firebase Helpers

| Function | Purpose |
|:---|:---|
| `submitContactMessage(data)` | Send message (works for anonymous users) |

---

## 🏆 LearnQuest (`learnquest.html` + jtlearn CLI)

> **Purpose:** Users download KSL quizzes, answer them, submit answer JSON, and win rewards for high scores.

### How It Works

#### In jtlearn (Terminal)

```
1. Press L → LearnQuest from main menu
2. Select a quiz from available quizzes
3. Answer questions one by one (with instant feedback)
4. Results shown with score, percentage, and reward eligibility
5. Answer JSON generated and saved to learnquest/answers_{questId}.json
6. Options: Submit to website, view file, copy to clipboard
```

#### On Website (`/learnquest.html`)

```
1. Upload answer JSON file (drag & drop or browse)
2. Preview questions and answers
3. Submit to Firebase (logged in = rewards tracked, guest = no rewards)
4. Download answer JSON for manual submission
```

### Answer JSON Format

```json
{
  "questId": "LQ-1712345678901",
  "title": "Python Basics Quiz",
  "answers": { "0": 1, "1": 2, "2": 0 },
  "score": 2,
  "totalQuestions": 3,
  "percentage": 66.7,
  "submittedAt": "2025-04-06T12:00:00.000Z"
}
```

### Rewards

| Score | Reward |
|:---|:---|
| **90%+** | 🏆 Free premium KSL content |
| **80%+** | 🏅 LearnQuest champion badge |
| **70%+** | 📊 Leaderboard spot |
| **Any** | 🎁 Early access to new content |

### Firebase Helpers

| Function | Purpose |
|:---|:---|
| `submitLearnQuest(questData)` | Logged-in user submission |
| `submitLearnQuestGuest(questData, name, email)` | Guest submission |

---

## 🛠️ Admin Dashboard Functions

| Function | Purpose |
|:---|:---|
| `approveKslLink(linkKey)` | Approve KSL submission → show in market |
| `rejectKslLink(linkKey, reason)` | Reject with reason |
| `approveTransaction(txnKey, link, msg)` | Approve payment + unlock download |
| `addStoreItem(item)` | Add new store item |
| `deleteStoreItem(itemId)` | Remove store item |
| `updateStoreItem(itemId, updates)` | Edit store item |
| `updateKslRequestStatus(key, status, notes)` | Approve/reject KSL requests |

---

## 🌳 Complete RTDB Tree

```
kash-sight-default-rtdb/
├── users/{uid}/                    # User profiles
├── kslSubmissions/                 # User-submitted KSL links (pending → approved)
├── kslRatings/{fileId}/{pushId}/  # Individual ratings
├── kslRatingsAgg/{fileId}/         # Aggregated ratings (avg + count)
├── transactions/                   # Payment submissions
├── contactMessages/                # Contact/suggestions (anonymous OK)
├── learnQuest/{questId}/           # LearnQuest answer submissions
├── kslRequests/                    # KSL content requests
├── kslDownloads/{uid}/             # Per-user download history
├── storeDownloads/{itemId}/        # Per-item download counts
├── storeItems/                     # Store catalog items
├── storeReviews/                   # Store reviews
├── kslLinks/                       # Tracked KSL link clicks
├── kslLinkActivity/                # Link click audit log
├── activityLog/                    # General activity log
└── kslStore/                       # Store items (legacy)
```

---

## 📋 jtlearn Menu Structure (v1.2)

| # | Option | Shortcut | Description |
|:---:|:---|:---:|:---|
| 1 | 📂 Course Catalog | `1` / `CC` | Hierarchical courses with AI tutor |
| 2 | 📚 Study Notes | `2` / `N` | Browse learning materials |
| 3 | 📝 Take Quiz | `3` / `Q` | Interactive quizzes |
| 4 | 🤖 AI Chat | `4` | AI tutor with proactive suggestions |
| 5 | 📊 My Progress | `5` / `P` | Analytics + scores + achievements + export |
| 6 | 🔖 Study Tools | `6` / `T` | Bookmarks + search + spaced review |
| 7 | 🧠 Knowledge Brain | `7` / `B` | Offline Q&A database |
| 8 | 🏪 Data Store | `8` | Download free & premium courses |
| S | ❤️ Support | `S` | Credits, email, website |
| F | 🎮 Study Modes | `F` / `M` | Flashcards + timed quiz + tutorials |
| **L** | **🏆 LearnQuest** | **`L`** | **Quiz → JSON → submit & win rewards** |
| D | 👤 Profiles | `D` | Switch/manage profiles |
| C | ⚙️ Settings | `C` | Configure experience |
| H | ❓ Help | `H` | Commands and usage |
| 0 | ❌ Exit | `0` | Leave jtlearn |

---

## 🌐 Website Pages

| Page | URL | Purpose |
|:---|:---|:---|
| 🏠 **Home** | `/index.html` | Landing page with hero, features, terminal preview |
| 📚 **jtlearn Tool** | `/jtlearn.html` | Features, install instructions, terminal mockup |
| 🏪 **KSL Store** | `/store.html` | Browse free/premium KSL content |
| 📎 **Submit KSL** | `/submit-ksl.html` | User-submitted KSL links for review |
| 📝 **Request KSL** | `/request-ksl.html` | Request custom KSL content |
| 🏆 **LearnQuest** | `/learnquest.html` | Upload answer JSON → submit → win rewards |
| 💬 **Contact** | `/contact.html` | Suggestions, feedback, support (anonymous OK) |
| 🔑 **Login** | `/login.html` | Firebase Auth sign-in |
| 📝 **Signup** | `/signup.html` | Firebase Auth registration |
| 👤 **Customer Dashboard** | `/customer-dashboard.html` | User dashboard with stats, requests, downloads |
| 🛡️ **Admin Dashboard** | `/admin-dashboard.html` | Admin panel for approvals, store management |

---

## 📁 Files Changed / Created

### Created

| File | Purpose |
|:---|:---|
| `website/public/submit-ksl.html` | KSL link submission page |
| `website/public/contact.html` | Contact/suggestions page (anonymous) |
| `website/public/learnquest.html` | LearnQuest challenge page |
| `website/public/js/learnquest.js` | LearnQuest JS engine (upload, render, submit) |
| `jtlearn/cli.py` `_run_learnquest()` | Terminal LearnQuest quiz runner |

### Updated

| File | Changes |
|:---|:---|
| `website/public/js/firebase-config.js` | Added: submitKslLink, approveKslLink, rateKslFile, submitTransaction, approveTransaction, submitContactMessage, submitLearnQuest, submitLearnQuestGuest |
| `website/public/index.html` | Nav: added Submit KSL, LearnQuest, Contact links |
| `website/public/jtlearn.html` | Nav updated, features updated |
| `website/public/store.html` | Nav updated |
| `website/public/request-ksl.html` | Uses submitKslRequest with Firebase guard |
| `website/public/login.html` | waitForAuth guard, Firebase SDK added |
| `website/public/signup.html` | waitForAuth guard, duplicate SDKs removed |
| `website/public/customer-dashboard.html` | Firebase SDK added, init guard |
| `website/public/admin-dashboard.html` | Fixed duplicate SDKs, single firebase-config |
| `website/public/js/ksl-store.js` | initStore() guard for db availability |
| `website/public/js/customer.js` | initCustomerAuth() guard |
| `website/public/js/admin.js` | initAdminAuth() guard |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/kashsight/kslearn">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
