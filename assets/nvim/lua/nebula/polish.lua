-- The finishing touches: diagnostics look, toast notifications, a path breadcrumb on top of every file.
local I = require("nebula.icons")
local M = {}

-- ── diagnostics: icons in the gutter, a short icon before inline messages, rounded floats ──
local sev = vim.diagnostic.severity
local signs = { [sev.ERROR] = I.error, [sev.WARN] = I.warn, [sev.INFO] = I.info, [sev.HINT] = I.hint }
local cfg = { severity_sort = true, update_in_insert = false, underline = true,
  virtual_text = { prefix = function(d) return signs[d.severity] or "●" end, spacing = 2, source = false },
  float = { border = "rounded", source = true, header = "" } }
if vim.fn.has("nvim-0.10") == 1 then cfg.signs = { text = signs } end
vim.diagnostic.config(cfg)
if vim.fn.has("nvim-0.10") == 0 then
  for s, ic in pairs(signs) do
    local name = ({ [sev.ERROR] = "DiagnosticSignError", [sev.WARN] = "DiagnosticSignWarn", [sev.INFO] = "DiagnosticSignInfo", [sev.HINT] = "DiagnosticSignHint" })[s]
    vim.fn.sign_define(name, { text = ic, texthl = name })
  end
end

-- ── toast notifications: small, top-right, auto-dismiss (replaces the bottom "Press ENTER" messages) ──
local toasts = {}
local lvl_hl = { [vim.log.levels.ERROR] = "DiagnosticError", [vim.log.levels.WARN] = "DiagnosticWarn", [vim.log.levels.INFO] = "NebulaSLOk", [vim.log.levels.DEBUG] = "NebulaSLDim", [vim.log.levels.TRACE] = "NebulaSLDim" }
local lvl_ic = { [vim.log.levels.ERROR] = I.bad, [vim.log.levels.WARN] = I.warn, [vim.log.levels.INFO] = I.note }

local function relayout()
  local row = 1
  for _, t in ipairs(toasts) do
    if vim.api.nvim_win_is_valid(t.win) then
      vim.api.nvim_win_set_config(t.win, { relative = "editor", row = row, col = vim.o.columns - t.w - 1 })
      row = row + t.h + 2
    end
  end
end

local function toast(msg, level)
  level = level or vim.log.levels.INFO
  local maxw = math.max(20, math.min(46, vim.o.columns - 6))
  local lines = {}
  for _, l in ipairs(vim.split(tostring(msg), "\n", { plain = true })) do
    while vim.fn.strdisplaywidth(l) > maxw do
      table.insert(lines, vim.fn.strcharpart(l, 0, maxw)); l = vim.fn.strcharpart(l, maxw)
    end
    table.insert(lines, l)
  end
  while #lines > 6 do table.remove(lines) end
  lines[1] = (lvl_ic[level] or I.note) .. " " .. lines[1]
  local w = 0
  for _, l in ipairs(lines) do w = math.max(w, vim.fn.strdisplaywidth(l)) end
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].bufhidden = "wipe"
  local win = vim.api.nvim_open_win(buf, false, { relative = "editor", style = "minimal", border = "rounded", focusable = false,
    width = w + 1, height = #lines, row = 1, col = math.max(0, vim.o.columns - w - 4), zindex = 250, noautocmd = true })
  vim.wo[win].winhighlight = "Normal:NormalFloat,FloatBorder:" .. (lvl_hl[level] or "FloatBorder")
  local t = { win = win, w = w + 3, h = #lines }
  table.insert(toasts, 1, t)
  relayout()
  vim.defer_fn(function()
    for i, x in ipairs(toasts) do if x == t then table.remove(toasts, i) break end end
    if vim.api.nvim_win_is_valid(win) then pcall(vim.api.nvim_win_close, win, true) end
    relayout()
  end, level >= vim.log.levels.WARN and 6000 or 3000)
end

local real_notify = vim.notify
vim.notify = function(msg, level, opts)
  if vim.in_fast_event() then return vim.schedule(function() toast(msg, level) end) end
  local ok = pcall(toast, msg, level)
  if not ok then real_notify(msg, level, opts) end
end

-- ── breadcrumb: dir › dir › file, only on normal file windows ──
local function crumb()
  local b = vim.api.nvim_get_current_buf()
  if vim.bo[b].buftype ~= "" or vim.api.nvim_win_get_config(0).relative ~= "" then return "" end
  local name = vim.api.nvim_buf_get_name(b)
  if name == "" then return "%#NebulaWinbarDim# " .. I.file .. " [new]" end
  local rel = vim.fn.fnamemodify(name, ":.")
  local parts = vim.split(rel, "/", { plain = true })
  local maxp = vim.o.columns < 70 and 2 or 5
  if #parts > maxp then parts = vim.list_extend({ "…" }, vim.list_slice(parts, #parts - maxp + 2)) end
  local file = table.remove(parts)
  local dirs = #parts > 0 and (table.concat(parts, " › ") .. " › ") or ""
  return "%#NebulaWinbarDim# " .. dirs .. "%#NebulaWinbar#" .. file .. (vim.bo[b].modified and " ●" or "")
end
_G.NebulaWinbar = function() local ok, r = pcall(crumb); return ok and r or "" end
vim.o.winbar = "%{%v:lua.NebulaWinbar()%}"
vim.api.nvim_create_autocmd("FileType", { pattern = { "NvimTree", "help", "qf", "TelescopePrompt", "lazy" }, callback = function() vim.wo.winbar = "" end })

return M
