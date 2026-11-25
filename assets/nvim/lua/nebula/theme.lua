-- Phosphor-green palette shared with Nebula's terminal UI (lib/skin.py: 48 / 120 / 221 / 203 / 35).
local M = {}

M.c = {
  bg = "#0b120e", bg2 = "#111b15", bg3 = "#18271e", line = "#1d2e23",
  fg = "#d7e6dc", muted = "#7f8f85", border = "#00af5f",
  primary = "#00ff87", second = "#87ff87", accent = "#ffd75f",
  danger = "#ff5f5f", info = "#5fd7ff", purple = "#af87ff", orange = "#ffaf5f",
}

-- `nebula palette <name>` writes $NEBULA_CFG/palette.json; use it when present (same roles as the shell)
do
  local f = (vim.env.NEBULA_CFG or "") .. "/palette.json"
  if vim.fn.filereadable(f) == 1 then
    local ok, p = pcall(vim.json.decode, table.concat(vim.fn.readfile(f), "\n"))
    if ok and type(p) == "table" and p.primary then
      local c = M.c
      c.primary, c.second, c.accent, c.danger = p.primary.hex, p.second.hex, p.accent.hex, p.danger.hex
      c.border, c.fg, c.muted = p.border.hex, p.text.hex, p.muted.hex
      if p.bg then c.bg = p.bg end
    end
  end
end

function M.apply()
  local c = M.c
  vim.cmd("highlight clear")
  if vim.fn.exists("syntax_on") == 1 then vim.cmd("syntax reset") end
  vim.g.colors_name = "nebula"
  vim.o.background = "dark"
  local function hl(g, v) vim.api.nvim_set_hl(0, g, v) end
  local groups = {
    Normal = { fg = c.fg, bg = c.bg }, NormalNC = { fg = c.fg, bg = c.bg }, NormalFloat = { fg = c.fg, bg = c.bg2 },
    FloatBorder = { fg = c.border, bg = c.bg2 }, FloatTitle = { fg = c.primary, bg = c.bg2, bold = true },
    Cursor = { fg = c.bg, bg = c.primary }, CursorLine = { bg = c.bg2 }, CursorLineNr = { fg = c.accent, bold = true },
    LineNr = { fg = "#3d5546" }, SignColumn = { bg = c.bg }, ColorColumn = { bg = c.bg2 },
    Visual = { bg = "#1f3a2b" }, Search = { fg = c.bg, bg = c.accent }, IncSearch = { fg = c.bg, bg = c.primary },
    MatchParen = { fg = c.accent, bold = true, underline = true },
    VertSplit = { fg = c.line }, WinSeparator = { fg = c.line },
    Pmenu = { fg = c.fg, bg = c.bg2 }, PmenuSel = { fg = c.bg, bg = c.primary }, PmenuSbar = { bg = c.bg3 }, PmenuThumb = { bg = c.border },
    StatusLine = { fg = c.fg, bg = c.bg2 }, StatusLineNC = { fg = c.muted, bg = c.bg2 },
    TabLine = { fg = c.muted, bg = c.bg2 }, TabLineSel = { fg = c.bg, bg = c.primary, bold = true }, TabLineFill = { bg = c.bg2 },
    NonText = { fg = "#2a3d31" }, Whitespace = { fg = "#2a3d31" }, EndOfBuffer = { fg = c.bg },
    Folded = { fg = c.muted, bg = c.bg2 }, Directory = { fg = c.primary },
    Title = { fg = c.primary, bold = true }, ErrorMsg = { fg = c.danger }, WarningMsg = { fg = c.accent }, MoreMsg = { fg = c.second },
    -- syntax
    Comment = { fg = c.muted, italic = true }, Constant = { fg = c.orange }, String = { fg = c.second },
    Character = { fg = c.second }, Number = { fg = c.orange }, Boolean = { fg = c.orange },
    Identifier = { fg = c.fg }, Function = { fg = c.primary }, Statement = { fg = c.purple },
    Keyword = { fg = c.purple }, Operator = { fg = c.info }, PreProc = { fg = c.info },
    Type = { fg = c.accent }, Special = { fg = c.info }, Delimiter = { fg = c.muted },
    Todo = { fg = c.bg, bg = c.accent, bold = true }, Error = { fg = c.danger },
    -- diagnostics / git
    DiagnosticError = { fg = c.danger }, DiagnosticWarn = { fg = c.accent }, DiagnosticInfo = { fg = c.info }, DiagnosticHint = { fg = c.second },
    DiagnosticUnderlineError = { undercurl = true, sp = c.danger }, DiagnosticUnderlineWarn = { undercurl = true, sp = c.accent },
    DiffAdd = { bg = "#14301f" }, DiffChange = { bg = "#2a2a14" }, DiffDelete = { fg = c.danger, bg = "#301414" }, DiffText = { bg = "#3a3a18" },
    GitSignsAdd = { fg = c.second }, GitSignsChange = { fg = c.accent }, GitSignsDelete = { fg = c.danger },
    -- treesitter links
    ["@variable"] = { fg = c.fg }, ["@property"] = { fg = c.info }, ["@parameter"] = { fg = c.orange, italic = true },
    ["@function.builtin"] = { fg = c.primary, italic = true }, ["@constructor"] = { fg = c.accent },
    ["@tag"] = { fg = c.primary }, ["@tag.attribute"] = { fg = c.accent }, ["@punctuation"] = { fg = c.muted },
    -- nebula ui
    NebulaMode = { fg = c.bg, bg = c.primary, bold = true }, NebulaModeIns = { fg = c.bg, bg = c.info, bold = true },
    NebulaModeVis = { fg = c.bg, bg = c.purple, bold = true }, NebulaModeCmd = { fg = c.bg, bg = c.accent, bold = true },
    NebulaModeRep = { fg = c.bg, bg = c.danger, bold = true },
    NebulaSL = { fg = c.fg, bg = c.bg2 }, NebulaSLDim = { fg = c.muted, bg = c.bg2 }, NebulaSLGit = { fg = c.second, bg = c.bg2 },
    NebulaSLErr = { fg = c.danger, bg = c.bg2 }, NebulaSLWarn = { fg = c.accent, bg = c.bg2 }, NebulaSLOk = { fg = c.primary, bg = c.bg2 },
    NebulaWinbar = { fg = c.primary, bg = c.bg, bold = true }, NebulaWinbarDim = { fg = c.muted, bg = c.bg },
    WinBar = { fg = c.muted, bg = c.bg }, WinBarNC = { fg = c.muted, bg = c.bg },
    NvimTreeNormal = { fg = c.fg, bg = c.bg2 }, NvimTreeNormalNC = { fg = c.fg, bg = c.bg2 }, NvimTreeEndOfBuffer = { fg = c.bg2, bg = c.bg2 },
    NvimTreeFolderName = { fg = c.primary }, NvimTreeOpenedFolderName = { fg = c.primary, bold = true }, NvimTreeRootFolder = { fg = c.accent, bold = true },
    NvimTreeFolderIcon = { fg = c.border }, NvimTreeIndentMarker = { fg = c.line }, NvimTreeGitDirty = { fg = c.accent }, NvimTreeGitNew = { fg = c.second },
    NvimTreeCursorLine = { bg = c.bg3 }, NvimTreeWinSeparator = { fg = c.line, bg = c.bg2 },
    NebulaDashLogo = { fg = c.primary, bold = true }, NebulaDashTag = { fg = c.muted }, NebulaDashKey = { fg = c.accent }, NebulaDashText = { fg = c.second },
    CopilotSuggestion = { fg = "#4a6a56", italic = true },
  }
  for g, v in pairs(groups) do hl(g, v) end
end

M.apply()
return M
