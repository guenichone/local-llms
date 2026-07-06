#!/bin/bash
#
# Claude Code Custom Status Line
# Pricing inspired by bvarhegyi/status-line (git.pictet.io)
#
# Line 1: [Model] ~/path:branch commit* +added/-removed
# Line 2: session:<name>   (only when session is named)
# Line 3: [context bricks] pct (k/k) ↻compact% duration session:$X.XX/Max  today:$X.XX  month:$X.XX (avg $/d)  5h:xx%(...) 7d:xx%(...)
#
# Rate-limit slots color by pace ratio (usage% / time-elapsed%):
#   <80 green · 80-105 default · 105-120 yellow · 120-140 orange · >=140 red
#   Usage >=95% is always red regardless of pace.
#
# Pricing (line 4) is computed locally from Claude Code's own per-session
# total_cost_usd (which already includes subagent calls). Each refresh
# upserts {session_id, date, cost_usd} into ~/.claude/statusline-costs.jsonl.
# Entries older than COST_LOG_RETENTION_DAYS (default 90) are pruned on write.
# No network, no external dependencies beyond jq. Note: counts only accrue
# for sessions where the statusline has run — no retroactive data.

input=$(cat)
cols="${STATUSLINE_COLS:-}"
if [[ -z "$cols" ]]; then
    cols=$(stty size < /dev/tty 2>/dev/null | awk '{print $2}')
    [[ "$cols" =~ ^[0-9]+$ ]] && [[ $cols -gt 0 ]] || cols=$(tput cols 2>/dev/null)
    [[ "$cols" =~ ^[0-9]+$ ]] && [[ $cols -gt 0 ]] || cols=200
fi

# Parse core data
model_raw=$(echo "$input" | jq -r '.model.display_name // "Claude"')
model=$(echo "$model_raw" | sed 's/Claude //')
is_local=false
echo "$model_raw" | grep -qiE "llamacpp|ornith|gguf|local" && is_local=true
current_dir=$(echo "$input" | jq -r '.workspace.current_dir // env.PWD')
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_removed=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')
folder_path="${current_dir/#$HOME/~}"

# Git info
cd "$current_dir" 2>/dev/null || cd "$HOME"
if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null || echo "detached")
    commit_short=$(git rev-parse --short HEAD 2>/dev/null || echo "")
    commit_msg=$(git log -1 --pretty=%s 2>/dev/null | cut -c1-30 || echo "")
    git_status=""
    [[ -n $(git status --porcelain 2>/dev/null) ]] && git_status="*"
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)
    if [[ -n "$upstream" ]]; then
        ahead=$(git rev-list --count "$upstream"..HEAD 2>/dev/null || echo "0")
        behind=$(git rev-list --count HEAD.."$upstream" 2>/dev/null || echo "0")
        [[ "$ahead" -gt 0 ]] && git_status="${git_status}↑${ahead}"
        [[ "$behind" -gt 0 ]] && git_status="${git_status}↓${behind}"
    fi
else
    branch=""; commit_short=""; commit_msg=""; git_status=""
fi

# Context window
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
duration_hours=$((duration_ms / 3600000))
duration_min=$(((duration_ms % 3600000) / 60000))
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
total_tokens=$(echo "$input" | jq -r '.context_window.context_window_size // 200000')
current_usage=$(echo "$input" | jq -r '.context_window.current_usage // null')

if [[ "$current_usage" != "null" ]]; then
    input_tokens=$(echo "$current_usage" | jq -r '.input_tokens // 0')
    cache_creation=$(echo "$current_usage" | jq -r '.cache_creation_input_tokens // 0')
    cache_read=$(echo "$current_usage" | jq -r '.cache_read_input_tokens // 0')
    used_tokens=$((input_tokens + cache_creation + cache_read))
else
    used_tokens=0
fi

free_tokens=$((total_tokens - used_tokens))
usage_pct=$(( total_tokens > 0 ? (used_tokens * 100) / total_tokens : 0 ))
autocompact_buffer=45000
autocompact_threshold=$((total_tokens - autocompact_buffer))
remaining_before_compact=$((autocompact_threshold - used_tokens))
[[ $remaining_before_compact -lt 0 ]] && remaining_before_compact=0
remaining_pct=$(( total_tokens > 0 ? remaining_before_compact * 100 / total_tokens : 0 ))
used_k=$(( used_tokens / 1000 ))
total_k=$(( total_tokens / 1000 ))

# Rate limits
rl_5h=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
rl_5h_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
rl_7d=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
rl_7d_resets=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

# Session
session_id=$(echo "$input" | jq -r '.session_id // ""')
session_name=$(echo "$input" | jq -r '.session_name // ""')

# ── LINE 1: budget-based construction ──
# Target: line1 visual width ≤ 85% of cols. If line1 approaches cols, Claude
# Code renders "…" at the right margin AND drops the second status line.
#
# Priority (hide first → hide last):
#   1. +lines/-lines (hide first — least important, can be long like "+489/-1234")
#   2. commit hash + git_status
#   3. branch name (truncate from the right with "…" before hiding)
#   4. path (full → "…/basename" before any other truncation)
#   5. [Model]  ALWAYS shown (may itself be long like "[Opus 4.7 (1M context)]")

target_len=$(( cols * 85 / 100 ))
basename_path="…/$(basename "$folder_path")"
lines_str="+${lines_added}/-${lines_removed}"
have_lines=0; [[ "$lines_added" -gt 0 || "$lines_removed" -gt 0 ]] && have_lines=1
have_commit=0; [[ -n "$commit_short" ]] && have_commit=1
gs_len=${#git_status}
model_seg_len=$(( 2 + ${#model} + 1 ))  # "[model] "
# "…" (U+2026) takes 2 visual columns in most terminals (East Asian Width = Ambiguous
# rendered wide by default in Warp/iTerm), but bash's ${#string} counts it as 1 char.
# We add +1 to the length whenever we include a "…" so the budget math uses visual cols.
basename_vlen=$(( ${#basename_path} + 1 ))   # one "…" in "…/basename"

# Upgrade to full path only if EVERY element still fits (never sacrifice info for path decoration)
lm_short=$(( model_seg_len + basename_vlen ))
[[ -n "$branch" ]] && lm_short=$(( lm_short + 1 + ${#branch} ))
lm_short=$(( lm_short + gs_len ))
[[ $have_commit -eq 1 ]] && lm_short=$(( lm_short + 1 + ${#commit_short} ))
[[ $have_lines -eq 1 ]] && lm_short=$(( lm_short + 1 + ${#lines_str} ))
lm_full=$(( lm_short - basename_vlen + ${#folder_path} ))

if [[ $lm_full -le $target_len ]]; then
    display_path="$folder_path"
    path_vlen=${#folder_path}
else
    display_path="$basename_path"
    path_vlen=$basename_vlen
fi

used=$(( model_seg_len + path_vlen ))

# Branch: full if it fits, else truncate with "…" (which itself costs 2 visual cols)
display_branch=""
branch_vlen=0
if [[ -n "$branch" ]]; then
    branch_budget=$(( target_len - used - 1 - gs_len ))  # -1 for ":"
    if [[ ${#branch} -le $branch_budget ]]; then
        display_branch="$branch"
        branch_vlen=${#branch}
    elif [[ $branch_budget -ge 5 ]]; then
        # "…" = 2 visual cols → keep (budget - 2) chars of branch + "…"
        display_branch="${branch:0:$((branch_budget - 2))}…"
        branch_vlen=$branch_budget  # exactly at budget
    fi
    [[ -n "$display_branch" ]] && used=$(( used + 1 + branch_vlen ))
fi
used=$(( used + gs_len ))

# Commit (only if it fits after branch is placed)
show_commit=0
if [[ $have_commit -eq 1 ]] && [[ $(( used + 1 + ${#commit_short} )) -le $target_len ]]; then
    show_commit=1
    used=$(( used + 1 + ${#commit_short} ))
fi

# +lines/-lines (only if it fits last)
show_lines=0
if [[ $have_lines -eq 1 ]] && [[ $(( used + 1 + ${#lines_str} )) -le $target_len ]]; then
    show_lines=1
fi

line1="\033[1;36m[$model]\033[0m "
line1+="\033[1;32m$display_path\033[0m"
[[ -n "$display_branch" ]] && line1+=":\033[1;34m$display_branch\033[0m"
[[ $show_commit -eq 1 ]] && line1+=" \033[1;33m$commit_short\033[0m"
[[ -n "$git_status" ]] && line1+="\033[1;31m$git_status\033[0m"
[[ $show_lines -eq 1 ]] && line1+=" \033[0;32m+$lines_added\033[0m/\033[0;31m-$lines_removed\033[0m"

# ── LINE 2: session (only if named) ──
line2=""
if [[ -n "$session_name" ]]; then
    line2+="\033[2;37msession:\033[0m \033[1;37m$session_name\033[0m"
fi

# ── LINE 3: [context bricks] pct | compact | duration | cost/max | rate limits ──

# Bricks (20 for compact display)
total_bricks=20
used_bricks=$(( total_tokens > 0 ? (used_tokens * total_bricks) / total_tokens : 0 ))
compact_brick=$(( total_tokens > 0 ? (autocompact_threshold * total_bricks) / total_tokens : 19 ))
warning_brick=$(( (compact_brick * 90) / 100 ))
danger_brick=$(( (compact_brick * 95) / 100 ))

# Context percentage + size
# Detect degrading threshold: 50% on 200k models, 400k on 1M models
if [[ $total_tokens -ge 500000 ]]; then
    ctx_degrade_threshold=400000
else
    ctx_degrade_threshold=$(( total_tokens / 2 ))
fi
if [[ $used_tokens -ge $ctx_degrade_threshold ]]; then
    ctx_token_color="\033[38;5;214m"  # light orange — context degrading
else
    ctx_token_color="\033[0m"
fi

degrade_brick=$(( total_tokens > 0 ? (ctx_degrade_threshold * total_bricks) / total_tokens : total_bricks ))

bar="["
for ((i=0; i<total_bricks; i++)); do
    if [[ $i -eq $compact_brick ]]; then
        bar+="\033[1;33m|\033[0m"
    elif [[ $i -lt $used_bricks ]]; then
        if [[ $i -ge $danger_brick ]]; then
            bar+="\033[0;31m■\033[0m"
        elif [[ $i -ge $warning_brick ]]; then
            bar+="\033[0;33m■\033[0m"
        elif [[ $i -ge $degrade_brick ]]; then
            bar+="\033[38;5;214m■\033[0m"
        else
            bar+="\033[0;36m■\033[0m"
        fi
    else
        bar+="\033[2;37m□\033[0m"
    fi
done
bar+="]"
line3="${bar} \033[1m${usage_pct}%\033[0m"
[[ $cols -ge 95 ]] && line3+=" ${ctx_token_color}(${used_k}k/${total_k}k)\033[0m"

# Compact status (short)
if [[ $remaining_pct -gt 10 ]]; then
    line3+=" \033[1;32m↻${remaining_pct}%\033[0m"
elif [[ $remaining_pct -gt 0 ]]; then
    line3+=" \033[1;33m↻${remaining_pct}%\033[0m"
else
    line3+=" \033[1;31m↻now\033[0m"
fi

# Duration (compact, skip 0h)
if [[ $duration_hours -gt 0 ]]; then
    line3+=" ${duration_hours}h${duration_min}m"
else
    line3+=" ${duration_min}m"
fi

# Session cost or Max (skip for local models — free)
if ! $is_local; then
# CLAUDE_STATUSLINE_IS_MAX=1 forces Max mode (set in shell profile when on a Max subscription)
is_max=false
if [[ "${CLAUDE_STATUSLINE_IS_MAX:-0}" == "1" ]]; then
    is_max=true
elif command -v bc &>/dev/null; then
    if (( $(echo "$cost_usd > 0" | bc -l 2>/dev/null || echo "0") )); then
        line3+=" \033[2;37msession:\033[0m\033[0;33m\$$(printf '%.2f' "$cost_usd")\033[0m"
    else
        is_max=true
    fi
else
    if [[ "$cost_usd" != "0" && "$cost_usd" != "0.0" && "$cost_usd" != "0.00" && -n "$cost_usd" ]]; then
        line3+=" \033[2;37msession:\033[0m\033[0;33m\$${cost_usd}\033[0m"
    else
        is_max=true
    fi
fi
$is_max && line3+=" \033[1;35mMax\033[0m"

# Rate limits (label in dim white, percentage colored by pace ratio, countdown timer in dim)
_rl_countdown() {
    local resets_at="$1"
    local now
    now=$(date +%s)
    local diff=$(( resets_at - now ))
    [[ $diff -le 0 ]] && echo "now" && return
    local s=$(( diff % 60 ))
    local m=$(( (diff % 3600) / 60 ))
    local h=$(( (diff % 86400) / 3600 ))
    local d=$(( diff / 86400 ))
    if [[ $d -gt 0 ]]; then
        printf '%dd%dh' "$d" "$h"
    elif [[ $h -gt 0 ]]; then
        printf '%dh%02dm' "$h" "$m"
    elif [[ $m -gt 0 ]]; then
        printf '%dm' "$m"
    else
        printf '%ds' "$s"
    fi
}

# Returns an ANSI color escape for a rate-limit slot based on pace ratio.
# Args: usage_percent resets_at window_seconds
_rl_pace_color() {
    local usage_pct="$1"
    local resets_at="$2"
    local window_sec="$3"
    local now
    now=$(date +%s)
    local remaining_sec=$(( resets_at - now ))
    [[ $remaining_sec -lt 0 ]] && remaining_sec=0
    local elapsed_sec=$(( window_sec - remaining_sec ))
    # time_elapsed_percent (integer, 0-100)
    local time_elapsed_pct=$(( window_sec > 0 ? (elapsed_sec * 100) / window_sec : 0 ))

    # Always red if usage > 95
    if (( $(printf '%.0f' "$usage_pct") >= 95 )); then
        printf '\033[31m'
        return
    fi

    # No color if very early in window (< 5% elapsed)
    if (( time_elapsed_pct < 5 )); then
        printf '\033[0m'
        return
    fi

    # pace_ratio = usage_pct / time_elapsed_pct (scaled *100 to stay integer).
    # Equivalent to projected final usage if current pace continues.
    # pace_x100: <80 → green, 80-105 → default (on pace, small buffer),
    #            105-120 → yellow, 120-140 → orange, ≥140 → red.
    local usage_int
    usage_int=$(printf '%.0f' "$usage_pct")
    local pace_x100=$(( (usage_int * 100) / time_elapsed_pct ))

    if (( pace_x100 < 80 )); then
        printf '\033[32m'
    elif (( pace_x100 < 105 )); then
        printf '\033[0m'
    elif (( pace_x100 < 120 )); then
        printf '\033[33m'
    elif (( pace_x100 < 140 )); then
        printf '\033[38;5;208m'
    else
        printf '\033[31m'
    fi
}

# Rate-limit slots apply to Max subscribers only. When the session shows an
# API cost (pay-per-token), hide the 5h/7d slots — they are not meaningful.
rl=""
if $is_max; then
    if [[ -n "$rl_5h" && -n "$rl_5h_resets" ]]; then
        v=$(printf '%.0f' "$rl_5h")
        color=$(_rl_pace_color "$rl_5h" "$rl_5h_resets" 18000)
        countdown=$(_rl_countdown "$rl_5h_resets")
        rl+="\033[2;37m5h:${color}${v}%\033[0m"
        [[ $cols -ge 130 ]] && rl+="\033[2;37m(${countdown})\033[0m"
    elif [[ -n "$rl_5h" ]]; then
        v=$(printf '%.0f' "$rl_5h")
        rl+="\033[2;37m5h:\033[0m${v}%\033[0m"
    fi
    if [[ -n "$rl_7d" && -n "$rl_7d_resets" ]]; then
        v=$(printf '%.0f' "$rl_7d")
        color=$(_rl_pace_color "$rl_7d" "$rl_7d_resets" 604800)
        countdown=$(_rl_countdown "$rl_7d_resets")
        [[ -n "$rl" ]] && rl+=" "
        rl+="\033[2;37m7d:${color}${v}%\033[0m"
        [[ $cols -ge 130 ]] && rl+="\033[2;37m(${countdown})\033[0m"
    elif [[ -n "$rl_7d" ]]; then
        v=$(printf '%.0f' "$rl_7d")
        [[ -n "$rl" ]] && rl+=" "
        rl+="\033[2;37m7d:\033[0m${v}%\033[0m"
    fi
fi
[[ -n "$rl" ]] && line3+=" $rl"
fi

# ── Today / month-to-date spend (local accumulator, appended to line 3) ──
#
# Schema: {session_id, date, cost_at_day_start, cost_usd, month, month_cost}
#
#   cost_at_day_start  session's total_cost_usd at the start of the current day
#   cost_usd           session's current total_cost_usd (authoritative, from Claude Code)
#   month_cost         cumulative spend from this session in the current month
#
# today  = sum(cost_usd - cost_at_day_start) across all entries where date=today
# month  = sum(month_cost)                   across all entries where month=current
#
# Day rollover:  cost_at_day_start ← prior cost_usd; month_cost accumulates delta
# Month rollover: month_cost resets to today's delta only
# First-seen old session (duration > elapsed since midnight): cost_at_day_start ← cost_usd
#   so its historical cost does NOT inflate today — only new spend from this point counts
# Migration: old-schema entries (no cost_at_day_start) are rebased on next refresh
COST_LOG="${STATUSLINE_COST_LOG:-${HOME}/.claude/statusline-costs.jsonl}"
COST_LOG_RETENTION_DAYS=90
COST_THRESHOLD_DAILY=15

if ! $is_local && [[ -n "$session_id" ]]; then
    today=$(date +%Y-%m-%d)
    month=$(date +%Y-%m)
    day_of_month=$(date +%-d)
    # Count weekdays elapsed so far this month (Mon–Fri), including today
    weekdays_elapsed=0
    for (( _d=1; _d<=day_of_month; _d++ )); do
        _dstr="${month}-$(printf '%02d' $_d)"
        _dow=$(date -j -f "%Y-%m-%d" "$_dstr" +%u 2>/dev/null \
            || date -d "$_dstr" +%u 2>/dev/null)
        [[ "$_dow" -le 5 ]] && (( weekdays_elapsed++ )) || true
    done
    [[ "$weekdays_elapsed" -lt 1 ]] && weekdays_elapsed=1
    cutoff=$(date -v -${COST_LOG_RETENTION_DAYS}d +%Y-%m-%d 2>/dev/null \
        || date -d "${COST_LOG_RETENTION_DAYS} days ago" +%Y-%m-%d 2>/dev/null \
        || echo "1970-01-01")

    session_cost=$(printf '%s' "$cost_usd" | awk '{printf "%.6f", $0+0}')
    mkdir -p "$(dirname "$COST_LOG")" 2>/dev/null

    if [[ -n "$session_cost" && "$session_cost" != "0.000000" ]]; then
        prior=$(grep -F "\"session_id\":\"${session_id}\"" "$COST_LOG" 2>/dev/null | tail -1)

        needs_write=false
        day_start="0.000000"
        month_acc="0.000000"

        if [[ -z "$prior" ]] || ! printf '%s' "$prior" | jq -e 'has("cost_at_day_start")' &>/dev/null; then
            # New session or old-schema entry: detect whether session started today
            now_ts=$(date +%s)
            midnight_ts=$(date -v0H -v0M -v0S +%s 2>/dev/null \
                || date -d "today 00:00:00" +%s 2>/dev/null \
                || echo $(( now_ts - 86400 )))
            elapsed_today=$(( now_ts - midnight_ts ))
            session_age_sec=$(( duration_ms / 1000 ))
            needs_write=true
            if [[ $session_age_sec -le $elapsed_today ]]; then
                # Started today: count full cost
                day_start="0.000000"
                month_acc="$session_cost"
            else
                # Older session: baseline at current cost, only future deltas count
                day_start="$session_cost"
                month_acc="0.000000"
            fi
        else
            prior_cost=$(printf '%s' "$prior" | jq -r '.cost_usd // 0' | awk '{printf "%.6f", $0}')
            prior_date=$(printf '%s' "$prior" | jq -r '.date // ""')
            prior_day_start=$(printf '%s' "$prior" | jq -r '.cost_at_day_start // 0' | awk '{printf "%.6f", $0}')
            prior_month=$(printf '%s' "$prior" | jq -r '.month // ""')
            prior_month_acc=$(printf '%s' "$prior" | jq -r '.month_cost // 0' | awk '{printf "%.6f", $0}')

            if [[ "$prior_date" != "$today" ]]; then
                # Day rolled over
                needs_write=true
                day_start="$prior_cost"
                delta=$(awk "BEGIN{printf \"%.6f\", $session_cost - $prior_cost}")
                if [[ "$prior_month" != "$month" ]]; then
                    month_acc="$delta"
                else
                    month_acc=$(awk "BEGIN{printf \"%.6f\", $prior_month_acc + $session_cost - $prior_cost}")
                fi
            elif [[ "$prior_cost" != "$session_cost" ]]; then
                needs_write=true
                # total_cost_usd is monotonic within a session. A drop means the
                # authoritative counter was reset — e.g. account switch to Max,
                # re-login, or SDK reset. Rebaseline instead of emitting a
                # negative delta (which would poison today: and month: totals).
                if awk "BEGIN{exit !($session_cost < $prior_cost)}"; then
                    day_start="$session_cost"
                    month_acc="$prior_month_acc"
                else
                    # Same day, cost grew
                    day_start="$prior_day_start"
                    month_acc=$(awk "BEGIN{printf \"%.6f\", $prior_month_acc + $session_cost - $prior_cost}")
                fi
            else
                day_start="$prior_day_start"
                month_acc="$prior_month_acc"
            fi
        fi

        if $needs_write; then
            tmp="${COST_LOG}.tmp.$$"
            {
                if [[ -s "$COST_LOG" ]]; then
                    jq -c --arg sid "$session_id" --arg cutoff "$cutoff" \
                        'select(.session_id != $sid and .date >= $cutoff)' \
                        "$COST_LOG" 2>/dev/null
                fi
                jq -cn \
                    --arg  sid   "$session_id"   \
                    --arg  date  "$today"         \
                    --argjson start "$day_start"  \
                    --argjson cur   "$session_cost" \
                    --arg  mon   "$month"         \
                    --argjson macc  "$month_acc"  \
                    '{session_id:$sid,date:$date,cost_at_day_start:$start,cost_usd:$cur,month:$mon,month_cost:$macc}'
            } > "$tmp" 2>/dev/null && mv "$tmp" "$COST_LOG" || rm -f "$tmp"
        fi
    fi

    if [[ -s "$COST_LOG" ]]; then
        # Clamp per-entry deltas to >= 0 so pre-fix poisoned rows (negative
        # deltas left by account switches before the rebaseline guard existed)
        # don't pull the totals negative. New writes can't produce negatives.
        daily_cost=$(jq -s --arg d "$today" \
            '[.[] | select(.date == $d) | ((.cost_usd - (.cost_at_day_start // 0)) | if . < 0 then 0 else . end)] | add // 0' \
            "$COST_LOG" 2>/dev/null)
        monthly_cost=$(jq -s --arg m "$month" \
            '[.[] | select(.month == $m) | ((.month_cost // 0) | if . < 0 then 0 else . end)] | add // 0' \
            "$COST_LOG" 2>/dev/null)

        if [[ $cols -ge 125 && -n "$daily_cost" && "$daily_cost" != "0" && "$daily_cost" != "null" ]]; then
            daily_int=$(printf '%.0f' "$daily_cost")
            if [[ "$daily_int" -ge "$COST_THRESHOLD_DAILY" ]]; then
                line3+="$(printf '  \033[2;37mtoday:\033[0m\033[0;31m$%.2f\033[0m' "$daily_cost")"
            else
                line3+="$(printf '  \033[2;37mtoday:\033[0m\033[0;36m$%.2f\033[0m' "$daily_cost")"
            fi
        fi

        if [[ $cols -ge 155 && -n "$monthly_cost" && "$monthly_cost" != "0" && "$monthly_cost" != "null" ]]; then
            daily_avg=$(echo "$monthly_cost $weekdays_elapsed" | awk '{printf "%.2f", $1 / $2}')
            avg_int=$(printf '%.0f' "$daily_avg")
            # Avg color: cyan ≤20, orange >20, red >30; warning ⚠ if >40
            if [[ "$avg_int" -ge 40 ]]; then
                avg_display="$(printf '\033[0;31m$%.2f/d ⚠\033[0m' "$daily_avg")"
            elif [[ "$avg_int" -ge 30 ]]; then
                avg_display="$(printf '\033[0;31m$%.2f/d\033[0m' "$daily_avg")"
            elif [[ "$avg_int" -ge 20 ]]; then
                avg_display="$(printf '\033[0;33m$%.2f/d\033[0m' "$daily_avg")"
            else
                avg_display="$(printf '\033[2;37m$%.2f/d\033[0m' "$daily_avg")"
            fi
            monthly_int=$(printf '%.0f' "$monthly_cost")
            if [[ "$monthly_int" -ge "$COST_THRESHOLD_DAILY" ]]; then
                line3+="$(printf '  \033[2;37mmonth:\033[0m\033[0;31m$%.2f\033[0m \033[2;37m(avg\033[0m %s\033[2;37m)\033[0m' "$monthly_cost" "$avg_display")"
            else
                line3+="$(printf '  \033[2;37mmonth:\033[0m\033[0;36m$%.2f\033[0m \033[2;37m(avg\033[0m %s\033[2;37m)\033[0m' "$monthly_cost" "$avg_display")"
            fi
        fi
    fi
fi

# Output
echo -e "$line1"
[[ -n "$line2" ]] && echo -e "$line2"
echo -e "$line3"
exit 0
