# Making Nebula installable with `pkg install nebula`

Termux's `pkg` is a thin wrapper around `apt`. For `pkg install nebula` to work, apt must be able to
find a **`.deb` file listed in a repository** it knows about. There are three ways to get there.
Start with Route A: you control it, it works today, and it costs nothing.

| Route | Who hosts it | Users run | Effort | Approval needed |
| :-- | :-- | :-- | :-- | :-- |
| **A. Your own APT repo** (GitHub Pages) | you | one-time `add-repo.sh`, then `pkg install nebula` | ~30 min, automated by CI | none |
| **B. Termux User Repository (TUR)** | community | `pkg install tur-repo`, then `pkg install nebula` | a pull request | TUR maintainers |
| **C. Official termux-packages** | Termux team | `pkg install nebula` (nothing else) | a pull request + review | Termux maintainers (strict) |

Everything below is already prepared in this repo: `packaging/`, `.github/workflows/`, `install/add-repo.sh`.

---

## How a Termux package is laid out

A `.deb` is an archive whose files are installed **under Termux's prefix**:

```text
/data/data/com.termux/files/usr/opt/nebula/...        the app
/data/data/com.termux/files/usr/bin/nebula            symlink → ../opt/nebula/bin/nebula
```

Rules that matter:

1. **Paths must start with `/data/data/com.termux/files/usr`** (not `/usr`). `packaging/build-deb.sh` does this.
2. **`Architecture: all`** is correct, because Nebula is shell scripts (no compiled code).
3. **`Depends:` uses Termux package names**: `bash, zsh, curl, tar, gawk, jq, ncurses-utils, coreutils, findutils, grep, sed`. (`tput` comes from `ncurses-utils`.)
4. **Your data must not be owned by the package.** Nebula's data lives in `opt/nebula/data`. It is created by `postinst`, never shipped inside the `.deb`, so upgrades and removals never touch it.
5. A package **can't ask questions or edit `~/.zshrc`** during install, so users finish with `nebula setup` (adds the zsh hook, Termux look, package picker). `nebula setup --undo` removes the hooks.
6. Installed with pkg → **`pkg upgrade nebula` updates it**. `nebula update` detects this and tells the user so (use `nebula update --self` to pull from GitHub anyway).

---

## Route A: your own APT repository (recommended)

### 1. Build locally (test)

In Termux or any Linux machine:

```bash
pkg install dpkg dpkg-dev          # Termux; on Debian/Ubuntu: sudo apt install dpkg-dev
bash packaging/build-deb.sh        # → dist/nebula_<version>_all.deb
pkg install ./dist/nebula_0.9.0_all.deb     # try it on your phone
nebula setup
```

### 2. Release with CI (automatic)

The workflow `.github/workflows/release.yml` does everything when you push a tag:

```bash
# 1. bump the version
echo 0.9.1 > VERSION            # and add a section to docs/CHANGELOG.md
git commit -am "Release 0.9.1" && git tag v0.9.1 && git push && git push --tag
```

CI will: check the tag matches `VERSION` → build the `.deb` → create a **GitHub Release** with it →
build an **APT repository** (`packaging/make-repo.sh`) → publish it to the **`gh-pages`** branch.

One-time GitHub setup: *Repo → Settings → Pages → Source: "Deploy from a branch" → `gh-pages` / root.*
Your repository URL is then `https://jitetee.github.io/nebula`.

### 3. (Recommended) sign the repository

Unsigned repos work with `[trusted=yes]`, but signing is the right way:

```bash
gpg --quick-generate-key "Nebula Release <you@example.com>" rsa3072 sign 2y
gpg --armor --export-secret-keys "Nebula Release"     # copy the whole output (private key)
```

Add it in *Repo → Settings → Secrets → Actions* as **`GPG_PRIVATE_KEY`**. CI signs the repo and publishes
`nebula.gpg` next to it. `install/add-repo.sh` automatically uses the key when it exists.

### 4. What your users do

```bash
curl -fsSL https://raw.githubusercontent.com/jitetee/nebula/main/install/add-repo.sh | bash
pkg install nebula
nebula setup
```

or by hand:

```bash
echo "deb [trusted=yes] https://jitetee.github.io/nebula stable main" > $PREFIX/etc/apt/sources.list.d/nebula.list
pkg update && pkg install nebula
```

### 5. Updating and removing

```bash
pkg update && pkg upgrade nebula       # update
nebula setup --undo && pkg uninstall nebula   # remove (your data folder is kept)
```

---

## Route B: Termux User Repository (TUR)

TUR is a community repository for packages the official repo doesn't carry. Users enable it once with `pkg install tur-repo`.

1. Push a tag `v0.9.0` to GitHub and get the source checksum:
   `curl -fsSL https://github.com/jitetee/nebula/archive/refs/tags/v0.9.0.tar.gz | sha256sum`
2. Fork <https://github.com/termux-user-repository/tur>.
3. Copy `packaging/termux-packages/nebula/` to `tur/nebula/` in your fork.
4. Put the checksum in `TERMUX_PKG_SHA256`.
5. Open a pull request; follow their contributing guide and review comments.

## Route C: official `termux-packages`

Same recipe (`packaging/termux-packages/nebula/build.sh`), submitted to <https://github.com/termux/termux-packages>
(copy to `packages/nebula/`). The Termux team is selective: packages should be open source (MIT is fine), useful to many people,
maintained, and must build with their scripts. Read their *CONTRIBUTING* and *packages guide* first. A good plan is to
**start with Route A**, grow users, and apply for B or C once the project is stable.

---

## Checklist before each release

- [ ] `VERSION` bumped, `docs/CHANGELOG.md` updated
- [ ] `bash -n` passes on all scripts (CI does this)
- [ ] `bash packaging/build-deb.sh` works, and `pkg install ./dist/*.deb` works on a real phone
- [ ] `nebula setup` completes on a clean install
- [ ] Tag matches `VERSION` (`v0.9.1`)

## Troubleshooting

| Problem | Fix |
| :-- | :-- |
| `E: Unable to locate package nebula` | `add-repo.sh` didn't run, or `pkg update` wasn't run after adding the repo. Check `cat $PREFIX/etc/apt/sources.list.d/nebula.list`. |
| `404` while updating | GitHub Pages isn't enabled for the `gh-pages` branch, or the first release hasn't finished. |
| `NO_PUBKEY` / signature errors | The repo is signed but the key isn't installed: re-run `add-repo.sh`, or use `[trusted=yes]` while testing. |
| `Depends: X but it is not installable` | A name in `Depends:` isn't a Termux package. Edit `packaging/build-deb.sh`. |
| Installed but `nebula: command not found` | The `/usr/bin/nebula` link is missing: reinstall, or `ln -sf $PREFIX/opt/nebula/bin/nebula $PREFIX/bin/nebula`. |
| Permission denied on `opt/nebula/data` | `chmod 700 $PREFIX/opt/nebula $PREFIX/opt/nebula/data` (postinst does this). |
