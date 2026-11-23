-- Help inside Neovim, from the same registry as the shell, ant and jtlearn (assets/help.txt + plugin help.txt).
--   :NebulaHelp           Nebula nvim keys + every topic      :NebulaHelp ant   one command's help
--   <leader>hh  help      <leader>hs  search topics           ?  on the start screen
local M = {}

local function disabled()
  local set, home = {}, vim.env.NEBULA_CFG
  if home then
    local f = io.open(home .. "/plugins.disabled", "r")
    if f then for l in f:lines() do if l:match("%S") then set[vim.trim(l)] = true end end f:close() end
  end
  return set
end

function M.plugin_dirs()
  local out, off = {}, disabled()
  for _, root in ipairs({ (vim.env.NEBULA_HOME or "") .. "/plugins", (vim.env.NEBULA_CFG or "") .. "/plugins" }) do
    for _, n in ipairs(vim.fn.isdirectory(root) == 1 and vim.fn.readdir(root) or {}) do
      if not n:match("^[._]") and not off[n] and vim.fn.isdirectory(root .. "/" .. n) == 1 then table.insert(out, root .. "/" .. n) end
    end
  end
  return out
end

function M.load()
  local files = { (vim.env.NEBULA_HOME or "") .. "/assets/help.txt" }
  for _, d in ipairs(M.plugin_dirs()) do
    if vim.fn.filereadable(d .. "/help.txt") == 1 then table.insert(files, d .. "/help.txt") end
  end
  local entries, order = {}, {}
  for _, f in ipairs(files) do
    local cur
    for _, ln in ipairs(vim.fn.filereadable(f) == 1 and vim.fn.readfile(f) or {}) do
      if ln:sub(1, 1) == "@" then
        local p = vim.split(ln:sub(2), "|", { plain = true })
        local name = vim.trim(p[1] or "")
        if entries[name] then cur = nil else
          cur = { name = name, cat = p[2] or "", args = p[3] or "", summary = table.concat(vim.list_slice(p, 4), "|"), detail = {} }
          entries[name] = cur; table.insert(order, name)
        end
      elseif cur and ln:sub(1, 2) == "  " then table.insert(cur.detail, ln:sub(3)) end
    end
  end
  return entries, order
end

local function float(lines, title)
  local b = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(b, 0, -1, false, lines)
  vim.bo[b].bufhidden = "wipe"
  vim.bo[b].filetype = "text"
  local w = math.min(vim.o.columns - 4, 92)
  local h = math.max(3, math.min(#lines + 1, vim.o.lines - 6))
  local win = vim.api.nvim_open_win(b, true, { relative = "editor", style = "minimal", border = "rounded",
    title = " " .. title .. " ", title_pos = "center", width = w, height = h,
    row = math.floor((vim.o.lines - h) / 2) - 1, col = math.floor((vim.o.columns - w) / 2) })
  vim.wo[win].wrap = true
  vim.wo[win].linebreak = true
  for _, k in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", k, function() pcall(vim.api.nvim_win_close, win, true) end, { buffer = b, nowait = true }) end
  return b
end

function M.topic(name)
  local entries = M.load()
  local e = entries[name]
  if not e then vim.notify("nebula: no help for '" .. name .. "'. Try :NebulaHelp", vim.log.levels.WARN); return end
  local lines = { e.name .. " " .. e.args, e.summary, "" }
  for _, d in ipairs(e.detail) do table.insert(lines, d) end
  float(lines, "help: " .. e.name)
end

function M.index()
  local entries, order = M.load()
  local lines = { "Nebula in Neovim  ·  :NebulaHelp <topic> for any Nebula command", "" }
  local nv = entries["nv"]
  if nv then for _, d in ipairs(nv.detail) do table.insert(lines, d) end table.insert(lines, "") end
  table.insert(lines, "Keys:  Space ?  all keys   Space h h  this help   Space h s  search topics   :help nebula")
  table.insert(lines, "AI:    Space a a ask · a e edit · a x explain · a f fix · a g agent · a t Ant terminal")
  table.insert(lines, "")
  local by, cats = {}, {}
  for _, n in ipairs(order) do
    local c = entries[n].cat
    if not by[c] then by[c] = {}; table.insert(cats, c) end
    table.insert(by[c], n)
  end
  for _, c in ipairs(cats) do table.insert(lines, string.format("%-8s %s", c, table.concat(by[c], " "))) end
  float(lines, "Nebula help")
end

function M.search()
  local entries, order = M.load()
  local items = {}
  for _, n in ipairs(order) do table.insert(items, n) end
  vim.ui.select(items, { prompt = "Help topic: ", format_item = function(n) return string.format("%-12s %s", n, entries[n].summary) end },
    function(c) if c then M.topic(c) end end)
end

vim.api.nvim_create_user_command("NebulaHelp", function(o)
  if o.args == "" then M.index() elseif o.args == "keys" then require("nebula.keymaps").cheatsheet() else M.topic(o.args) end
end, { nargs = "?", desc = "Nebula help: any command, keys, AI",
  complete = function() local _, order = M.load(); return vim.list_extend({ "keys" }, order) end })

local map = require("nebula.keymaps").map
map("n", "<leader>hh", M.index, "Help: Nebula in Neovim")
map("n", "<leader>hs", M.search, "Help: search topics")
return M
