import sys

from split import split


def main(argv):
    total = float(argv[1])
    n = int(argv[2])
    for i, share in enumerate(split(total, n), 1):
        print(f"第{i}人: {share}")


if __name__ == "__main__":
    main(sys.argv)
