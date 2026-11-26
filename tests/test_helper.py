import unittest

from system_manager import helper


class AllowListTests(unittest.TestCase):
    def test_unknown_action(self):
        self.assertIn("unknown action", helper.check("root", ["systemctl", "restart", "x"]))

    def test_command_outside_the_action_list(self):
        self.assertIn("not allowed", helper.check("power", ["bash", "-c", "id"]))

    def test_install_to_etc_passwd_is_refused(self):
        reason = helper.check("storage", ["install", "-m", "0644", "/tmp/x", "/etc/passwd"])
        self.assertIn("outside", reason)

    def test_install_to_fstab_is_allowed(self):
        self.assertEqual(helper.check("storage", ["install", "-m", "0644", "/tmp/x",
                                                  "/etc/fstab"]), "")

    def test_mountpoint_creation_is_allowed_under_mnt(self):
        self.assertEqual(helper.check("storage", ["install", "-d", "-m", "0755",
                                                  "/mnt/data"]), "")

    def test_tee_to_a_battery_threshold_is_allowed(self):
        self.assertEqual(helper.check(
            "power", ["tee", "/sys/class/power_supply/BAT0/charge_control_end_threshold"]), "")

    def test_tee_somewhere_else_is_refused(self):
        self.assertIn("outside", helper.check("power", ["tee", "/etc/sudoers"]))

    def test_systemctl_restart_is_allowed(self):
        self.assertEqual(helper.check("system", ["systemctl", "restart", "cups"]), "")

    def test_systemctl_daemon_reexec_is_refused(self):
        self.assertIn("not allowed", helper.check("system", ["systemctl", "daemon-reexec"]))

    def test_ufw_only_enable_disable_status(self):
        self.assertEqual(helper.check("privacy", ["ufw", "--force", "enable"]), "")
        self.assertIn("only enable", helper.check("privacy", ["ufw", "reset"]))

    def test_nft_cannot_add_rules(self):
        self.assertEqual(helper.check("privacy", ["nft", "list", "ruleset"]), "")
        self.assertIn("nft list", helper.check(
            "privacy", ["nft", "add", "table", "inet", "x"]))

    def test_mkfs_needs_one_device(self):
        with_reason = helper.check("storage", ["mkfs.ext4", "-F", "/dev/does-not-exist"])
        self.assertIn("existing", with_reason)
        self.assertIn("flags", helper.check("storage", ["mkfs.ext4", "--weird", "/dev/sda1"]))

    def test_empty_command(self):
        self.assertIn("no command", helper.check("storage", []))


class PathTraversalTests(unittest.TestCase):
    """The allow-list is the security boundary; `..` must not escape it."""

    def test_install_cannot_climb_out_of_run_media(self):
        reason = helper.check("storage", ["install", "-m", "0644", "/tmp/x",
                                          "/run/media/../../etc/sudoers"])
        self.assertIn("outside", reason)

    def test_install_dash_d_cannot_climb_out_of_mnt(self):
        reason = helper.check("storage", ["install", "-d", "/mnt/../../etc/cron.d/evil"])
        self.assertIn("outside", reason)

    def test_tee_cannot_climb_out_of_sys(self):
        reason = helper.check("power", ["tee", "/sys/class/leds/../../../etc/sudoers"])
        self.assertIn("outside", reason)

    def test_normalisation_keeps_legitimate_targets(self):
        self.assertEqual(helper.check("storage", ["install", "-d", "-m", "0755",
                                                  "/mnt/a/../data"]), "")


class PrivilegeEscalationTests(unittest.TestCase):
    def test_install_cannot_set_suid(self):
        reason = helper.check("storage", ["install", "-m", "4755", "/tmp/payload",
                                          "/mnt/ok"])
        self.assertIn("setuid", reason)

    def test_install_cannot_copy_a_protected_source(self):
        reason = helper.check("storage", ["install", "-m", "0644", "/etc/shadow",
                                          "/mnt/evil"])
        self.assertIn("may not copy", reason)

    def test_install_rejects_owner_override(self):
        reason = helper.check("storage", ["install", "-o", "root", "-g", "root",
                                          "/tmp/x", "/mnt/ok"])
        self.assertIn("-o is not allowed", reason)

    def test_grub_mkconfig_cannot_write_elsewhere(self):
        self.assertIn("only accepts", helper.check("system", ["grub-mkconfig", "-o",
                                                             "/etc/sudoers"]))
        self.assertEqual(helper.check("system", ["grub-mkconfig", "-o",
                                                 "/boot/grub/grub.cfg"]), "")

    def test_usermod_cannot_set_a_password_hash(self):
        reason = helper.check("users", ["usermod", "-p", "$6$x$y", "root"])
        self.assertIn("not allowed", reason)
        self.assertEqual(helper.check("users", ["usermod", "-a", "-G", "video", "hyprtk"]), "")

    def test_passwd_needs_exactly_one_user(self):
        self.assertIn("one user", helper.check("users", ["passwd", "-d", "root"]))
        self.assertEqual(helper.check("users", ["passwd", "alice"]), "")

    def test_chpasswd_cannot_chroot(self):
        self.assertIn("not allowed", helper.check("users", ["chpasswd", "-R", "/tmp/x"]))
        self.assertEqual(helper.check("users", ["chpasswd", "-e"]), "")

    def test_systemctl_cannot_target_another_root(self):
        reason = helper.check("system", ["systemctl", "--root=/mnt", "restart", "ssh"])
        self.assertIn("--root=/mnt", reason)


class HelperMainTests(unittest.TestCase):
    def test_refuses_without_root(self):
        # check() passes, then the euid guard refuses in the test process.
        with unittest.mock.patch.object(helper.os, "geteuid", return_value=1000):
            code = helper.main(["power", "--", "tee",
                                "/sys/class/power_supply/BAT0/charge_control_end_threshold"])
        self.assertEqual(code, 126)

    def test_refuses_a_disallowed_command_before_root(self):
        with unittest.mock.patch.object(helper.os, "geteuid", return_value=0):
            code = helper.main(["power", "--", "sh", "-c", "id"])
        self.assertEqual(code, 126)

    def test_help(self):
        self.assertEqual(helper.main(["--help"]), 2)


import unittest.mock  # noqa: E402 - kept next to the tests that use it

if __name__ == "__main__":
    unittest.main()
