"""
Skill execution module.
Supports two modes:
- ssh-docker: SSH into remote VPS, docker exec into OpenClaw container
- local: Run scripts directly on the same machine
"""
import os
import subprocess
import json
import tempfile
import shutil
import re
import time


def execute_skill_ssh(skill_name: str, args: list, config: dict) -> dict:
    """Execute a skill via SSH -> docker exec."""
    ssh_host = config.get('SSH_HOST', '185.255.95.245')
    ssh_port = config.get('SSH_PORT', '8239')
    ssh_user = config.get('SSH_USER', 'root')
    ssh_pass = config.get('SSH_PASS', '')
    docker_container = config.get('DOCKER_CONTAINER', 'dk_openclaw-openclaw-gateway-1')
    docker_skills_path = config.get('DOCKER_SKILLS_PATH', '/home/node/clawd/skills')
    sshpass_bin = config.get('SSHPASS_BIN', '/usr/bin/sshpass')
    ssh_bin = config.get('SSH_BIN', '/usr/bin/ssh')

    script_path = f"{docker_skills_path}/{skill_name}/scripts/skill.py"
    escaped_args = ' '.join(f"'{a}'" if ' ' in a else a for a in args)
    cmd_full = f"python3 '{script_path}' {escaped_args}"

    remote_cmd = f"docker exec {docker_container} {cmd_full}"

    timeout = config.get('EXEC_TIMEOUT', 120)
    ssh_cmd = [
        sshpass_bin, '-p', ssh_pass,
        ssh_bin, '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ConnectTimeout=15',
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        '--', remote_cmd
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout
        error = result.stderr
        exit_code = result.returncode

        output, error = _filter_ssh_output(output, error)

        return {
            'success': exit_code == 0,
            'output': output.strip(),
            'error': error.strip() if error else None,
            'exit_code': exit_code
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': f'Timed out after {timeout}s',
            'exit_code': -1
        }
    except FileNotFoundError as e:
        return {
            'success': False,
            'output': '',
            'error': f'Binary not found: {e}',
            'exit_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'exit_code': -1
        }


def execute_skill_local(skill_name: str, args: list, config: dict) -> dict:
    """Execute a skill locally."""
    skills_dir = config.get('SKILLS_DIR', '/app/skills')
    python_bin = config.get('PYTHON', 'python3')

    script_path = os.path.join(skills_dir, skill_name, 'scripts', 'skill.py')
    if not os.path.exists(script_path):
        return {
            'success': False,
            'output': '',
            'error': f'Script not found: {script_path}',
            'exit_code': -1
        }

    cmd = [python_bin, script_path] + args
    timeout = config.get('EXEC_TIMEOUT', 120)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout
        error = result.stderr
        exit_code = result.returncode

        return {
            'success': exit_code == 0,
            'output': output.strip(),
            'error': error.strip() if error else None,
            'exit_code': exit_code
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': f'Timed out after {timeout}s',
            'exit_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'exit_code': -1
        }


def _filter_ssh_output(stdout: str, stderr: str) -> tuple:
    """Remove sshpass/ssh banner messages from output."""
    filtered_stdout = stdout
    filtered_stderr = stderr

    # Remove sshpass warning about password prompt
    lines_stderr = stderr.split('\n')
    filtered_stderr_lines = [
        l for l in lines_stderr
        if 'sshpass' not in l.lower() and 'warning' not in l.lower()
    ]
    filtered_stderr = '\n'.join(filtered_stderr_lines).strip()

    return filtered_stdout, filtered_stderr


def handle_file_output(skill_name: str, args: list, output: str, config: dict) -> dict:
    """Handle skills that produce downloadable files (QR codes, etc.)."""
    # For QR codes, check if --output or -o flag was used
    download_url = None
    file_path = None

    if skill_name == 'qr-generator':
        # Find the output file path from args
        for i, arg in enumerate(args):
            if arg in ('-o', '--output') and i + 1 < len(args):
                file_path = args[i + 1]
                break

    if file_path and os.path.exists(file_path):
        # Copy to temp directory for download
        basename = os.path.basename(file_path)
        dest = os.path.join('/tmp', basename)
        shutil.copy2(file_path, dest)
        download_url = f'/download?file={basename}'
        # Clean up original
        try:
            os.unlink(file_path)
        except OSError:
            pass

    return {
        'success': True,
        'output': output,
        'download': download_url,
        'message': 'File generated!' if download_url else None
    }
