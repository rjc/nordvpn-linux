import random
from lib import (
    daemon,
    info,
    logging,
    login,
    network,
    server,
)
import lib
import pytest
import sh
import socket
import timeout_decorator


def setup_module(module):
    daemon.start()
    login.login_as("default")


def teardown_module(module):
    sh.nordvpn.logout("--persist-token")
    daemon.stop()


def setup_function(function):
    logging.log()


def teardown_function(function):
    logging.log(data=info.collect())
    logging.log()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_quick_connect(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_double_quick_connect_only(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
def test_connect_to_absent_server(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.connect("moon")

    print(ex.value)
    assert lib.is_connect_unsuccessful(ex)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
def test_mistype_connect(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.kinect()

    print(ex.value)
    assert lib.is_invalid_command("kinect", ex)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_connect_to_random_server_by_name(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    name, hostname = server.get_hostname_by(tech, proto, obfuscated)
    output = sh.nordvpn.connect(hostname.split(".")[0])
    print(output)
    assert lib.is_connect_successful(output, name, hostname)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_connection_recovers_from_network_restart(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    links = socket.if_nameindex()
    logging.log(links)
    network.stop()
    network.start()
    daemon.wait_for_reconnect(links)
    with lib.ErrorDefer(sh.nordvpn.disconnect):
        assert network.is_connected()
    logging.log(info.collect())

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_double_quick_connect_disconnect(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()

    output = sh.nordvpn.connect()
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.timeout(120) # TODO: make this test faster, there's some gateway error that eats 30 seconds
def test_connect_without_internet_access(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    network.stop()
    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.connect()

    print(ex.value)
    network.start()


@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(20)
def test_connect_to_group():
    group = random.choice(lib.GROUPS)

    output = sh.nordvpn.connect(group)
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.connect("--group", group)
    print(output)
    assert lib.is_connect_successful(output)
    assert network.is_connected()

    output = sh.nordvpn.disconnect()
    print(output)
    assert lib.is_disconnect_successful(output)
    assert network.is_disconnected()

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.connect("--group", group, group)

    print(ex.value)
    assert lib.is_connect_unsuccessful(ex)


def test_connect_to_invalid_group():
    try:
        with pytest.raises(sh.ErrorReturnCode_1) as ex:
            sh.nordvpn.connect("--group", "nonexisting_group")
        # We want to check for this exact message
        assert "The specified group does not exist." in str(ex.value)
    finally:
        sh.nordvpn.disconnect()
