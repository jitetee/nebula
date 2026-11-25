-- Plugins via lazy.nvim, kept small and tiered like install/packages.list.
-- Everything is gated: no git → no plugins (the core UI still works); no C compiler → no treesitter.
-- Turn pieces off from $NEBULA_CFG/nvim/user.lua:  vim.g.nebula_disable = { "copilot", "treesitter" }
local M = {}

local function off(name)
  for _, n in ipairs(vim.g.nebula_disable or {}) do if n == name then return true end end
  return false
end
local function has(exe) return vim.fn.executable(exe) == 1 end

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  if not has("git") then
    vim.schedule(function() vim.notify("nebula: git is missing, plugins skipped (pkg install git)", vim.log.levels.WARN) end)
    return M
  end
  local out = vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable",
    "https://github.com/folke/lazy.nvim.git", lazypath })
  if vim.v.shell_error ~= 0 then
    vim.schedule(function() vim.notify("nebula: could not fetch lazy.nvim\n" .. out, vim.log.levels.WARN) end)
    return M
  end
end
vim.opt.rtp:prepend(lazypath)

local spec = {}
local function add(name, s) if not off(name) then table.insert(spec, s) end end

-- fuzzy finder (rg/fd make it faster but are not required)
add("telescope", {
  "nvim-telescope/telescope.nvim", cmd = "Telescope", dependencies = { "nvim-lua/plenary.nvim" },
  opts = { defaults = { prompt_prefix = "❯ ", selection_caret = "❯ ", border = true,
    layout_strategy = vim.o.columns < 100 and "vertical" or "horizontal" } },
})
-- git marks in the gutter + branch name for the statusline
add("gitsigns", {
  "lewis6991/gitsigns.nvim", event = { "BufReadPre", "BufNewFile" },
  opts = { current_line_blame = true, current_line_blame_opts = { delay = 700, virt_text_pos = "eol" },
    current_line_blame_formatter = "  <author> · <author_time:%R>",
    signs = { add = { text = "▎" }, change = { text = "▎" }, delete = { text = "▁" },
    topdelete = { text = "▔" }, changedelete = { text = "▎" } } },
})
-- file tree in Nebula's glyphs (works without devicons)
add("tree", {
  "nvim-tree/nvim-tree.lua", cmd = { "NvimTreeToggle", "NvimTreeFindFile", "NvimTreeOpen" },
  opts = function()
    local I = require("nebula.icons")
    return {
      hijack_cursor = true, sync_root_with_cwd = true, update_focused_file = { enable = true },
      view = { width = vim.o.columns < 80 and 24 or 30, signcolumn = "no" },
      renderer = { group_empty = true, highlight_git = "name", indent_markers = { enable = true },
        icons = { show = { file = true, folder = true, folder_arrow = true, git = true }, git_placement = "after",
          glyphs = { default = I.file, symlink = I.file, folder = { arrow_closed = "▸", arrow_open = "▾", default = I.folder, open = I.folder, empty = I.folder, empty_open = I.folder, symlink = I.folder, symlink_open = I.folder },
            git = { unstaged = "~", staged = "+", unmerged = "!", renamed = "→", untracked = "?", deleted = "x", ignored = "·" } } } },
      filters = { dotfiles = false, custom = { "^.git$", "node_modules", "__pycache__" } },
      git = { ignore = false }, actions = { open_file = { quit_on_open = vim.o.columns < 80 } },
    }
  end,
})
-- syntax highlighting needs a C compiler (Termux: pkg install clang)
M.ts_langs = { "lua", "vimdoc", "bash", "python", "javascript", "json", "markdown", "html", "css" }
if has("cc") or has("gcc") or has("clang") then
  add("treesitter", {
    "nvim-treesitter/nvim-treesitter", branch = "master", build = ":TSUpdate",   -- master builds parsers with just a C compiler (no tree-sitter CLI) event = { "BufReadPost", "BufNewFile" },
    config = function()
      local ok, ts = pcall(require, "nvim-treesitter.configs")
      -- parsers are fetched by `nv plugins` (quietly); nothing is downloaded while you are typing
      if ok then ts.setup({ highlight = { enable = true }, indent = { enable = true } }) end
    end,
  })
end
-- completion (LSP + buffer + path); Copilot ghost text stays separate
add("cmp", {
  "hrsh7th/nvim-cmp", event = "InsertEnter",
  dependencies = { "hrsh7th/cmp-nvim-lsp", "hrsh7th/cmp-buffer", "hrsh7th/cmp-path" },
  config = function()
    local cmp = require("cmp")
    local function tab(fallback)
      if cmp.visible() then return cmp.select_next_item() end
      local okc, cop = pcall(require, "nebula.copilot")
      if okc and cop.accept() then return end
      fallback()
    end
    cmp.setup({
      completion = { completeopt = "menu,menuone,noselect" },
      window = { completion = cmp.config.window.bordered(), documentation = cmp.config.window.bordered() },
      mapping = cmp.mapping.preset.insert({
        ["<C-n>"] = cmp.mapping.select_next_item(), ["<C-p>"] = cmp.mapping.select_prev_item(),
        ["<C-Space>"] = cmp.mapping.complete(), ["<C-e>"] = cmp.mapping.abort(),
        ["<CR>"] = cmp.mapping.confirm({ select = false }),
        ["<Tab>"] = cmp.mapping(tab, { "i", "s" }),
        ["<S-Tab>"] = cmp.mapping(function(fallback) if cmp.visible() then cmp.select_prev_item() else fallback() end end, { "i", "s" }),
      }),
      sources = cmp.config.sources({ { name = "nvim_lsp" }, { name = "path" } }, { { name = "buffer", keyword_length = 3 } }),
    })
  end,
})
-- language servers: only the ones already installed (mason does not work on Termux)
add("lsp", {
  "neovim/nvim-lspconfig", event = { "BufReadPre", "BufNewFile" },
  config = function()
    local servers = {
      lua_ls = "lua-language-server", pyright = "pyright-langserver", ts_ls = "typescript-language-server",
      bashls = "bash-language-server", clangd = "clangd", rust_analyzer = "rust-analyzer", gopls = "gopls",
      html = "vscode-html-language-server", cssls = "vscode-css-language-server", jsonls = "vscode-json-language-server",
    }
    local caps = vim.lsp.protocol.make_client_capabilities()
    local okc, cmp_lsp = pcall(require, "cmp_nvim_lsp")
    if okc then caps = cmp_lsp.default_capabilities(caps) end
    for name, exe in pairs(servers) do
      if has(exe) then
        if vim.lsp.config and vim.lsp.enable then         -- Neovim 0.11+
          vim.lsp.config(name, { capabilities = caps }); vim.lsp.enable(name)
        else
          local ok, lc = pcall(require, "lspconfig")
          if ok and lc[name] then lc[name].setup({ capabilities = caps }) end
        end
      end
    end
    vim.api.nvim_create_autocmd("LspAttach", { callback = function(a)
      local m = require("nebula.keymaps").map
      local function b(lhs, fn, d) m("n", lhs, fn, d, { buffer = a.buf }) end
      b("gd", vim.lsp.buf.definition, "Go to definition"); b("gr", vim.lsp.buf.references, "References")
      b("K", vim.lsp.buf.hover, "Hover docs"); b("<leader>cr", vim.lsp.buf.rename, "Rename")
      b("<leader>ca", vim.lsp.buf.code_action, "Code action"); b("<leader>cf", function() vim.lsp.buf.format({ async = true }) end, "Format")
    end })
  end,
})
-- GitHub Copilot (settings live in nebula/copilot.lua, which loads BEFORE the plugin)
add("copilot", { "github/copilot.vim", event = "InsertEnter", cmd = "Copilot" })

local ok, lazy = pcall(require, "lazy")
if ok then
  lazy.setup(spec, {
    lockfile = vim.fn.stdpath("data") .. "/lazy-lock.json",   -- not inside the Nebula folder
    install = { missing = true },
    checker = { enabled = false }, change_detection = { notify = false },
    ui = { border = "rounded" },
    performance = { rtp = { disabled_plugins = { "gzip", "tarPlugin", "tohtml", "tutor", "zipPlugin" } } },
  })
end
-- called headless by `nv plugins`: build the syntax parsers once
function M.install_parsers()
  local okl, lz = pcall(require, "lazy")
  if not okl then return end
  pcall(lz.load, { plugins = { "nvim-treesitter" } })
  if vim.fn.exists(":TSInstallSync") == 2 then pcall(vim.cmd, "TSInstallSync " .. table.concat(M.ts_langs, " ")) end
end

return M
