-- One global statusline: mode · git branch · file · diagnostics · copilot · filetype · position.
local M = {}
local I = require("nebula.icons")

local modes = {
  n = { "NORMAL", "NebulaMode" }, i = { "INSERT", "NebulaModeIns" }, v = { "VISUAL", "NebulaModeVis" },
  V = { "V-LINE", "NebulaModeVis" }, ["\22"] = { "V-BLOCK", "NebulaModeVis" }, c = { "COMMAND", "NebulaModeCmd" },
  R = { "REPLACE", "NebulaModeRep" }, t = { "TERMINAL", "NebulaModeIns" }, s = { "SELECT", "NebulaModeVis" },
}

local function diag()
  local e = #vim.diagnostic.get(0, { severity = vim.diagnostic.severity.ERROR })
  local w = #vim.diagnostic.get(0, { severity = vim.diagnostic.severity.WARN })
  local out = ""
  if e > 0 then out = out .. "%#NebulaSLErr# " .. I.error .. " " .. e end
  if w > 0 then out = out .. "%#NebulaSLWarn# " .. I.warn .. " " .. w end
  return out
end

local function git()
  local b = vim.b.gitsigns_head
  if b and b ~= "" then return "%#NebulaSLGit# " .. I.branch .. " " .. b .. " " end
  return ""
end

local function ai()
  if vim.g.nebula_ai_busy then return "%#NebulaSLWarn# " .. I.bolt .. " ant… " end
  return ""
end

local function copilot()
  if vim.g.loaded_copilot ~= 1 and vim.fn.exists("*copilot#Enabled") == 0 then return "" end
  local ok, on = pcall(vim.fn["copilot#Enabled"])
  if ok and on == 1 then return "%#NebulaSLOk# " .. I.copilot .. " " end
  return "%#NebulaSLDim# " .. I.copilot .. " "
end

function M.render()
  local m = modes[vim.fn.mode()] or { vim.fn.mode():upper(), "NebulaMode" }
  local narrow = vim.o.columns < 60
  local parts = {
    "%#" .. m[2] .. "# " .. I.logo .. " " .. (narrow and m[1]:sub(1, 1) or m[1]) .. " ",
    git(),
    "%#NebulaSL# %t%m%r ",
    diag(),
    "%=",
    ai(),
    copilot(),
    narrow and "" or ("%#NebulaSLDim# " .. (vim.bo.filetype ~= "" and vim.bo.filetype or "no ft") .. " "),
    "%#NebulaSL# %l:%c ",
    "%#" .. m[2] .. "# %p%% ",
  }
  return table.concat(parts)
end

_G.NebulaStatusline = function() local ok, r = pcall(M.render); return ok and r or " nebula " end
vim.o.statusline = "%!v:lua.NebulaStatusline()"
return M
