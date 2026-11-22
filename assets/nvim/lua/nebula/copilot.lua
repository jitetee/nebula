-- GitHub Copilot settings + a doctor. This file runs before the plugin loads, so the globals apply.
local M = {}

-- 1) Use the language server bundled inside copilot.vim. By default it runs through `npx`, which needs npm
--    and network at every start and is the usual reason Copilot "does nothing" on Termux.
if vim.g.copilot_version == nil then vim.g.copilot_version = false end
-- 2) We map <Tab> ourselves (accept Copilot, else completion menu, else a real Tab).
vim.g.copilot_no_tab_map = true
vim.g.copilot_filetypes = vim.tbl_extend("keep", vim.g.copilot_filetypes or {}, { markdown = true, text = true, gitcommit = true })

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

-- ── doctor ───────────────────────────────────────────────────────────
local function node_version(cmd)
  local out = vim.fn.system({ cmd, "--version" })
  if vim.v.shell_error ~= 0 then return nil end
  return tonumber(out:match("v(%d+)"))
end

function M.report()
  local L, bad = {}, 0
  local function ok(m) table.insert(L, "  ✔ " .. m) end
  local function no(m, fix) bad = bad + 1; table.insert(L, "  ✖ " .. m); if fix then table.insert(L, "      → " .. fix) end end
  local function info(m) table.insert(L, "  ℹ " .. m) end

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

  if vim.g.copilot_version == false then ok("using the server bundled with the plugin (no npx)")
  else no("copilot_version is set (" .. tostring(vim.g.copilot_version) .. "): the server starts through npx", "remove it, or set vim.g.copilot_version = false in user.lua") end

  if vim.fn.exists(":Copilot") == 2 then
    ok("copilot.vim is loaded")
  else
    local found = vim.api.nvim_get_runtime_file("plugin/copilot.vim", false)[1]
    local data = vim.fn.stdpath("data") .. "/lazy/copilot.vim"
    if vim.loop.fs_stat(data) then
      info("copilot.vim is installed but loads on first insert — press `i`, then run this again")
    else
      local stray = vim.fn.expand("~/.config/nvim/pack/github/start/copilot.vim")
      if vim.loop.fs_stat(stray) then
        no("copilot.vim sits in ~/.config/nvim/pack/... which this setup never reads (lazy.nvim resets packpath)", "nebula nvim plugins   (installs it the Nebula way)")
      else
        no("copilot.vim is not installed", "nebula nvim plugins")
      end
    end
    if found then info("found: " .. found) end
  end

  local auth = vim.fn.expand("~/.config/github-copilot")
  if vim.loop.fs_stat(auth .. "/apps.json") or vim.loop.fs_stat(auth .. "/hosts.json") then ok("signed in (github-copilot config found)")
  else no("not signed in yet", "run :Copilot setup, open the link it shows, enter the code") end

  table.insert(L, "")
  table.insert(L, bad == 0 and "  All good. In insert mode, type a comment or a function name and wait a second." or
    ("  " .. bad .. " thing(s) to fix. Then try  :Copilot status  and  :Copilot log"))
  return L
end

vim.api.nvim_create_user_command("NebulaCopilot", function()
  local lines = M.report()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local w = 0
  for _, l in ipairs(lines) do w = math.max(w, vim.fn.strdisplaywidth(l)) end
  w = math.min(w + 2, vim.o.columns - 4)
  vim.api.nvim_open_win(buf, true, { relative = "editor", style = "minimal", border = "rounded", title = " Copilot doctor ",
    title_pos = "center", width = w, height = #lines, row = math.max(1, math.floor((vim.o.lines - #lines) / 2) - 1),
    col = math.floor((vim.o.columns - w) / 2) })
  vim.bo[buf].bufhidden = "wipe"
  for _, k in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", k, "<cmd>close<cr>", { buffer = buf, nowait = true }) end
end, { desc = "Check why Copilot is not working" })

return M
