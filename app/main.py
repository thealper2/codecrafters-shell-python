import sys
import os
import subprocess
import readline

BUILTINS = ["echo", "exit"]
COMMANDS = ["type", "exit", "echo", "pwd", "cd", "complete"]
completions = {}

def get_executables(text):
    """Find executables in PATH that start with text."""
    matches = set()
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        try:
            for entry in os.listdir(directory):
                if entry.startswith(text):
                    full_path = os.path.join(directory, entry)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        matches.add(entry)
                        
        except OSError:
            continue
        
    return matches

def get_filenames(text):
    """Find files/dirs in the relevant directory matching the prefix."""
    directory = os.path.dirname(text) or "."
    prefix = os.path.basename(text)
    matches = []
    try:
        for entry in os.listdir(directory):
            if entry.startswith(prefix):
                full = os.path.join(directory, entry)
                if os.path.dirname(text):
                    candidate = os.path.join(os.path.dirname(text), entry)
                else:
                    candidate = entry
                    
                if os.path.isdir(full):
                    matches.append(candidate + "/")
                else:
                    matches.append(candidate)
                    
    except OSError:
        pass
    
    return matches

last_text = None
tab_count = 0

def completer(text, state):
    global last_text, tab_count
    
    line = readline.get_line_buffer()
    
    stripped = line.lstrip()
    parts = stripped.split()
    if parts:
        cmd_word = parts[0]
        
        if cmd_word in completions and (len(parts) > 1 or line.endswith(" ")):
            script = completions[cmd_word]
            comp_word = text
            before = line[:len(line) - len(text)]
            before_words = before.split()
            prev_word = before_words[-1] if before_words else ""
            
            try:
                comp_env = os.environ.copy()
                comp_env["COMP_LINE"] = line
                comp_env["COMP_POINT"] = str(len(line))
                result = subprocess.run(
                    [script, cmd_word, comp_word, prev_word],
                    capture_output=True,
                    text=True,
                    env=comp_env,
                )
                lines = [l for l in result.stdout.splitlines() if l.startswith(text)]
            except Exception:
                lines = []
                
            matches = sorted(lines)
            if len(matches) == 0:
                return None
            if state == 0:
                return matches[0] + " "
            return None
    
    if " " not in line.strip() and not line[:len(line) - len(text)].strip():
        candidates = set(c for c in BUILTINS if c.startswith(text))
        candidates |= get_executables(text)
        matches = sorted(candidates)
    else:
        matches = sorted(get_filenames(text))
    
    if len(matches) == 0:
        return None
    
    if len(matches) == 1:
        if state == 0:
            m = matches[0]
            return m if m.endswith("/") else m + " "
        
        return None
    
    common = os.path.commonprefix(matches)
    if len(common) > len(text):
        if state == 0:
            return common
            
        return None
    
    if state == 0:
        if text == last_text:
            tab_count += 1
        else:
            tab_count = 1
            last_text = text
            
        if tab_count == 1:
            sys.stdout.write("\x07")
            sys.stdout.flush()
            return None
        else:
            display = [os.path.basename(m.rstrip("/")) + ("/" if m.endswith("/") else "") for m in matches]
            sys.stdout.write("\n" + "  ".join(matches) + "\n")
            sys.stdout.write("$ " + line)
            sys.stdout.flush()
            tab_count = 0
            last_text = None
            return None
    
    return None

readline.set_completer(completer)
readline.parse_and_bind("tab: complete")
readline.set_completer_delims(" \t\n")

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
    stdout_file = None
    stdout_append = None
    stderr_file = None
    stderr_append = None
    i = 0
    n = len(line)
    has_current = False
    
    while i < n:
        c = line[i]
        
        if c == "\\" and not in_single and not in_double:
            if i + 1 < n:
                current_arg.append(line[i + 1])
                has_current = True
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
            has_current = True
        elif c == "'" and not in_double:
            in_single = not in_single
            has_current = True
            i += 1
        elif c == '"' and not in_single:
            in_double = not in_double
            has_current = True
            i += 1
        elif c == ">" and not in_single and not in_double:
            fd = 1
            if current_arg == ["2"]:
                fd = 2
                current_arg = []
                has_current = False
            elif current_arg == ["1"]:
                current_arg = []
                has_current = False
            if has_current:
                args.append(''.join(current_arg))
                current_arg = []
                has_current = False
                
            i += 1
            append = False
            if i < n  and line[i] == ">":
                append = True
                i += 1
            while i < n and line[i].isspace():
                i += 1
                
            fname, i = _parse_token(line, i)
            if fd == 2:
                stderr_file = fname
                stderr_append = append
            else:
                stdout_file = fname
                stdout_append = append
        elif c.isspace() and not in_single and not in_double:
            if has_current:
                args.append(''.join(current_arg))
                current_arg = []
                has_current = False
                
            i += 1
        else:
            current_arg.append(c)
            has_current = True
            i += 1
            
    if has_current:
        args.append(''.join(current_arg))
        
    return args, stdout_file, stderr_file, stdout_append, stderr_append

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

        command_parts, stdout_file, stderr_file, stdout_append, stderr_append = parse_command(command)
        if not command_parts:
            continue
        
        cmd = command_parts[0]
        args = command_parts[1:] if len(command_parts) > 1 else []

        out = None
        err = None
        if stdout_file is not None:
            try:
                out = open(stdout_file, "a" if stdout_append else "w")
            except Exception as e:
                print(f"{stdout_file}: {e}")
                continue
        if stderr_file is not None:
            try:
                err = open(stderr_file, "a" if stderr_append else "w")
            except Exception as e:
                print(f"{stderr_file}: {e}")
                if out: out.close()
                continue

        if cmd == "exit":
            if out: out.close()
            if err: err.close()
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
                if err: err.close()
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
        elif cmd == "complete":
            target = out if out else sys.stdout
            if len(args) >= 3 and args[0] == "-C":
                script = args[1]
                cmd_name = args[2]
                completions[cmd_name] = script
            if len(args) >= 2 and args[0] == "-p":
                cmd_name = args[1]
                if cmd_name in completions:
                    print(f"complete -C '{completions[cmd_name]}' {cmd_name}", file=target)
                else:
                    print(f"complete: {cmd_name}: no completion specification", file=target)
        else:
            full_path = find_in_path(cmd)
            if full_path is None:
                print(f"{cmd}: command not found", file=(err if err else sys.stderr))
            else:
                try:
                    subprocess.run([cmd] + args, executable=full_path, stdout=out, stderr=err)
                except Exception as e:
                    print(f"Error executing {cmd}: {e}")

        if out:
            out.close()
            
        if err:
            err.close()
            
if __name__ == "__main__":
    main()
