-- Start screen (only when nvim is opened with no file). Reads the same logo style as `nebula banner`.
local logo = {
  "███╗   ██╗███████╗██████╗ ██╗   ██╗██╗      █████╗ ",
  "████╗  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔══██╗",
  "██╔██╗ ██║█████╗  ██████╔╝██║   ██║██║     ███████║",
  "██║╚██╗██║██╔══╝  ██╔══██╗██║   ██║██║     ██╔══██║",
  "██║ ╚████║███████╗██████╔╝╚██████╔╝███████╗██║  ██║",
  "╚═╝  ╚═══╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝",
}
local small = { "N E B U L A" }
local I = require("nebula.icons")
local function find_files()
  local ok, b = pcall(require, "telescope.builtin")
  if ok then b.find_files() else vim.cmd("edit .") end
end
local items = {
  { "f", "Find file", find_files, I.search },
  { "r", "Recent files", "<cmd>browse oldfiles<cr>", I.recent },
  { "n", "New file", "<cmd>enew<cr>", I.new },
  { "p", "Plugins", "<cmd>Lazy<cr>", I.plug },
  { "c", "Copilot doctor", "<cmd>NebulaCopilot<cr>", I.copilot },
  { "q", "Quit", "<cmd>qa<cr>", I.quit },
}

local function show()
  if vim.fn.argc() > 0 or vim.api.nvim_buf_get_name(0) ~= "" or vim.bo.modified then return end
  if vim.api.nvim_buf_line_count(0) > 1 or #vim.api.nvim_buf_get_lines(0, 0, 1, false)[1] > 0 then return end
  local buf = vim.api.nvim_get_current_buf()
  local art = vim.o.columns >= 56 and logo or small
  local lines, marks = {}, {}
  local function add(text, hl) table.insert(lines, text); table.insert(marks, hl) end
  for _, l in ipairs(art) do add(l, "NebulaDashLogo") end
  add("", nil)
  add("Neovim, the Nebula way  ·  v" .. (vim.fn.readfile((vim.env.NEBULA_HOME or "") .. "/VERSION", "", 1)[1] or ""), "NebulaDashTag")
  add("", nil)
  for _, it in ipairs(items) do add(string.format("%s  %s  %s", it[4], it[1], it[2]), "NebulaDashText") end

  local w = 0
  for _, l in ipairs(lines) do w = math.max(w, vim.fn.strdisplaywidth(l)) end
  local pad_top = math.max(0, math.floor((vim.o.lines - #lines) / 3))
  local pad_left = math.max(0, math.floor((vim.o.columns - w) / 2))
  local out = {}
  for _ = 1, pad_top do table.insert(out, "") end
  for _, l in ipairs(lines) do table.insert(out, string.rep(" ", pad_left) .. l) end

  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, out)
  for i, hl in ipairs(marks) do
    if hl then vim.api.nvim_buf_add_highlight(buf, -1, hl, pad_top + i - 1, 0, -1) end
  end
  for _, it in ipairs(items) do
    vim.keymap.set("n", it[1], it[3], { buffer = buf, nowait = true, silent = true })
  end
  vim.bo[buf].modifiable = false
  vim.bo[buf].buftype = "nofile"
  vim.bo[buf].bufhidden = "wipe"
  vim.bo[buf].buflisted = false
  vim.bo[buf].swapfile = false
  vim.wo.number, vim.wo.relativenumber, vim.wo.cursorline, vim.wo.list, vim.wo.signcolumn = false, false, false, false, "no"
end

vim.api.nvim_create_autocmd("VimEnter", { once = true, callback = function() vim.schedule(show) end })
return {}
