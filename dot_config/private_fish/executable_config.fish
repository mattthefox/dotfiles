if status is-interactive
    # Commands to run in interactive sessions can go here
end
starship init fish | source

function please
    sudo $argv; 
end

function ytdl
    /home/mantra/MyWebServer/web_server/bin/media_downloader.sh $argv;
end

function reload_gtk_theme
  #set theme (gsettings get org.gnome.desktop.interface gtk-theme)
  gsettings set org.gnome.desktop.interface gtk-theme ''
  sleep 1
  gsettings set org.gnome.desktop.interface gtk-theme 'Lavanda-Dark'
end

function audio
    set cmd $argv[1]
    set infile $argv[2]
    set outfile $argv[3]

    switch $cmd
        case repitch
            # Increase pitch by 25% (about +3 semitones)
            ffmpeg -i $infile -filter:a "asetrate=44100*1.2,aresample=44100" $outfile
        case '*'
            echo "Usage: audio repitch <infile> <outfile>"
    end
end

function render_video
    /home/mantra/Scripts/InteractiveFFMPEG.sh
end

function unzip
    if test (count $argv) -lt 1 -o (count $argv) -gt 2
        echo "Usage: unzip <source.zip> [destination_directory]"
        return 1
    end

    set SOURCE $argv[1]

    if not test -f "$SOURCE"
        echo "Error: '$SOURCE' is not a valid file."
        return 1
    end

    if test (count $argv) -eq 2
        set DEST $argv[2]
    else
        set BASENAME (basename "$SOURCE" .zip)
        set DEST (dirname "$SOURCE")"/"$BASENAME
    end

    if not test -d "$DEST"
        mkdir -p "$DEST"
    end

    bsdtar -xvf "$SOURCE" -C "$DEST"
end

function mypip
    ~/myenv/bin/pip $argv
end


# Do not use fish_add_path (added in Fish 3.2) because it
# potentially changes the order of items in PATH
if not contains $_asdf_shims $PATH
    set -gx --prepend PATH $_asdf_shims
end

# Quick access to git repos
set -x GIT_ZEPHKIT ~/blender-git/build_linux/bin/4.1/scripts/addons
alias sharen='~/.local/share/applications/ShareNebula/sharenebula.sh'
alias mypy='~/myenv/bin/python'
alias code='~/.local/share/applications/Binaries/VSCodium-1.98.2.25078.glibc2.29-x86_64.AppImage'
alias mode='~/Scripts/theater_mode.sh'
alias wallpaper='~/Scripts/HyprlandWallpapers.sh'
alias rgb="mypy ~/Scripts/keyboard_rgb.py"
alias HOME_BACKUP="-r /run/media/mantra/projects/restic"

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd
    builtin pwd -L
end

# A copy of fish's internal cd function. This makes it possible to use
# `alias cd=z` without causing an infinite loop.
if ! builtin functions --query __zoxide_cd_internal
    if builtin functions --query cd
        builtin functions --copy cd __zoxide_cd_internal
    else
        alias __zoxide_cd_internal='builtin cd'
    end
end

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd
    __zoxide_cd_internal $argv
end

# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to add new entries to the database.
function __zoxide_hook --on-variable PWD
    test -z "$fish_private_mode"
    and command zoxide add -- (__zoxide_pwd)
end

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

if test -z $__zoxide_z_prefix
    set __zoxide_z_prefix 'z!'
end
set __zoxide_z_prefix_regex ^(string escape --style=regex $__zoxide_z_prefix)

# Jump to a directory using only keywords.
function __zoxide_z
    set -l argc (count $argv)
    if test $argc -eq 0
        __zoxide_cd $HOME
    else if test "$argv" = -
        __zoxide_cd -
    else if test $argc -eq 1 -a -d $argv[1]
        __zoxide_cd $argv[1]
    else if set -l result (string replace --regex $__zoxide_z_prefix_regex '' $argv[-1]); and test -n $result
        __zoxide_cd $result
    else
        set -l result (command zoxide query --exclude (__zoxide_pwd) -- $argv)
        and __zoxide_cd $result
    end
end

# Completions.
function __zoxide_z_complete
    set -l tokens (commandline --current-process --tokenize)
    set -l curr_tokens (commandline --cut-at-cursor --current-process --tokenize)

    if test (count $tokens) -le 2 -a (count $curr_tokens) -eq 1
        # If there are < 2 arguments, use `cd` completions.
        complete --do-complete "'' "(commandline --cut-at-cursor --current-token) | string match --regex '.*/$'
    else if test (count $tokens) -eq (count $curr_tokens); and ! string match --quiet --regex $__zoxide_z_prefix_regex. $tokens[-1]
        # If the last argument is empty and the one before doesn't start with
        # $__zoxide_z_prefix, use interactive selection.
        set -l query $tokens[2..-1]
        set -l result (zoxide query --exclude (__zoxide_pwd) --interactive -- $query)
        and echo $__zoxide_z_prefix$result
        commandline --function repaint
    end
end
complete --command __zoxide_z --no-files --arguments '(__zoxide_z_complete)'

# Jump to a directory using interactive search.
function __zoxide_zi
    set -l result (command zoxide query --interactive -- $argv)
    and __zoxide_cd $result
end

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

alias launch="exec /home/mantra/Scripts/launch-waybar.sh"

abbr --erase z &>/dev/null
alias z=__zoxide_z

abbr --erase zi &>/dev/null
alias zi=__zoxide_zi

# Pyenv setup
set -Ux PYENV_ROOT $HOME/.pyenv
fish_add_path $PYENV_ROOT/bin

# Initialize pyenv + shims
status --is-interactive; and pyenv init - | source

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually
# ~/.config/fish/config.fish):
#
#   zoxide init fish | source