local o = vim.opt
o.termguicolors = true
o.number = true
o.relativenumber = true
o.cursorline = true
o.signcolumn = "yes"
o.mouse = "a"                       -- phone touch scrolling / selecting
o.clipboard = vim.env.TERMUX_VERSION and "" or "unnamedplus"
o.ignorecase = true
o.smartcase = true
o.splitright = true
o.splitbelow = true
o.expandtab = true
o.shiftwidth = 2
o.tabstop = 2
o.smartindent = true
o.wrap = false
o.scrolloff = 4
o.sidescrolloff = 8
o.undofile = true
o.updatetime = 250
o.timeoutlen = 400
o.completeopt = { "menu", "menuone", "noselect" }
o.laststatus = 3                    -- one global statusline (saves a row on small screens)
o.showmode = false                  -- the statusline shows the mode
o.showtabline = 2
o.cmdheight = 1
o.pumheight = 10
o.list = true
o.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
o.fillchars = { eob = " ", vert = "│" }
o.shortmess:append("cI")
-- small screens: fewer columns of chrome
if vim.o.columns < 60 then
  o.relativenumber = false
  o.signcolumn = "number"
end
