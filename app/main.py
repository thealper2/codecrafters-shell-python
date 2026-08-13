import sys


def main():
    while True:
        sys.stdout.write("$ ")

        command = input()
        if command == "exit":
            break
        elif command.startswith("echo"):
            print(command[1:])
        else:
           print(f"{command}: command not found")


if __name__ == "__main__":
    main()
