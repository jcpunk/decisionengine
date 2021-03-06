import os
import threading
from unittest.mock import patch

import pytest

import decisionengine.framework.config.policies as policies
from decisionengine.framework.config.ValidConfig import ValidConfig
from decisionengine.framework.dataspace import datablock
from decisionengine.framework.taskmanager.TaskManager import State, TaskManager
from decisionengine.framework.taskmanager.tests.fixtures import (  # noqa: F401
    DATABASES_TO_TEST,
    PG_DE_DB_WITH_SCHEMA,
    PG_DE_DB_WITHOUT_SCHEMA,
    PG_PROG,
    SQLALCHEMY_TEMPFILE_SQLITE,
    SQLALCHEMY_PG_WITH_SCHEMA,
    dataspace,
)

_CWD = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_CWD, "../../tests/etc/decisionengine")
_CHANNEL_CONFIG_DIR = os.path.join(_CWD, "channels")

_TEST_CHANNEL_NAMES = ("test_channel",)


class RunChannel:
    def __init__(self, global_config, channel):
        self._tm = TaskManager(channel, 1, get_channel_config(channel), global_config)
        self._thread = threading.Thread(name=channel, target=self._tm.run)

    def __enter__(self):
        self._thread.start()
        return self._tm

    def __exit__(self, type, value, traceback):
        if type:
            return False
        self._thread.join()


def get_channel_config(name):
    return ValidConfig(os.path.join(_CHANNEL_CONFIG_DIR, name + ".jsonnet"))


@pytest.fixture
@pytest.mark.usefixtures("dataspace")
def global_config(dataspace):  # noqa: F811
    conf = ValidConfig(policies.global_config_file(_CONFIG_PATH))
    conf["dataspace"] = dataspace.config["dataspace"]
    yield conf


@pytest.mark.usefixtures("global_config")
def test_taskmanager_init(global_config):
    for channel in _TEST_CHANNEL_NAMES:
        task_manager = TaskManager(channel, 1, get_channel_config(channel), global_config)
        assert task_manager.state.has_value(State.BOOT)


@pytest.mark.usefixtures("global_config")
def test_set_to_shutdown(global_config):
    for channel in _TEST_CHANNEL_NAMES:
        with RunChannel(global_config, channel) as task_manager:
            task_manager.state.wait_while(State.BOOT)
            m = "decisionengine.framework.tests.PublisherNOP.PublisherNOP.shutdown"
            with patch(m) as mocked_shutdown:
                task_manager.set_to_shutdown()
                mocked_shutdown.assert_called()
            assert task_manager.state.has_value(State.SHUTDOWN)


@pytest.mark.usefixtures("global_config")
def test_take_task_manager_offline(global_config):
    for channel in _TEST_CHANNEL_NAMES:
        with RunChannel(global_config, channel) as task_manager:
            task_manager.state.wait_while(State.BOOT)
            task_manager.take_offline(None)
            assert task_manager.state.has_value(State.OFFLINE)
            assert task_manager.get_state_value() == State.OFFLINE.value


@pytest.mark.usefixtures("global_config")
def test_failing_publisher(global_config):
    task_manager = TaskManager("failing_publisher", 1, get_channel_config("failing_publisher"), global_config)
    task_manager.run()
    assert task_manager.state.has_value(State.OFFLINE)


@pytest.mark.usefixtures("global_config", "dataspace")
def test_bad_datablock(global_config, dataspace, caplog):  # noqa: F811
    for channel in _TEST_CHANNEL_NAMES:
        with RunChannel(global_config, channel) as task_manager:
            task_manager.state.wait_while(State.BOOT)
            dblock = datablock.DataBlock(dataspace, channel)
            task_manager.data_block_put("bad_string", "header", dblock)
            task_manager.take_offline(None)
            assert "data_block put expecting" in caplog.text


@pytest.mark.usefixtures("global_config")
def test_no_data_to_transform(global_config):
    for channel in _TEST_CHANNEL_NAMES:
        with RunChannel(global_config, channel) as task_manager:
            task_manager.state.wait_while(State.BOOT)
            task_manager.run_transforms()
            task_manager.run_publishers("action", "facts")
            task_manager.run_logic_engine()
            task_manager.take_offline(None)
