import sys

COMMANDS = ["type", "exit", "echo"]

def main():
    while True:
        sys.stdout.write("$ ")

        command = input()
        if command == "exit":
            break
        elif command.startswith("echo "):
            print(command[5:])
        elif command.startswith("type "):
            if command[5:] in COMMANDS:
                print(f"{command[5:]} is a shell builtin")
            else:
                print(f"{command[5:]}: not found")
        else:
           print(f"{command}: command not found")


if __name__ == "__main__":
    main()
