-- Keymaps. Every map goes through `map()` so <leader>? can list them (our own tiny which-key).
local M = { list = {} }

local function map(mode, lhs, rhs, desc, extra)
  local opts = vim.tbl_extend("force", { desc = desc, silent = true }, extra or {})
  vim.keymap.set(mode, lhs, rhs, opts)
  table.insert(M.list, { lhs = lhs, desc = desc })
end
M.map = map

-- files / search (telescope when present, built-ins otherwise)
local function tele(fn, fallback)
  return function()
    local ok, b = pcall(require, "telescope.builtin")
    if ok and b[fn] then b[fn]() else vim.cmd(fallback or "echo 'telescope is not installed (nebula nvim plugins)'") end
  end
end
map("n", "<leader>ff", tele("find_files", "edit ."), "Find files")
map("n", "<leader>fg", tele("live_grep"), "Search text (needs ripgrep)")
map("n", "<leader>fb", tele("buffers", "ls"), "Buffers")
map("n", "<leader>fr", tele("oldfiles", "browse oldfiles"), "Recent files")
map("n", "<leader>fh", tele("help_tags", "help"), "Help pages")
map("n", "<leader>e", function() vim.cmd("Lexplore 28") end, "File tree")

-- buffers / windows
map("n", "<S-l>", "<cmd>bnext<cr>", "Next buffer")
map("n", "<S-h>", "<cmd>bprevious<cr>", "Previous buffer")
map("n", "<leader>bd", "<cmd>bdelete<cr>", "Close buffer")
map("n", "<leader>w", "<cmd>write<cr>", "Save")
map("n", "<leader>q", "<cmd>quit<cr>", "Quit window")
map("n", "<C-h>", "<C-w>h", "Window left")
map("n", "<C-j>", "<C-w>j", "Window down")
map("n", "<C-k>", "<C-w>k", "Window up")
map("n", "<C-l>", "<C-w>l", "Window right")
map("n", "<leader>-", "<cmd>split<cr>", "Split below")
map("n", "<leader>|", "<cmd>vsplit<cr>", "Split right")

-- editing
map("n", "<Esc>", "<cmd>nohlsearch<cr>", "Clear search highlight")
map("v", "<", "<gv", "Indent left, keep selection")
map("v", ">", ">gv", "Indent right, keep selection")
map("n", "<A-j>", "<cmd>m .+1<cr>==", "Move line down")
map("n", "<A-k>", "<cmd>m .-2<cr>==", "Move line up")
map("v", "J", ":m '>+1<cr>gv=gv", "Move selection down")
map("v", "K", ":m '<-2<cr>gv=gv", "Move selection up")

-- diagnostics
map("n", "]d", vim.diagnostic.goto_next, "Next diagnostic")
map("n", "[d", vim.diagnostic.goto_prev, "Previous diagnostic")
map("n", "<leader>cd", vim.diagnostic.open_float, "Line diagnostics")

-- Nebula
map("n", "<leader>nc", "<cmd>NebulaCopilot<cr>", "Copilot doctor")
map("n", "<leader>np", "<cmd>Lazy<cr>", "Plugins")
map("n", "<leader>?", function() M.cheatsheet() end, "Keymap cheat sheet")

function M.cheatsheet()
  local lines, w = {}, 0
  for _, k in ipairs(M.list) do
    local l = string.format(" %-12s %s", (k.lhs:gsub("<leader>", "␣")), k.desc)
    w = math.max(w, vim.fn.strdisplaywidth(l)); table.insert(lines, l)
  end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local h = math.min(#lines, vim.o.lines - 6)
  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor", style = "minimal", border = "rounded", title = " Nebula keys ", title_pos = "center",
    width = math.min(w + 2, vim.o.columns - 4), height = h,
    row = math.floor((vim.o.lines - h) / 2) - 1, col = math.floor((vim.o.columns - math.min(w + 2, vim.o.columns - 4)) / 2),
  })
  vim.bo[buf].bufhidden = "wipe"
  for _, key in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", key, "<cmd>close<cr>", { buffer = buf, nowait = true }) end
  return win
end

return M
