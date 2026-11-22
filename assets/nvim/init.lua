-- Nebula nvim — a small, readable Neovim setup in the Nebula look (phosphor green).
-- Launched by `nebula nvim` (or the `nv` alias). Your own tweaks go in:
--   $NEBULA_CFG/nvim/user.lua      (survives updates)
if vim.fn.has("nvim-0.9") == 0 then
  vim.api.nvim_echo({ { "Nebula nvim needs Neovim 0.9+. In Termux: pkg upgrade neovim", "ErrorMsg" } }, true, {})
  return
end
require("nebula").setup()
