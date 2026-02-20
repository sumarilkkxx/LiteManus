from langchain_core.tools import tool
import os
import subprocess

# 统一工作区目录
PROJECT_ROOT = os.getcwd()
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", os.path.join(PROJECT_ROOT, "workspace"))
os.makedirs(WORKSPACE_DIR, exist_ok=True)


def _to_workspace_path(file_name: str) -> str:
    """
    将文件路径归一到workspace下：
    - 支持子路径：如reports/a.md -> workspace/reports/a.md
    - 若传入绝对路径或带盘符路径：强制落到workspace
    - 防止 .. 逃逸
    """
    file_name = (file_name or "").strip().replace("\\", "/")
    if not file_name:
        raise ValueError("file_name is empty")

    base_name = os.path.basename(file_name)
    sub_dir = os.path.dirname(file_name)

    safe_rel = os.path.join(sub_dir, base_name) if sub_dir else base_name
    safe_rel = os.path.normpath(safe_rel)

    if safe_rel.startswith(".."):
        safe_rel = base_name

    return os.path.join(WORKSPACE_DIR, safe_rel)


@tool
def create_file(file_name, file_contents):
    """
    Create a new file under workspace/ with the provided contents.
    """
    try:
        file_path = _to_workspace_path(file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_contents)

        return {"message": f"Successfully created file at {file_path}"}
    except Exception as e:
        return {"error": str(e)}


@tool
def str_replace(file_name, old_str, new_str):
    """
    Replace specific text in a file under workspace/.
    """
    try:
        file_path = _to_workspace_path(file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = content.replace(old_str, new_str, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {"message": f"Successfully replaced '{old_str}' with '{new_str}' in {file_path}"}
    except Exception as e:
        return {"error": f"Error replacing text in workspace file: {str(e)}"}


@tool
def send_message(message: str):
    """send a message to the user"""
    return message


@tool
def shell_exec(command: str) -> dict:
    """
    Execute command in PROJECT ROOT (so data sources keep working),
    but steer outputs to workspace via common env vars.

    - cwd: project root（不改变数据源相对路径语义）
    - env: inject output dirs -> workspace
    """
    try:
        
        if os.name == "nt":
            cmd = command.strip()
            if cmd == "ls":
                command = "dir"
            elif cmd.startswith("cat "):
                command = "type " + cmd[4:]

        env = os.environ.copy()

        # 常用输出目录约定
        env.setdefault("WORKSPACE_DIR", WORKSPACE_DIR)
        env.setdefault("OUTPUT_DIR", WORKSPACE_DIR)
        env.setdefault("OUT_DIR", WORKSPACE_DIR)
        env.setdefault("RESULTS_DIR", WORKSPACE_DIR)
        env.setdefault("REPORT_DIR", WORKSPACE_DIR)
        env.setdefault("ARTIFACTS_DIR", WORKSPACE_DIR)
        env.setdefault("TMPDIR", WORKSPACE_DIR)     
        env.setdefault("TEMP", WORKSPACE_DIR)       
        env.setdefault("TMP", WORKSPACE_DIR)        

        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,        
            capture_output=True,
            text=True,
            check=False,
            env=env                  
        )

        return {
            "message": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": PROJECT_ROOT,
                "workspace": WORKSPACE_DIR,
            }
        }
    except Exception as e:
        return {"error": {"stderr": str(e), "cwd": PROJECT_ROOT, "workspace": WORKSPACE_DIR}}