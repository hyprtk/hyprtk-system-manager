Name:           hyprtk-system-manager
Version:        0.6.2
Release:        1%{?dist}
Summary:        System settings for the hyprtk desktop
License:        MIT
URL:            https://github.com/hyprtk/hyprtk-system-manager
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3
Requires:       quickshell
Requires:       polkit
Recommends:     udisks2
Recommends:     power-profiles-daemon
Recommends:     flatpak

%description
One searchable settings application for the Hyprland desktop: power, storage,
privacy, the bar itself and the compositor pages from config-manager.

%prep
%setup -q

%build

%install
DESTDIR=%{buildroot} ./install.sh --system --prefix /usr

%files
/usr/share/hyprtk-system-manager
/usr/bin/hyprtk-settings
/usr/share/applications/hyprtk-system-manager.desktop
/usr/libexec/hyprtk-sm-helper
/usr/share/polkit-1/actions/org.hyprtk.system-manager.policy

%changelog
* Wed Nov 25 2026 hyprtk <hyprtk@users.noreply.github.com> - 0.6.1-1
- Packaging fixes: no bytecode in the payload; build script and Debian metadata.
