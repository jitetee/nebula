-- Buffer tabs, trimmed to fit the screen (the current buffer is always visible).
local M = {}

function M.render()
  local cur = vim.api.nvim_get_current_buf()
  local items, idx = {}, 1
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.bo[b].buflisted and vim.api.nvim_buf_is_loaded(b) then
      local name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(b), ":t")
      if name == "" then name = "[new]" end
      if vim.bo[b].modified then name = name .. " ●" end
      table.insert(items, { b = b, text = " " .. name .. " " })
      if b == cur then idx = #items end
    end
  end
  -- window of buffers around the current one so the line never overflows
  local budget, first, last = vim.o.columns - 2, idx, idx
  local used = #(items[idx] and items[idx].text or "")
  while true do
    local grew = false
    if first > 1 and used + #items[first - 1].text <= budget then first = first - 1; used = used + #items[first].text; grew = true end
    if last < #items and used + #items[last + 1].text <= budget then last = last + 1; used = used + #items[last].text; grew = true end
    if not grew then break end
  end
  local out = {}
  for i = first, last do
    local it = items[i]
    table.insert(out, (it.b == cur and "%#TabLineSel#" or "%#TabLine#") .. "%" .. it.b .. "@v:lua.NebulaTabClick@" .. it.text .. "%X")
  end
  return table.concat(out) .. "%#TabLineFill#"
end

_G.NebulaTabClick = function(minwid) if minwid and minwid > 0 then vim.cmd("buffer " .. minwid) end end
_G.NebulaTabline = M.render
vim.o.tabline = "%!v:lua.NebulaTabline()"
return M
