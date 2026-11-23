-- Nebula plugins can ship Neovim code: <plugin>/nvim.lua (bundled plugins/ or $NEBULA_CFG/plugins/).
-- A broken one never stops Neovim from starting.
for _, d in ipairs(require("nebula.help").plugin_dirs()) do
  local f = d .. "/nvim.lua"
  if vim.fn.filereadable(f) == 1 then
    local ok, err = pcall(dofile, f)
    if not ok then vim.notify("nebula plugin " .. vim.fn.fnamemodify(d, ":t") .. ": " .. tostring(err), vim.log.levels.WARN) end
  end
end
return {}
