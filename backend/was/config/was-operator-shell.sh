#!/usr/bin/env bash
# WAS operator interactive-shell configuration.
# This tracked file contains no secrets and is sourced by ~/.bashrc.

case $- in
  *i*) ;;
  *) return ;;
esac

PROMPT_YELLOW='\[\033[1;33m\]'
PROMPT_RED='\[\033[1;31m\]'
PROMPT_CYAN='\[\033[1;36m\]'
PROMPT_RESET='\[\033[0m\]'

# Let the custom prompt display the active named uv environment.
export VIRTUAL_ENV_DISABLE_PROMPT=1

prompt_uv_environment() {
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    printf '(%s) ' "${VIRTUAL_ENV##*/}"
  fi
}

prompt_git_branch() {
  local branch
  branch="$(git branch --show-current 2>/dev/null)"

  if [[ -n "$branch" ]]; then
    printf ' (%s)' "$branch"
  fi
}

PS1="${PROMPT_CYAN}"'$(prompt_uv_environment)'"${PROMPT_YELLOW}\u@\h${PROMPT_RESET}:${PROMPT_RED}\w${PROMPT_CYAN}"'$(prompt_git_branch)'"${PROMPT_RED} \$ ${PROMPT_RESET}"

alias ls='ls --color=auto -lah'
alias ll='ls --color=auto -lah'
alias la='ls --color=auto -A'
alias l='ls --color=auto -CF'
alias grep='grep --color=auto'
alias python='python3'

export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

alias cdwas='cd "$HOME/code/was_reporting/backend/was"'
alias menu='cdwas && make menu'

export WAS_S3_URI='s3://cisa-was-reports'

WAS_VIRTUAL_ENV="$HOME/code/was_reporting/was_reporting"

if [[ -r "$WAS_VIRTUAL_ENV/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$WAS_VIRTUAL_ENV/bin/activate"
fi

unset WAS_VIRTUAL_ENV
