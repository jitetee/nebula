-- GitHub Copilot settings + a doctor. This file runs before the plugin loads, so the globals apply.
local M = {}

-- 1) Use the language server bundled inside copilot.vim. By default it runs through `npx`, which needs npm
--    and network at every start and is the usual reason Copilot "does nothing" on Termux.
if vim.g.copilot_version == nil then vim.g.copilot_version = false end
-- 2) We map <Tab> ourselves (accept Copilot, else completion menu, else a real Tab).
vim.g.copilot_no_tab_map = true
-- Copilot ignores buffers with no filetype ("Disabled for filetype= by internal default"): a fresh :enew buffer is
-- exactly where people try it first, so turn that on.
vim.g.copilot_filetypes = vim.tbl_extend("keep", vim.g.copilot_filetypes or {}, { [""] = true, markdown = true, text = true, gitcommit = true })
-- Termux has no xdg-open: let Copilot's sign-in link open through Termux's own opener.
if vim.g.copilot_browser == nil and vim.fn.executable("termux-open-url") == 1 then vim.g.copilot_browser = { "termux-open-url" } end

-- Accept the visible suggestion. Returns true when something was inserted.
function M.accept()
  if vim.fn.exists("*copilot#Accept") == 0 then return false end
  local ok, keys = pcall(vim.fn["copilot#Accept"], "")
  if ok and type(keys) == "string" and keys ~= "" then
    vim.api.nvim_feedkeys(keys, "n", false)
    return true
  end
  return false
end

vim.keymap.set("i", "<Tab>", function()
  if not M.accept() then vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Tab>", true, false, true), "n", false) end
end, { silent = true, desc = "Accept Copilot / Tab" })     -- cmp replaces this with its own version when loaded
vim.keymap.set("i", "<M-]>", "<Plug>(copilot-next)", { desc = "Next Copilot suggestion" })
vim.keymap.set("i", "<M-[>", "<Plug>(copilot-previous)", { desc = "Previous Copilot suggestion" })
vim.keymap.set("i", "<C-]>", "<Plug>(copilot-dismiss)", { desc = "Dismiss Copilot suggestion" })

-- ── doctor / Copilot window ──────────────────────────────────────────
local function node_version(cmd)
  local out = vim.fn.system({ cmd, "--version" })
  if vim.v.shell_error ~= 0 then return nil end
  return tonumber(out:match("v(%d+)"))
end

local function load_plugin()
  local ok, lazy = pcall(require, "lazy")
  if ok then pcall(lazy.load, { plugins = { "copilot.vim" } }) end
end

function M.report(origin_buf)
  load_plugin()
  local I = require("nebula.icons")
  local L, bad = {}, 0
  local function ok(m) table.insert(L, "  " .. I.ok .. " " .. m) end
  local function no(m, fix) bad = bad + 1; table.insert(L, "  " .. I.bad .. " " .. m); if fix then table.insert(L, "      > " .. fix) end end
  local function info(m) table.insert(L, "  " .. I.note .. " " .. m) end

  local v = vim.version()
  ok(string.format("Neovim %d.%d.%d", v.major, v.minor, v.patch))

  local node = vim.g.copilot_node_command
  if type(node) == "table" then node = node[1] end
  node = node or "node"
  if vim.fn.executable(node) == 0 then
    no("`" .. node .. "` not found (Copilot's server runs on Node.js)", "pkg install nodejs")
  else
    local major = node_version(node)
    if not major then no("`" .. node .. " --version` failed", "reinstall: pkg reinstall nodejs")
    elseif major < 20 then no("Node " .. major .. " is too old", "pkg upgrade nodejs   (or set vim.g.copilot_node_command)")
    else ok("Node " .. major) end
  end

  if vim.g.copilot_version == false then ok("bundled server, no npx")
  else no("copilot_version is set (" .. tostring(vim.g.copilot_version) .. "): the server starts through npx", "remove it, or set vim.g.copilot_version = false in user.lua") end

  if vim.fn.exists(":Copilot") == 2 then
    ok("copilot.vim is loaded")
    if origin_buf and vim.api.nvim_buf_is_valid(origin_buf) then
      local en = vim.api.nvim_buf_call(origin_buf, function() return vim.fn.exists("*copilot#Enabled") == 1 and vim.fn["copilot#Enabled"]() or 0 end)
      local ft = vim.bo[origin_buf].filetype
      if en == 1 then ok("on in this buffer (" .. (ft ~= "" and ft or "no filetype") .. ")")
      else info("off in this buffer (" .. (ft ~= "" and ft or "no filetype") .. ")") end
    end
  else
    local data = vim.fn.stdpath("data") .. "/lazy/copilot.vim"
    if vim.loop.fs_stat(data) then no("copilot.vim is installed but did not load", "restart nvim, then press r here")
    else no("copilot.vim is not installed", "nv plugins   (in the terminal)") end
  end

  local auth = vim.fn.expand("~/.config/github-copilot")
  if vim.loop.fs_stat(auth .. "/apps.json") or vim.loop.fs_stat(auth .. "/hosts.json") then ok("signed in to GitHub")
  else no("not signed in yet", "press  s  below") end

  table.insert(L, "")
  table.insert(L, bad == 0 and "  All good: in insert mode type a comment and wait a second. Tab accepts." or ("  " .. bad .. " thing(s) to fix."))
  return L
end

local function action_lines()
  return { "",
    "  s  sign in to GitHub        p  suggestions panel",
    "  e  turn Copilot on          d  turn Copilot off",
    "  l  show log                 r  refresh        q  close" }
end

function M.window()
  local origin = vim.api.nvim_get_current_buf()
  local lines = M.report(origin)
  for _, l in ipairs(action_lines()) do table.insert(lines, l) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local w = 0
  for _, l in ipairs(lines) do w = math.max(w, vim.fn.strdisplaywidth(l)) end
  w = math.min(w + 2, vim.o.columns - 2)
  local h = math.min(#lines, vim.o.lines - 4)
  local win = vim.api.nvim_open_win(buf, true, { relative = "editor", style = "minimal", border = "rounded",
    title = " " .. require("nebula.icons").sparkle .. " Copilot ", title_pos = "center", width = w, height = h,
    row = math.max(1, math.floor((vim.o.lines - h) / 2) - 1), col = math.floor((vim.o.columns - w) / 2) })
  vim.bo[buf].bufhidden = "wipe"
  vim.wo[win].wrap = true
  local function close() pcall(vim.api.nvim_win_close, win, true) end
  local function run(c) return function() close(); vim.schedule(function() local ok, e = pcall(vim.cmd, c); if not ok then vim.notify("copilot: " .. tostring(e), vim.log.levels.WARN) end end) end end
  local function key(k, fn) vim.keymap.set("n", k, fn, { buffer = buf, nowait = true, silent = true }) end
  key("q", close); key("<Esc>", close)
  key("s", run("Copilot setup")); key("e", run("Copilot enable")); key("d", run("Copilot disable")); key("l", run("Copilot log"))
  key("p", function()
    close()
    vim.schedule(function()
      if vim.bo[origin].buftype ~= "" then vim.notify("copilot: open a real file first, then press p", vim.log.levels.INFO); return end
      pcall(vim.api.nvim_set_current_buf, origin); pcall(vim.cmd, "Copilot panel")
    end)
  end)
  key("r", function() close(); vim.schedule(M.window) end)
end

vim.api.nvim_create_user_command("NebulaCopilot", M.window, { desc = "Copilot window: status, sign in, panel" })

return M
