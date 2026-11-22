-- Icons. "nebula" adds our own glyphs (Nebula Mono font, assets/fonts/nebula.ttf); "nerd" uses private-use glyphs (FiraCode Nerd / Nebula's own font); "plain" works in any font.
-- Default "auto": nebula when Termux uses Nebula Mono, else nerd. Force one with NEBULA_ICONS=nebula|nerd|plain
-- (env) or  vim.g.nebula_icons = "plain"  in user.lua. Test: :NebulaIcons
local M = {}
local u = vim.fn.nr2char

M.sets = {
  nerd = {
    branch = u(0xE0A0), error = u(0xF057), warn = u(0xF071), info = u(0xF05A), hint = u(0xF0EB),
    copilot = u(0xF4B8), file = u(0xF15B), folder = u(0xF07B), search = u(0xF002), recent = u(0xF1DA),
    new = u(0xF15B), plug = u(0xF1E6), quit = u(0xF011), lock = u(0xF023), git_add = u(0xF055), sep = u(0xE0B1),
    logo = u(0xF135), bolt = u(0xF0E7), sparkle = u(0xF4B8), prompt = u(0xF054), face = u(0xF118), planet = u(0xF0AC),
  },
  plain = {   -- only characters nearly every monospace font has
    branch = "@", error = "x", warn = "!", info = "i", hint = "-", copilot = "*", file = "-", folder = ">",
    search = "/", recent = "~", new = "+", plug = "#", quit = "x", lock = "=", git_add = "+", sep = "|",
    logo = "◉", bolt = "!", sparkle = "*", prompt = "❯", face = "☺", planet = "o",
  },
}
-- Nebula Mono: our own glyphs (U+E400..E405) on top of the nerd set
M.sets.nebula = vim.tbl_extend("force", M.sets.nerd, {
  logo = u(0xE400), bolt = u(0xE401), sparkle = u(0xE402), prompt = u(0xE403), face = u(0xE404), planet = u(0xE405),
  copilot = u(0xE402), plug = u(0xE405),
})

local function font_is_nebula()   -- Termux reads ~/.termux/font.ttf; the installer links it to our font
  local real = vim.loop.fs_realpath(vim.fn.expand("~/.termux/font.ttf"))
  return real ~= nil and real:find("fonts/nebula.ttf", 1, true) ~= nil
end

function M.mode()
  local v = vim.g.nebula_icons or vim.env.NEBULA_ICONS or "auto"
  if v == "0" or v == "off" then v = "plain" end
  if v == "auto" then v = font_is_nebula() and "nebula" or "nerd" end
  return M.sets[v] and v or "nerd"
end

setmetatable(M, { __index = function(_, k) return M.sets[M.mode()][k] end })

vim.api.nvim_create_user_command("NebulaIcons", function()
  local lines = { " Icon test: each row should show symbols, not boxes or ?", "" }
  for _, name in ipairs({ "nebula", "nerd", "plain" }) do
    local s = M.sets[name]
    table.insert(lines, string.format(" %-6s %s %s %s %s %s %s %s %s %s %s", name, s.logo, s.bolt, s.sparkle, s.prompt, s.face, s.planet, s.branch, s.error, s.copilot, s.file))
  end
  table.insert(lines, "")
  table.insert(lines, " Boxes in a row? Pick another:  NEBULA_ICONS=nerd nv  or  NEBULA_ICONS=plain nv")
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local w = 0
  for _, l in ipairs(lines) do w = math.max(w, vim.fn.strdisplaywidth(l)) end
  vim.api.nvim_open_win(buf, true, { relative = "editor", style = "minimal", border = "rounded", title = " Icons ", title_pos = "center",
    width = math.min(w + 2, vim.o.columns - 4), height = #lines, row = 3, col = 2 })
  vim.bo[buf].bufhidden = "wipe"
  for _, k in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", k, "<cmd>close<cr>", { buffer = buf, nowait = true }) end
end, { desc = "Show the icon sets to check your font" })

return M
