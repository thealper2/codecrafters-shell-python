import sys
import os

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

        if command == "exit":
            break
        elif command.startswith("echo "):
            print(command[5:])
        elif command.startswith("type "):
            cmd = command[5:]

            if cmd in COMMANDS:
                print(f"{cmd} is a shell builtin")
            else:
                found_path = find_in_path(cmd)
                if found_path:
                    print(f"{cmd} is {found_path}")
                else:
                    print(f"{cmd}: not found")
        else:
            if find_in_path(command):
                print(f"{command}: command not found")
            else:
                print(f"{command}: command not found")

if __name__ == "__main__":
    main()
