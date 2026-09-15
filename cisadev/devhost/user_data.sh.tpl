#!/usr/bin/env bash
set -euo pipefail

exec > >(tee -a /var/log/user-data.log) 2>&1

# Config injected by Terraform.
USERNAME="${username}"
PASSWORD="${password}"
DESKTOP="${desktop}"

DESKTOP="$${DESKTOP,,}" # normalize to lowercase

echo "--- Dev Host Config ---"
echo "  USERNAME : '$${USERNAME}'"
echo "  PASSWORD : [set]"
echo "  DESKTOP  : '$${DESKTOP}'"

# Flatpak app list (comment out apps you don't want).
cat > /root/flatpaks.txt <<'EOF'
# Development Tools & IDEs
com.visualstudio.code
#com.jetbrains.IntelliJ-IDEA-Community
#io.neovim.nvim

# Version Control & Git Tools
io.github.shiftey.Desktop

# Browsers
#org.mozilla.firefox

# Design, Mockup & Creative
com.figma.Figma

# Diagramming & Modeling
com.jgraph.drawio.desktop

# Productivity & Office
org.libreoffice.LibreOffice

# Password Managers
org.keepassxc.KeePassXC
EOF

export DEBIAN_FRONTEND=noninteractive
apt-get update

# Install only the selected desktop environment.
case "$${DESKTOP}" in
  ubuntu)
    printf 'gdm3 shared/default-x-display-manager select gdm3\n' | debconf-set-selections
    apt-get install -y ubuntu-desktop
    systemctl set-default graphical.target
    systemctl enable gdm
    ;;
  cinnamon)
    apt-get install -y cinnamon-desktop-environment
    ;;
  xfce)
    apt-get install -y xfce4 xfce4-goodies
    ;;
esac

# xrdp, smart card, and supporting packages.
apt-get install -y xrdp xorgxrdp dbus-x11 flatpak unzip \
  pcscd pcsc-tools libccid opensc

# AWS CLI v2 — GPG-verified against AWS's pinned signing key before install.
if ! command -v aws >/dev/null 2>&1; then
  apt-get install -y gnupg curl
  TMPDIR="$(mktemp -d)"
  cd "$${TMPDIR}"

  AWS_CLI_FPR="FB5DB77FD5C118B80511ADA8A6310ACC4672475C"

  curl -fsSL "https://awscli.amazonaws.com/aws-cli.gpg" -o aws-cli.gpg 2>/dev/null \
    || curl -fsSL "https://awscli.amazonaws.com/awscli.pub" -o aws-cli.gpg
  gpg --import aws-cli.gpg
  if ! gpg --fingerprint "$${AWS_CLI_FPR}" >/dev/null 2>&1; then
    echo "ERROR: AWS CLI signing key fingerprint did not match pinned value. Aborting."
    exit 1
  fi

  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip.sig" -o awscliv2.sig
  gpg --verify awscliv2.sig awscliv2.zip
  unzip -q awscliv2.zip
  ./aws/install
  cd /
  rm -rf "$${TMPDIR}"
fi
aws --version

# Ensure the login user exists, then set the password.
if ! id -u "$${USERNAME}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "$${USERNAME}"
fi
echo "$${USERNAME}:$${PASSWORD}" | chpasswd
usermod -aG sudo "$${USERNAME}"

# Configure the xrdp session for the user.
case "$${DESKTOP}" in
  ubuntu)
    cat > "/home/$${USERNAME}/.xsession" <<'XSEOF'
export GNOME_SHELL_SESSION_MODE=ubuntu
exec gnome-session --session=ubuntu
XSEOF
    ;;
  cinnamon)
    echo "exec cinnamon-session" > "/home/$${USERNAME}/.xsession"
    ;;
  xfce)
    echo "exec startxfce4" > "/home/$${USERNAME}/.xsession"
    ;;
esac
chown "$${USERNAME}:$${USERNAME}" "/home/$${USERNAME}/.xsession"
chmod 755 "/home/$${USERNAME}/.xsession"

systemctl enable --now xrdp

# Firewall: SSH + RDP.
apt-get install -y ufw
ufw allow 22/tcp
ufw allow 3389/tcp
ufw --force enable

# Flatpak apps.
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
grep -Ev '^\s*(#|$)' /root/flatpaks.txt | xargs -r -n1 flatpak install -y

echo "Setup complete. RDP to instance IP:3389 as '$${USERNAME}'. Desktop: '$${DESKTOP}'."
