-- Nebula nvim — a small, readable Neovim setup in the Nebula look (phosphor green).
-- Launched by `nebula nvim` (or the `nv` alias). Your own tweaks go in:
--   $NEBULA_CFG/nvim/user.lua      (survives updates)
if vim.fn.has("nvim-0.9") == 0 then
  vim.api.nvim_echo({ { "Nebula nvim needs Neovim 0.9+. In Termux: pkg upgrade neovim", "ErrorMsg" } }, true, {})
  return
end
-- Plain `nvim` must work without the `nv` launcher: find Nebula from where this config really lives.
if not vim.env.NEBULA_HOME or vim.env.NEBULA_HOME == "" then
  local real = vim.fn.resolve(vim.fn.stdpath("config"))          -- .../nebula/assets/nvim
  local home = vim.fn.fnamemodify(real, ":h:h")
  if vim.fn.filereadable(home .. "/VERSION") == 1 then vim.env.NEBULA_HOME = home end
end
if (not vim.env.NEBULA_CFG or vim.env.NEBULA_CFG == "") and vim.env.NEBULA_HOME then vim.env.NEBULA_CFG = vim.env.NEBULA_HOME .. "/data" end
require("nebula").setup()
