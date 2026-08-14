import sys
import os
import subprocess

COMMANDS = ["type", "exit", "echo", "pwd", "cd"]

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

def parse_command(line):
    args = []
    current_arg = []
    in_single = False
    in_double = False
    redirect_file = None
    i = 0
    n = len(line)
    has_current = False
    
    while i < n:
        c = line[i]
        
        if c == "\\" and not in_single and not in_double:
            if i + 1 < n:
                current_arg.append(line[i + 1])
                i += 2
            else:
                i += 1
        elif c == "\\" and in_double:
            if i + 1 < n and line[i + 1] in ('"', "\\"):
                current_arg.append(line[i + 1])
                i += 2
            else:
                current_arg.append(c)
                i += 1
        elif c == "'" and not in_double:
            in_single = not in_single
            i += 1
        elif c == '"' and not in_single:
            in_double = not in_double
            i += 1
        elif c == ">" and not in_single and not in_double:
            if current_arg == ["1"]:
                current_arg = []
                has_current = False
            if has_current:
                args.append(''.join(current_arg))
                current_arg = []
                has_current = False
                
            i += 1
            while i < n and line[i].isspace():
                i += 1
                
            fname, i = _parse_token(line, i)
            redirect_file = fname
        elif c.isspace() and not in_single and not in_double:
            if current_arg:
                args.append(''.join(current_arg))
                current_arg = []
                
            i += 1
        else:
            current_arg.append(c)
            i += 1
            
    if current_arg:
        args.append(''.join(current_arg))
        
    return args

def _parse_token(line, i):
    """Parse a single token (respecting quotes/backslashes) starting at i."""
    current = []
    in_single = False
    in_double = False
    n = len(line)
    
    while i < n:
        c = line[i]
        if c == "\\" and not in_single and not in_double:
            if i + 1 < n:
                current.append(line[i + 1])
                i += 2
            else:
                i += 1
        elif c == "\\" and in_double:
            if i + 1 < n and line[i + 1] in ('"', "\\"):
                current.append(line[i + 1])
                i += 2
            else:
                current.append(c)
                i += 1
        elif c == "'" and not in_double:
            in_single = not in_single
            i += 1
        elif c == '"' and not in_single:
            in_double = not in_double
            i += 1
        elif c.isspace() and not in_single and not in_double:
            break
        else:
            current.append(c)
            i += 1
            
    return ''.join(current), i

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

        command_parts = parse_command(command)
        if not command_parts:
            continue
        
        cmd = command_parts[0]
        args = command_parts[1:] if len(command_parts) > 1 else []

        out = None
        if redirect_file is not None:
            try:
                out = open(redirect_file, "w")
            except Exception as e:
                print(f"{redirect_file}: {e}")
                continue

        if cmd == "exit":
            if out: out.close()
            break
        elif cmd == "echo":
            print(" ".join(args), file=(out if out else sys.stdout))
        elif cmd == "pwd":
            try:
                print(os.getcwd(), file=(out if out else sys.stdout))
            except Exception as e:
                print(f"Error getting current directory: {e}")
        elif cmd == "cd":
            if not args:
                home_dir = os.environ.get("HOME")
                if home_dir:
                    try:
                        os.chdir(home_dir)
                    except Exception as e:
                        print(f"cd: {home_dir}: {e}")
                else:
                    print("cd: HOME not set")

                continue

            target_dir = args[0]

            if target_dir == "~":
                home_dir = os.environ.get("HOME")
                if home_dir:
                    target_dir = home_dir
                else:
                    print("cd: HOME not set")
                    continue

            if os.path.isdir(target_dir):
                try:
                    os.chdir(target_dir)
                except Exception as e:
                    print(f"cd: {target_dir}: {e}")
            else:
                print(f"cd: {target_dir}: No such file or directory")
        elif cmd == "type":
            target = out if out else sys.stdout
            if not args:
                if out: out.close()
                continue

            cmd_to_check = args[0]

            if cmd_to_check in COMMANDS:
                print(f"{cmd_to_check} is a shell builtin", file=target)
            else:
                found_path = find_in_path(cmd_to_check)
                if found_path:
                    print(f"{cmd_to_check} is {found_path}", file=target)
                else:
                    print(f"{cmd_to_check}: not found", file=target)
        else:
            full_path = find_in_path(cmd)
            if full_path is None:
                print(f"{cmd}: command not found")
            else:
                try:
                    subprocess.run([cmd] + args, executable=full_path, stdout=out)
                except Exception as e:
                    print(f"Error executing {cmd}: {e}")

if __name__ == "__main__":
    main()
