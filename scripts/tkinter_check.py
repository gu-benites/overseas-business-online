import tkinter


def main() -> None:
    root = tkinter.Tk()
    try:
        print(f"TK {tkinter.TkVersion}")
        print(f"WINDOWING {root.tk.call('tk', 'windowingsystem')}")
    finally:
        root.withdraw()
        root.destroy()


if __name__ == "__main__":
    main()
