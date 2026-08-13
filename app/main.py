import sys
import os
import subprocess

COMMANDS = ["type", "exit", "echo"]

def find_in_path(command):
    """Search for an executable command in PATH directories."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:
        if not directory:
            continue

        full_path = os.path.join(directory, command)

        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            command = input()
        except EOFError:
            break

        if not command.strip():
            continue

        command_parts = command.split()
        cmd = command_parts[0]
        args = command_parts[1:] if len(command_parts) > 1 else []

        if command == "exit":
            break
        elif command.startswith("echo "):
            print(" ".join(args))
        elif command.startswith("type "):
            if not args:
                continue

            cmd_to_check = args[0]

            if cmd_to_check in COMMANDS:
                print(f"{cmd_to_check} is a shell builtin")
            else:
                found_path = find_in_path(cmd_to_check)
                if found_path:
                    print(f"{cmd_to_check} is {found_path}")
                else:
                    print(f"{cmd_to_check}: not found")
        else:
            full_path = find_in_path(cmd)
            if full_path is None:
                print(f"{cmd}: command not found")
            else:
                try:
                    subprocess.run([cmd] + args, executable=full_path)
                except Exception as e:
                    print(f"Error executing {cmd}: {e}")

if __name__ == "__main__":
    main()
