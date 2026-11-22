-- nebula/init.lua — load order: options → theme → keymaps → ui → plugins → user
local M = {}

local function safe(mod)
  local ok, err = pcall(require, mod)
  if not ok then
    vim.schedule(function() vim.notify("nebula: " .. mod .. " failed\n" .. tostring(err), vim.log.levels.WARN) end)
  end
  return ok
end

function M.setup()
  vim.g.mapleader = " "
  vim.g.maplocalleader = ","
  safe("nebula.options")
  safe("nebula.theme")
  safe("nebula.icons")
  safe("nebula.keymaps")
  safe("nebula.statusline")
  safe("nebula.tabline")
  safe("nebula.dashboard")
  safe("nebula.plugins")      -- lazy.nvim + the tiered plugin list (degrades without git)
  safe("nebula.copilot")      -- Copilot settings + :NebulaCopilot doctor
  safe("nebula.ai")           -- Ant-powered AI coding (ask / edit / fix / agent)
  -- user overrides last, so they win
  local cfg = vim.env.NEBULA_CFG
  if cfg and cfg ~= "" then
    local f = cfg .. "/nvim/user.lua"
    if vim.loop.fs_stat(f) then
      local ok, err = pcall(dofile, f)
      if not ok then vim.notify("nebula user.lua: " .. tostring(err), vim.log.levels.WARN) end
    end
  end
end

return M
