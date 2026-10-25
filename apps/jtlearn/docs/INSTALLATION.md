# 🚀 jtlearn Installation Guide

> **Complete installation instructions for all platforms — from scratch to fully working!**

<p align="center">
  <sub>📦 Installation Guide • Version 2.0 • jtlearn 2.0.0</sub>
</p>

---

## 📋 Table of Contents

- [⚡ Quick Start](#-quick-start)
- [📱 Android (Termux)](#-android-termux)
- [🐧 Linux (Ubuntu/Debian)](#-linux-ubuntudebian)
- [🍎 macOS](#-macos)
- [🪟 Windows](#-windows)
- [📥 Installation Methods](#-installation-methods)
- [✅ Verification](#-verification)
- [🔧 Troubleshooting](#-troubleshooting)
- [🗑️ Uninstallation](#%EF%B8%8F-uninstallation)
- [📊 Installation Comparison](#-installation-comparison)
- [🎯 Post-Installation](#-post-installation)
- [📞 Getting Help](#-getting-help)

---

## ⚡ Quick Start

> **Already have Python? Install in 30 seconds.**

### Method 1: Git Clone (Recommended)

```bash
# Clone repository
git clone https://github.com/kashsight/kslearn.git
cd jtlearn

# Install in editable mode
pip install -e .

# Start learning!
jtlearn
```

### Method 2: ZIP Download

```bash
# Download from GitHub → Code → Download ZIP
# Extract and navigate to folder
cd jtlearn

# Install
pip install -e .

# Start learning!
jtlearn
```

> 💡 **Tip:** v2.0.0 includes 13+ features, AI-powered suggestions, hierarchical courses, and KSL-Verse game.

---

## 📱 Android (Termux)

### Prerequisites

| Requirement | Details |
|:---|:---|
| **Device** | Android phone/tablet |
| **App** | Termux (F-Droid recommended, or Play Store) |
| **Python** | 3.7+ |

### Step-by-Step Installation

#### 1. Update Termux Packages

```bash
pkg update && pkg upgrade -y
```

#### 2. Install Python

```bash
pkg install python -y
```

#### 3. Install Required Dependencies

```bash
pkg install python-pip -y
pkg install git -y
pkg install build-essential -y
```

#### 4. Install jtlearn

**Option A: Git Clone (Recommended)**

```bash
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip install -e .
```

**Option B: ZIP Download**

```bash
# Install wget and unzip
pkg install wget unzip -y

# Download ZIP
wget https://github.com/kashsight/kslearn/archive/refs/heads/main.zip

# Extract and install
unzip main.zip
cd jtlearn-main
pip install -e .
```

#### 5. (Optional) Install AI Chat

For offline AI chat feature:

```bash
# Install termux-ai
pkg install termux-ai -y

# Or install tgpt directly
curl -sL https://is.gd/Termux_Ai | bash
```

#### 6. Verify & Launch

```bash
# Check version
jtlearn --version

# Launch
jtlearn
```

### 🏃 Termux Quick Install (One-Liner)

```bash
pkg update && pkg upgrade -y && pkg install python git -y && git clone https://github.com/kashsight/kslearn.git && cd jtlearn && pip install -e . && jtlearn
```

### Termux Troubleshooting

| Problem | Solution |
|:---|:---|
| `pip` not found | `pkg install python-pip -y` |
| Permission denied | `chmod +x setup.py && pip install --user -e .` |
| Installation fails | `pip install --upgrade pip && pip install -e . --no-cache-dir` |

---

## 🐧 Linux (Ubuntu/Debian)

### Prerequisites

| Requirement | Details |
|:---|:---|
| **OS** | Ubuntu 20.04+ / Debian 10+ / Linux Mint 20+ |
| **Access** | Terminal with sudo |

### Step-by-Step Installation

#### 1. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Install Python and pip

```bash
sudo apt install python3 python3-pip python3-venv -y
```

#### 3. Install Git

```bash
sudo apt install git -y
```

#### 4. Create Virtual Environment (Recommended)

```bash
python3 -m venv jtlearn-env
source jtlearn-env/bin/activate
```

#### 5. Install jtlearn

```bash
# Clone repository
git clone https://github.com/kashsight/kslearn.git
cd jtlearn

# Install
pip install -e .
```

#### 6. Create Alias (Optional)

```bash
# Add to your shell config
echo 'alias ksl="jtlearn"' >> ~/.bashrc
source ~/.bashrc
```

#### 7. Verify & Launch

```bash
jtlearn --version
jtlearn
```

### Linux Distribution Specific

<details>
<summary><strong>Fedora/RHEL</strong></summary>

```bash
sudo dnf install python3 python3-pip git -y
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip3 install -e .
```

</details>

<details>
<summary><strong>Arch Linux</strong></summary>

```bash
sudo pacman -S python python-pip git
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip install -e .
```

</details>

<details>
<summary><strong>openSUSE</strong></summary>

```bash
sudo zypper install python3 python3-pip git
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip3 install -e .
```

</details>

---

## 🍎 macOS

### Prerequisites

| Requirement | Details |
|:---|:---|
| **OS** | macOS 10.15 (Catalina) or later |
| **Access** | Terminal app |

### Step-by-Step Installation

#### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python

```bash
brew install python
```

#### 3. Install Git

```bash
brew install git
```

#### 4. Install jtlearn

```bash
# Clone repository
git clone https://github.com/kashsight/kslearn.git
cd jtlearn

# Install
pip3 install -e .
```

#### 5. Verify & Launch

```bash
jtlearn --version
jtlearn
```

### macOS Troubleshooting

| Problem | Solution |
|:---|:---|
| Permission denied | `pip3 install --user -e .` |
| Command not found | Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` |

---

## 🪟 Windows

### Prerequisites

| Requirement | Details |
|:---|:---|
| **OS** | Windows 10/11 |
| **Access** | Administrator access |

### Method 1: Standard Installation

#### 1. Install Python

1. Download from https://python.org
2. Run installer
3. ✅ **CHECK** "Add Python to PATH"
4. Click "Install Now"

#### 2. Install Git

1. Download from https://git-scm.com/download/win
2. Run installer with default options

#### 3. Install jtlearn

```cmd
# Open Command Prompt or PowerShell
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip install -e .
```

#### 4. Verify & Launch

```cmd
jtlearn --version
jtlearn
```

### Method 2: Windows Subsystem for Linux (WSL)

> **Recommended for better compatibility.**

```powershell
# Install WSL
wsl --install
```

Restart when prompted, then:

```bash
# Open Ubuntu (WSL) from Start Menu
sudo apt update
sudo apt install python3 python3-pip git -y
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip3 install -e .
jtlearn
```

### Windows Troubleshooting

| Problem | Solution |
|:---|:---|
| `pip` not recognized | `python -m pip install -e .` |
| Permission denied | `pip install --user -e .` |
| Long path errors | Enable long paths in Registry (see full guide) |

---

## 📥 Installation Methods

### Comparison

| Method | Pros | Cons | Best For |
|:---|:---:|:---:|:---|
| **Git Clone** | ✅ Easy updates, latest features, smaller download | ❌ Requires Git | Developers, contributors |
| **ZIP Download** | ✅ No Git needed, simple | ❌ Manual updates, larger download | Beginners, one-time users |
| **pip Install** | ✅ Cleanest, PyPI standard | ❌ Not yet available | Future releases |

### Method 1: Git Clone (Recommended)

```bash
git clone https://github.com/kashsight/kslearn.git
cd jtlearn
pip install -e .
```

### Method 2: ZIP Download

1. Go to https://github.com/kashsight/kslearn
2. Click **"Code"** → **"Download ZIP"**
3. Extract ZIP file
4. Open terminal in extracted folder
5. Run: `pip install -e .`

---

## ✅ Verification

### Check Installation

```bash
jtlearn --version
# Should output: jtlearn v2.0.0
```

### Test All Features

| Command | Description |
|:---|:---|
| `jtlearn` | Launch interactive mode |
| `jtlearn study` | Test Study Notes |
| `jtlearn quiz --random` | Test Quiz system |
| `jtlearn brain` | Test Knowledge Brain |
| `jtlearn chat` | Test AI Chat (if tgpt installed) |

### Expected Output

```
╔══════════════════════════════════════════╗
║     ███╗   ██╗███████╗██╗    ██╗███████╗ ║
║     ████╗  ██║██╔════╝██║    ██║██╔════╝ ║
║     ██╔██╗ ██║█████╗  ██║ █╗ ██║███████╗ ║
║     ██║╚██╗██║██╔══╝  ██║███╗██║╚════██║ ║
║     ██║ ╚████║███████╗╚███╔███╔╝███████║ ║
║     ╚═╝  ╚═══╝╚══════╝ ╚══╝╚══╝ ╚══════╝ ║
╚══════════════════════════════════════════╝

📚 Welcome to jtlearn - Your Learning Platform
```

---

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution |
|:---|:---|
| **"pip: command not found"** | `python3 -m pip install -e .` (Linux/macOS) or `python -m pip install -e .` (Windows) |
| **"Permission denied"** | `pip install --user -e .` or use virtual environment |
| **"No module named 'rich'"** | `pip install -r requirements.txt` then `pip install -e . --force-reinstall` |
| **"jtlearn: command not found"** | Add `$HOME/.local/bin` to PATH |
| **Installation hangs** | `pip install --upgrade pip && pip cache purge && pip install -e . --no-cache-dir` |

### Platform-Specific Issues

| Platform | Problem | Solution |
|:---|:---|:---|
| **Termux** | Wheel building failed | `pkg install build-essential libffi -y` |
| **macOS** | Xcode required | `xcode-select --install` |
| **Windows** | Visual C++ required | Download from https://visualstudio.microsoft.com/visual-cpp-build-tools/ |

---

## 🗑️ Uninstallation

### Remove jtlearn

```bash
# Uninstall package
pip uninstall jtlearn

# Remove cloned directory
rm -rf jtlearn  # Linux/macOS
rmdir /s jtlearn  # Windows

# Remove config files
rm -rf ~/.jtlearn
rm ~/.jtlearnrc
```

### Remove Virtual Environment

```bash
rm -rf jtlearn-env  # Linux/macOS
rmdir /s jtlearn-env  # Windows
```

### Remove from PATH

**Linux/macOS:** Edit `~/.bashrc` or `~/.zshrc` and remove:
```bash
alias ksl="jtlearn"
```

**Windows:** Search "Environment Variables" → Edit PATH → Remove jtlearn entries

---

## 📊 Installation Comparison

| Platform | Difficulty | Time | Commands | Notes |
|:---|:---:|:---:|:---:|:---|
| **Termux** | 🟢 Easy | ~2 min | 5 | Fastest setup |
| **Ubuntu** | 🟢 Easy | ~3 min | 6 | Standard Linux |
| **macOS** | 🟢 Easy | ~3 min | 6 | Requires Homebrew |
| **Windows** | 🟡 Medium | ~5 min | 6 | Check PATH option |
| **WSL** | 🟡 Medium | ~5 min | 7 | Best compatibility |

---

## 🎯 Post-Installation

### First Steps

1. **Launch jtlearn:**
   ```bash
   jtlearn
   ```

2. **Take the tour:**
   - Press `H` for Help
   - Explore Study Notes (Option 2)
   - Try a Quiz (Option 3)

3. **Configure settings:**
   - Press `C` → Settings
   - Customize theme, daily goal, AI provider

4. **Start learning!**
   - Begin with Course Catalog (Option 1)
   - Take quizzes to test knowledge
   - Track progress (Option 5)

### Optional Enhancements

| Enhancement | Command/Action |
|:---|:---|
| **Install AI Chat** | See Termux AI section above |
| **Create Desktop Shortcut (Linux)** | Create `.desktop` file in `~/.local/share/applications/` |
| **Create Desktop Shortcut (Windows)** | Point shortcut to `python.exe -m jtlearn` |

---

## 📞 Getting Help

| Resource | Link |
|:---|:---|
| 📖 **Documentation** | See [ADDING_CONTENT.md](ADDING_CONTENT.md) for adding content |
| 🐛 **Bug Reports** | https://github.com/kashsight/kslearn/issues |
| 💬 **Discussions** | https://github.com/kashsight/kslearn/discussions |
| 📧 **Email** | kashsight@gmail.com |
| 🌐 **Website** | https://kash-sight.web.app |

---

<p align="center">
  <sub>📚 jtlearn Documentation • <a href="https://github.com/kashsight/kslearn">GitHub</a> • <a href="https://kash-sight.web.app">Website</a></sub>
</p>
