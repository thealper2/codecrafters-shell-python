import sys
import os
import subprocess
import readline

BUILTINS = ["echo", "exit"]
COMMANDS = ["type", "exit", "echo", "pwd", "cd", "complete", "jobs", "history", "declare"]
completions = {}
jobs = []

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
            
            if len(matches) == 1:
                if state == 0:
                    return matches[0] + " "
                
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
                    sys.stdout.write("\n" + "  ".join(matches) + "\n")
                    sys.stdout.write("$ " + line)
                    sys.stdout.flush()
                    tab_count = 0
                    last_text = None
                    return None
                
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
readline.parse_and_bind("set editing-mode emacs")

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

def reap_jobs(target=None):
    """Print Done lines for completed jobs and remove thgem. Returns nothing."""
    if target is None:
        target = sys.stdout
        
    n_jobs = len(jobs)
    remaining = []
    for idx, job in enumerate(jobs):
        if job["proc"].poll() is None:
            remaining.append(job)
        else:
            if idx == n_jobs - 1:
                marker = "+"
            elif idx == n_jobs - 2:
                marker = "-"
            else:
                marker = " "
            print(f"[{job['num']}]{marker}  {'Done':<24}{job['cmd']}", file=target)
            
    jobs[:] = remaining

def split_pipeline(line):
    """Split a line into pipeline segments on unquoted, unescaped '|'."""
    segments = []
    current = []
    in_single = False
    in_double = False
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == "\\" and not in_single:
            current.append(c)
            if i + 1 < n:
                current.append(line[i + 1])
                i += 2
            else:
                i += 1
            continue
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        if c == "|" and not in_single and not in_double:
            segments.append(''.join(current))
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
        
    segments.append(''.join(current))
    return segments

def run_builtin(cmd, args, out=None):
    """Execute a builtin, writing to `out` (a file object) or sys.stdout."""
    target = out if out else sys.stdout
    if cmd == "echo":
        print(" ".join(args), file=target)
    elif cmd == "type":
        if args:
            name = args[0]
            if name in COMMANDS:
                print(f"{name} is a shell builtin", file=target)
            else:
                fp = find_in_path(name)
                if fp:
                    print(f"{name} is {fp}", file=target)
                else:
                    print(f"{name}: not found", file=target)
    elif cmd == "pwd":
        print(os.getcwd(), file=target)

def run_pipeline(segments):
    parsed = []
    for seg in segments:
        parts, so, se, sa, sea = parse_command(seg)
        if parts:
            parsed.append(parts)
    if not parsed:
        return

    n = len(parsed)
    pids = []
    procs = []
    prev_read = None

    for idx, parts in enumerate(parsed):
        cmd = parts[0]
        args = parts[1:]

        if idx < n - 1:
            read_fd, write_fd = os.pipe()
        else:
            read_fd, write_fd = None, None

        is_builtin = cmd in COMMANDS

        if is_builtin:
            pid = os.fork()
            if pid == 0:
                if prev_read is not None:
                    os.dup2(prev_read, 0)
                if write_fd is not None:
                    os.dup2(write_fd, 1)
                if prev_read is not None:
                    os.close(prev_read)
                if read_fd is not None:
                    os.close(read_fd)
                if write_fd is not None:
                    os.close(write_fd)
                try:
                    run_builtin(cmd, args)
                    sys.stdout.flush()
                finally:
                    os._exit(0)
            else:
                pids.append(pid)
        else:
            full_path = find_in_path(cmd)
            if full_path is None:
                print(f"{cmd}: command not found", file=sys.stderr)
            else:
                stdin = prev_read
                stdout = write_fd if write_fd is not None else None
                proc = subprocess.Popen(
                    [cmd] + args,
                    executable=full_path,
                    stdin=stdin,
                    stdout=stdout,
                )
                procs.append(proc)

        if prev_read is not None:
            os.close(prev_read)
        if write_fd is not None:
            os.close(write_fd)
        prev_read = read_fd

    if prev_read is not None:
        os.close(prev_read)

    for pid in pids:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    for proc in procs:
        proc.wait()

def main():
    global job_counter
    history_list = []
    last_append_index = 0
    histfile = os.environ.get("HISTFILE")
    shell_vars = {}
    
    if histfile:
        try:
            with open(histfile) as f:
                for line in f:
                    entry = line.rstrip("\n")
                    if entry:
                        history_list.append(entry)
                        readline.add_history(entry)        
        except OSError:
            pass
        
    last_append_index = len(history_list)
    
    while True:
        reap_jobs()

        try:
            command = input("$ ")
        except EOFError:
            if histfile:
                try:
                    with open(histfile, "w") as f:
                        for item in history_list:
                            f.write(item + "\n")
                except OSError:
                    pass
            break

        history_list.append(command)
        if not command.strip():
            continue
        
        segments = split_pipeline(command)
        if len(segments) > 1:
            run_pipeline(segments)
            continue

        command_parts, stdout_file, stderr_file, stdout_append, stderr_append = parse_command(command)
        if not command_parts:
            continue
        
        background = False
        if command_parts and command_parts[-1] == "&":
            background = True
            command_parts = command_parts[:-1]
            
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
            if histfile:
                try:
                    with open(histfile, "w") as f:
                        for item in history_list:
                            f.write(item + "\n")
                except OSError:
                    pass
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
            elif len(args) >= 2 and args[0] == "-r":
                cmd_name = args[1]
                completions.pop(cmd_name, None)  
            elif len(args) >= 2 and args[0] == "-p":
                cmd_name = args[1]
                if cmd_name in completions:
                    print(f"complete -C '{completions[cmd_name]}' {cmd_name}", file=target)
                else:
                    print(f"complete: {cmd_name}: no completion specification", file=target)
        elif cmd == "jobs":
            target = out if out else sys.stdout
            n_jobs = len(jobs)
            remaining = []
            
            for idx, job in enumerate(jobs):
                if idx == n_jobs - 1:
                    marker = "+"
                elif idx == n_jobs - 2:
                    marker = "-"
                else:
                    marker = " "
                if job["proc"].poll() is None:
                    print(f"[{job['num']}]{marker}  {'Running':<24}{job['cmd']} &", file=target)
                    remaining.append(job)
                else:
                    print(f"[{job['num']}]{marker}  {'Done':<24}{job['cmd']}", file=target)
            jobs[:] = remaining
        elif cmd == "history":
            target = out if out else sys.stdout
            if len(args) >= 2 and args[0] == "-r":
                path = args[1]
                try:
                    with open(path) as f:
                        for line in f:
                            entry = line.rstrip("\n")
                            if entry:
                                history_list.append(entry)
                                readline.add_history(entry)
                                
                except OSError:
                    pass
            elif len(args) >= 2 and args[0] == "-w":
                path = args[1]
                try:
                    with open(path, "w") as f:
                        for item in history_list:
                            f.write(item + "\n")
                except OSError:
                    pass
            elif len(args) >= 2 and args[0] == "-a":
                path = args[1]
                try:
                    with open(path, "a") as f:
                        for item in history_list[last_append_index:]:
                            f.write(item + "\n")
                    last_append_index = len(history_list)
                except OSError:
                    pass
            else:
                length = len(history_list)
                start = 0
                if args:
                    try:
                        count = int(args[0])
                        start = max(0, length - count)
                    except ValueError:
                        start = 0
                for i in range(start, length):
                    print(f"{i:>5}  {history_list[i]}", file=target)
        elif cmd == "declare":
            target = out if out else sys.stdout
            if len(args) >= 2 and args[0] == "-p":
                name = args[1]
                if name in shell_vars:
                    print(f'declare -- {name}="{shell_vars[name]}"', file=target)
                else:
                    print(f"declare: {name}: not found", file=target)
            elif args and "=" in args[0]:
                name, _, value = args[0].partition("=")
                shell_vars[name] = value
        else:
            full_path = find_in_path(cmd)
            if full_path is None:
                print(f"{cmd}: command not found", file=(err if err else sys.stderr))
            elif background:
                try:
                    proc = subprocess.Popen(
                        [cmd] + args,
                        executable=full_path,
                        stdout=out,
                        stderr=err,
                    )
                    if jobs:
                        job_num = max(j["num"] for j in jobs) + 1
                    else:
                        job_num = 1
                        
                    jobs.append({
                        "num": job_num,
                        "pid": proc.pid,
                        "proc": proc,
                        "cmd": " ".join([cmd] + args),
                    })
                    print(f"[{job_num}] {proc.pid}")
                except Exception as e:
                    print(f"Error executing {cmd}: {e}")
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
