from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cloudai._core.install_status_result import InstallStatusResult
from cloudai.schema.test_template.nccl_test.slurm_install_strategy import NcclTestSlurmInstallStrategy
from cloudai.schema.test_template.nemo_launcher.slurm_install_strategy import (
    DatasetCheckResult,
    NeMoLauncherSlurmInstallStrategy,
)
from cloudai.schema.test_template.ucc_test.slurm_install_strategy import UCCTestSlurmInstallStrategy
from cloudai.systems import SlurmSystem
from cloudai.systems.slurm import SlurmNode, SlurmNodeState
from cloudai.systems.slurm.strategy import SlurmInstallStrategy


@pytest.fixture
def slurm_system(tmp_path: Path) -> SlurmSystem:
    slurm_system = SlurmSystem(
        name="TestSystem",
        install_path=str(tmp_path / "install"),
        output_path=str(tmp_path / "output"),
        default_partition="main",
        partitions={
            "main": [
                SlurmNode(name="node1", partition="main", state=SlurmNodeState.IDLE),
                SlurmNode(name="node2", partition="main", state=SlurmNodeState.IDLE),
                SlurmNode(name="node3", partition="main", state=SlurmNodeState.IDLE),
                SlurmNode(name="node4", partition="main", state=SlurmNodeState.IDLE),
            ]
        },
    )
    Path(slurm_system.install_path).mkdir()
    Path(slurm_system.output_path).mkdir()
    return slurm_system


@pytest.fixture
def slurm_install_strategy(slurm_system: SlurmSystem) -> SlurmInstallStrategy:
    env_vars = {"TEST_VAR": "VALUE"}
    cmd_args = {"docker_image_url": {"default": "http://example.com/docker_image"}}
    strategy = SlurmInstallStrategy(slurm_system, env_vars, cmd_args)
    return strategy


def test_install_path_attribute(slurm_install_strategy: SlurmInstallStrategy, slurm_system: SlurmSystem):
    assert slurm_install_strategy.install_path == slurm_system.install_path


@pytest.fixture
def mock_docker_image_cache_manager(slurm_system: SlurmSystem):
    mock = MagicMock()
    mock.cache_docker_images_locally = True
    mock.install_path = slurm_system.install_path
    mock.check_docker_image_exists.return_value = InstallStatusResult(success=False, message="Docker image not found")
    mock.ensure_docker_image.return_value = InstallStatusResult(success=True)
    mock.uninstall_cached_image.return_value = InstallStatusResult(success=True)
    return mock


class TestNcclTestSlurmInstallStrategy:
    @pytest.fixture
    def strategy(self, slurm_system, mock_docker_image_cache_manager) -> NcclTestSlurmInstallStrategy:
        strategy = NcclTestSlurmInstallStrategy(slurm_system, {}, {})
        strategy.docker_image_cache_manager = mock_docker_image_cache_manager
        return strategy

    def test_is_installed_locally(self, strategy: NcclTestSlurmInstallStrategy):
        expected_docker_image_path = str(Path(strategy.slurm_system.install_path) / "nccl-test" / "nccl_test.sqsh")

        result = strategy.is_installed()

        assert not result.success
        assert result.message == (
            "Docker image for NCCL test is not installed.\n"
            f"    - Expected path: {expected_docker_image_path}.\n"
            f"    - Error: Docker image not found"
        )

    def test_is_installed_remote(self, strategy: NcclTestSlurmInstallStrategy):
        strategy.docker_image_cache_manager.cache_docker_images_locally = False

        result = strategy.is_installed()

        assert not result.success
        assert result.message == (
            "Docker image for NCCL test is not accessible.\n" "    - Error: Docker image not found"
        )

    def test_install_success(self, strategy: NcclTestSlurmInstallStrategy):
        with patch.object(
            strategy.docker_image_cache_manager,
            "check_docker_image_exists",
            return_value=InstallStatusResult(success=True),
        ):
            result = strategy.install()
            assert result.success

    def test_uninstall_success(self, strategy: NcclTestSlurmInstallStrategy):
        result = strategy.uninstall()

        assert result.success


class TestNeMoLauncherSlurmInstallStrategy:
    @pytest.fixture
    def strategy(self, slurm_system, mock_docker_image_cache_manager) -> NeMoLauncherSlurmInstallStrategy:
        strategy = NeMoLauncherSlurmInstallStrategy(
            slurm_system,
            {},
            {
                "repository_url": {"default": "https://github.com/NVIDIA/NeMo-Framework-Launcher.git"},
                "repository_commit_hash": {"default": "cf411a9ede3b466677df8ee672bcc6c396e71e1a"},
                "docker_image_url": {"default": "nvcr.io/nvidian/nemofw-training:24.01.01"},
                "data_dir": {"default": "DATA_DIR"},
            },
        )
        strategy.docker_image_cache_manager = mock_docker_image_cache_manager
        return strategy

    def test_is_installed(self, strategy: NeMoLauncherSlurmInstallStrategy):
        with patch.object(
            strategy,
            "_check_datasets_on_nodes",
            return_value=DatasetCheckResult(success=True, nodes_without_datasets=[]),
        ):
            result = strategy.is_installed()
            assert not result.success
            assert (
                "The following components are missing:" in result.message
                and "Repository" in result.message
                and "Docker image" in result.message
            )


class TestUCCTestSlurmInstallStrategy:
    @pytest.fixture
    def strategy(self, slurm_system, mock_docker_image_cache_manager) -> UCCTestSlurmInstallStrategy:
        strategy = UCCTestSlurmInstallStrategy(slurm_system, {}, {})
        strategy.docker_image_cache_manager = mock_docker_image_cache_manager
        return strategy

    def test_is_installed_locally(self, strategy: UCCTestSlurmInstallStrategy):
        expected_docker_image_path = str(Path(strategy.slurm_system.install_path) / "ucc-test" / "ucc_test.sqsh")

        result = strategy.is_installed()

        assert not result.success
        assert result.message == (
            "Docker image for UCC test is not installed.\n"
            f"    - Expected path: {expected_docker_image_path}.\n"
            f"    - Error: Docker image not found"
        )

    def test_is_installed_remote(self, strategy: UCCTestSlurmInstallStrategy):
        strategy.docker_image_cache_manager.cache_docker_images_locally = False

        result = strategy.is_installed()

        assert not result.success
        assert result.message == (
            "Docker image for UCC test is not accessible.\n" "    - Error: Docker image not found"
        )

    def test_install_success(self, strategy: UCCTestSlurmInstallStrategy):
        with patch.object(
            strategy.docker_image_cache_manager,
            "check_docker_image_exists",
            return_value=InstallStatusResult(success=True),
        ):
            result = strategy.install()
            assert result.success

    def test_uninstall_success(self, strategy: UCCTestSlurmInstallStrategy):
        result = strategy.uninstall()

        assert result.success