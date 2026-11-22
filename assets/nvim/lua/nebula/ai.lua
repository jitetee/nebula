-- AI coding in Neovim, powered by Ant (apps/ant). Not a second AI stack: it talks to `python3 -m ant --rpc`,
-- so provider, model, API key, memory and sessions are the ones from the terminal `ant` (~/.ant).
--   <leader>aa  ask about the selection / code around the cursor       (n, v)
--   <leader>ae  edit the selection with an instruction → diff preview   (v)
--   <leader>ax  explain the selection                                   (v)
--   <leader>af  fix the diagnostics on this line / selection            (n, v)
--   <leader>ag  agent: let Ant work on the project (asks before writing or running anything)
--   <leader>at  open the full Ant terminal here     <leader>as  status / which AI is in use
local M = {}
local I = require("nebula.icons")

local job, buf_out, pending, nextid = nil, "", {}, 0
M.busy = 0
M.last = { session = nil }

local function notify(msg, lvl) vim.notify("ant: " .. msg, lvl or vim.log.levels.INFO) end

local function set_busy(d)
  M.busy = math.max(0, M.busy + d)
  vim.g.nebula_ai_busy = M.busy > 0
  vim.schedule(function() pcall(vim.cmd, "redrawstatus") end)
end

local function ant_env()
  local env = {}
  local home = vim.env.NEBULA_HOME
  if home and home ~= "" then env.PYTHONPATH = home .. "/apps/ant" .. (vim.env.PYTHONPATH and (":" .. vim.env.PYTHONPATH) or "") end
  return env
end

local function python()
  for _, p in ipairs({ "python3", "python" }) do if vim.fn.executable(p) == 1 then return p end end
end

local function handle(line)
  local ok, m = pcall(vim.json.decode, line)
  if not ok or type(m) ~= "table" then return end
  local p = pending[m.id]
  if not p then return end
  if m.type == "log" then
    if p.on_log then p.on_log(m.text) end
  elseif m.type == "confirm" then
    local function reply(yes) if job then vim.fn.chansend(job, vim.json.encode({ op = "confirm_reply", cid = m.cid, ok = yes }) .. "\n") end end
    if p.on_confirm then p.on_confirm(m.message, reply) else reply(false) end
  else
    pending[m.id] = nil
    set_busy(-1)
    if m.type == "done" then p.on_done(m) elseif p.on_error then p.on_error(m.message) else notify(m.message, vim.log.levels.ERROR) end
  end
end

local function start()
  if job then return true end
  local py = python()
  if not py then notify("python3 is missing (pkg install python)", vim.log.levels.ERROR); return false end
  job = vim.fn.jobstart({ py, "-m", "ant", "--rpc" }, {
    env = ant_env(), cwd = vim.fn.getcwd(),
    stdout_buffered = false,
    on_stdout = function(_, data)
      for i, chunk in ipairs(data) do
        buf_out = buf_out .. chunk
        if i < #data then
          local line = buf_out; buf_out = ""
          vim.schedule(function() handle(line) end)
        end
      end
    end,
    on_exit = function()
      job = nil
      for id, p in pairs(pending) do pending[id] = nil; set_busy(-1); if p.on_error then vim.schedule(function() p.on_error("ant stopped") end) end end
    end,
  })
  if job <= 0 then job = nil; notify("could not start ant (is apps/ant there? NEBULA_HOME=" .. tostring(vim.env.NEBULA_HOME) .. ")", vim.log.levels.ERROR); return false end
  return true
end

function M.request(req, h)
  if not start() then return end
  nextid = nextid + 1
  req.id = nextid
  pending[nextid] = h
  set_busy(1)
  vim.fn.chansend(job, vim.json.encode(req) .. "\n")
  return nextid
end

function M.stop()
  if job then vim.fn.jobstop(job) end
  notify("stopped")
end

-- ── context ──────────────────────────────────────────────────────────
local function range_lines(opts)
  -- visual mapping: use the live selection; command with a range: use it; otherwise none
  if opts and opts.line1 and opts.range and opts.range > 0 then return opts.line1, opts.line2 end
  local mode = vim.fn.mode()
  if mode == "v" or mode == "V" or mode == "\22" then
    local a, b = vim.fn.line("v"), vim.fn.line(".")
    vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "nx", false)
    return math.min(a, b), math.max(a, b)
  end
end

local function context(s, e)
  local b = vim.api.nvim_get_current_buf()
  local name = vim.api.nvim_buf_get_name(b)
  local c = { file = name ~= "" and vim.fn.fnamemodify(name, ":.") or nil, filetype = vim.bo[b].filetype }
  if s then
    c.selection = table.concat(vim.api.nvim_buf_get_lines(b, s - 1, e, false), "\n")
    c.start, c.end_ = s, e
    c["end"] = e
  else
    local cur = vim.fn.line(".")
    local from, to = math.max(1, cur - 80), math.min(vim.api.nvim_buf_line_count(b), cur + 80)
    c.buffer = table.concat(vim.api.nvim_buf_get_lines(b, from - 1, to, false), "\n")
    c.line = cur
  end
  c.end_ = nil
  local ds, lo, hi = {}, (s or vim.fn.line(".")) - 1, (e or vim.fn.line(".")) - 1
  for _, d in ipairs(vim.diagnostic.get(b)) do
    if d.lnum >= lo and d.lnum <= hi then table.insert(ds, { line = d.lnum + 1, message = d.message }) end
  end
  if #ds > 0 then c.diagnostics = ds end
  return c, b
end

-- ── floating windows ─────────────────────────────────────────────────
local function float(lines, o)
  o = o or {}
  local b = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(b, 0, -1, false, lines)
  vim.bo[b].filetype = o.ft or "markdown"
  vim.bo[b].bufhidden = "wipe"
  local w = math.min(vim.o.columns - 4, o.width or 100)
  local h = math.max(3, math.min(#lines + 1, vim.o.lines - 6))
  local win = vim.api.nvim_open_win(b, true, { relative = "editor", style = "minimal", border = "rounded",
    title = " " .. (o.title or "ant") .. " ", title_pos = "center", width = w, height = h,
    row = math.floor((vim.o.lines - h) / 2) - 1, col = math.floor((vim.o.columns - w) / 2) })
  vim.wo[win].wrap = true
  vim.wo[win].linebreak = true
  for _, k in ipairs({ "q", "<Esc>" }) do vim.keymap.set("n", k, function() pcall(vim.api.nvim_win_close, win, true) end, { buffer = b, nowait = true }) end
  return b, win
end

local function show_answer(text, title)
  local lines = vim.split(text ~= "" and text or "(empty answer)", "\n", { plain = true })
  local b = float(lines, { title = title })
  vim.keymap.set("n", "y", function() vim.fn.setreg("+", text); vim.fn.setreg('"', text); notify("copied") end, { buffer = b, nowait = true })
  vim.keymap.set("n", "p", function() vim.cmd("close"); vim.api.nvim_put(lines, "l", true, true) end, { buffer = b, nowait = true })
end

local function after_hello(cb)
  M.request({ op = "hello" }, { on_done = function(m)
    if not m.has_key then
      notify("no API key for " .. m.provider .. ". Opening Ant: type /setup", vim.log.levels.WARN)
      M.terminal(true)
    else cb(m) end
  end })
end

-- ── actions ──────────────────────────────────────────────────────────
function M.ask(opts, prompt)
  local s, e = range_lines(opts)
  local c = context(s, e)
  local function go(q)
    if not q or q == "" then return end
    after_hello(function(m)
      M.request({ op = "ask", prompt = q, context = c }, { on_done = function(r) show_answer(r.text, "ant · " .. m.model) end })
    end)
  end
  if prompt then go(prompt) else vim.ui.input({ prompt = I.sparkle .. " Ask Ant: " }, go) end
end

function M.explain(opts) M.ask(opts, "Explain this code: what it does, and anything risky or surprising. Be brief.") end

-- show the diff, apply on <CR>/a, drop on q
local function preview_and_apply(b, s, e, old, new, tick)
  local diff = vim.diff(old .. "\n", new .. "\n", { result_type = "unified", ctxlen = 2 })
  if diff == "" then notify("no changes suggested"); return end
  local lines = vim.split(vim.trim(diff), "\n", { plain = true })
  table.insert(lines, "")
  table.insert(lines, "  <CR>/a apply · q discard")
  local pb = float(lines, { ft = "diff", title = "ant edit" })
  local function apply()
    pcall(vim.cmd, "close")
    if not vim.api.nvim_buf_is_valid(b) or vim.api.nvim_buf_get_changedtick(b) ~= tick then notify("buffer changed meanwhile, edit dropped", vim.log.levels.WARN); return end
    vim.api.nvim_buf_set_lines(b, s - 1, e, false, vim.split(new, "\n", { plain = true }))
    notify("applied (u to undo)")
  end
  for _, k in ipairs({ "<CR>", "a" }) do vim.keymap.set("n", k, apply, { buffer = pb, nowait = true }) end
end

function M.edit(opts, instruction)
  local s, e = range_lines(opts)
  if not s then s = vim.fn.line("."); e = s end
  local c, b = context(s, e)
  local tick = vim.api.nvim_buf_get_changedtick(b)
  local function go(q)
    if not q or q == "" then return end
    after_hello(function()
      M.request({ op = "edit", instruction = q, context = c }, { on_done = function(r)
        preview_and_apply(b, s, e, c.selection, (r.text:gsub("\n$", "")), tick)
      end })
    end)
  end
  if instruction then go(instruction) else vim.ui.input({ prompt = I.bolt .. " Edit with Ant: " }, go) end
end

function M.fix(opts)
  local s, e = range_lines(opts)
  local c = context(s, e)
  if not c.diagnostics then notify("no diagnostics here. Use <leader>ae to describe the change."); return end
  local first = c.diagnostics[1].line
  M.edit({ line1 = s or first, line2 = e or first, range = 2 }, "Fix these problems with the smallest change: " .. table.concat(vim.tbl_map(function(d) return d.message end, c.diagnostics), "; "))
end

-- agent: streams its log in a float, asks before anything risky, reloads changed files afterwards
function M.agent(prompt)
  local function go(q)
    if not q or q == "" then return end
    after_hello(function(m)
      local c = context(nil, nil)
      local logs, lb, lw = { "ant is working on: " .. q, "" }, nil, nil
      local function render()
        if not lb or not vim.api.nvim_buf_is_valid(lb) then return end
        vim.api.nvim_buf_set_lines(lb, 0, -1, false, logs)
        if lw and vim.api.nvim_win_is_valid(lw) then vim.api.nvim_win_set_cursor(lw, { #logs, 0 }) end
      end
      lb, lw = float(logs, { ft = "text", title = "ant agent · " .. m.model, width = 110 })
      local last_tool = ""
      M.request({ op = "agent", prompt = q, cwd = vim.fn.getcwd(), mode = "default", context = { file = c.file, filetype = c.filetype } }, {
        on_log = function(t) logs[#logs + 1] = t; if t:find("┃", 1, true) then last_tool = t end; render() end,
        on_confirm = function(msg, reply)
          vim.ui.select({ "Yes, approve", "No, skip" }, { prompt = (last_tool ~= "" and last_tool or msg) }, function(choice) reply(choice ~= nil and choice:sub(1, 1) == "Y") end)
        end,
        on_done = function(r)
          M.last.session = r.session
          logs[#logs + 1] = ""; logs[#logs + 1] = "── done ──"; logs[#logs + 1] = r.text
          if r.session then logs[#logs + 1] = "continue in the terminal:  ant --session " .. r.session end
          render(); pcall(vim.cmd, "checktime")
        end,
        on_error = function(msg) logs[#logs + 1] = "error: " .. tostring(msg); render() end,
      })
    end)
  end
  if prompt then go(prompt) else vim.ui.input({ prompt = I.logo .. " Ant, do: " }, go) end
end

function M.terminal(fresh)
  local py = python()
  if not py then notify("python3 is missing", vim.log.levels.ERROR); return end
  vim.cmd("botright 16new")
  local cmd = { py, "-m", "ant" }
  if not fresh then table.insert(cmd, "-c") end
  vim.fn.termopen(cmd, { env = ant_env(), cwd = vim.fn.getcwd() })
  vim.cmd("startinsert")
end

function M.status()
  M.request({ op = "hello" }, { on_done = function(m)
    notify(string.format("%s · %s · key %s · ant %s", m.provider, m.model, m.has_key and "set" or "MISSING (:AntTerminal then /setup)", m.version))
  end })
end

-- ── commands + keys ──────────────────────────────────────────────────
local cmd = vim.api.nvim_create_user_command
cmd("AntAsk", function(o) M.ask(o, o.args ~= "" and o.args or nil) end, { range = true, nargs = "*", desc = "Ask Ant about the code" })
cmd("AntEdit", function(o) M.edit(o, o.args ~= "" and o.args or nil) end, { range = true, nargs = "*", desc = "Edit the selection with Ant" })
cmd("AntExplain", function(o) M.explain(o) end, { range = true, desc = "Explain the selection" })
cmd("AntFix", function(o) M.fix(o) end, { range = true, desc = "Fix diagnostics with Ant" })
cmd("AntAgent", function(o) M.agent(o.args ~= "" and o.args or nil) end, { nargs = "*", desc = "Let the Ant agent work on the project" })
cmd("AntTerminal", function() M.terminal(false) end, { desc = "Open Ant in a terminal split" })
cmd("AntStatus", function() M.status() end, { desc = "Which AI is Ant using?" })
cmd("AntStop", function() M.stop() end, { desc = "Stop the Ant helper process" })

local map = require("nebula.keymaps").map
map({ "n", "v" }, "<leader>aa", function() M.ask() end, "AI: ask")
map("v", "<leader>ae", function() M.edit() end, "AI: edit selection")
map("n", "<leader>ae", function() M.edit() end, "AI: edit this line")
map("v", "<leader>ax", function() M.explain() end, "AI: explain selection")
map({ "n", "v" }, "<leader>af", function() M.fix() end, "AI: fix diagnostics")
map("n", "<leader>ag", function() M.agent() end, "AI: agent (project)")
map("n", "<leader>at", function() M.terminal(false) end, "AI: Ant terminal")
map("n", "<leader>as", function() M.status() end, "AI: status")

vim.api.nvim_create_autocmd("VimLeavePre", { callback = function() if job then pcall(vim.fn.jobstop, job) end end })
return M
